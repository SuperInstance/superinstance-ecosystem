# GPU/OpenCL/NEON Paradigms for Tile Fields

**Date:** 2026-06-03  
**Author:** Research synthesis from existing benchmarks + novel exploration  
**Status:** Ideation — paradigms not yet implemented  
**Hardware:** RTX 4050 (6GB VRAM, Ada, CUDA 8.9) / Ryzen 9 5900X (12C/24T) / Oracle ARM64 (Ampere A1)

---

## Context

What we've proven so far:
- **GPU SVD:** 86× faster than CPU for batch SVD on tile fields
- **Throughput:** 2.7B tile evolves/sec at dim=64, batch=1024
- **Compression:** Rank-1 SVD captures 8.9× compression; rank-1 viable at 30% of tiles
- **Pruning:** 96.5% dead code elimination; negative space converges with CV < 0.02
- **Rust carapace:** 128ns per tile hash, dominates the pipeline at small scale
- **CUDA integration:** lever-runner has PTX warp-shuffle for intra-warp reduction
- **Conservation law:** Score magnitudes are Penrose-conserved; strategies are degenerate

What we haven't tried: **everything below.**

---

## Paradigm 1: GPU-Native Tile Fields — Zero CPU Round-Trips

### Concept
Currently, tiles live on CPU (Rust carapace hashes at 128ns) and get batched to GPU for SVD/similarity. This means every evolve cycle pays:
1. CPU hash → score update → batch collection
2. CPU→GPU transfer (PCIe, ~10µs latency even for small payloads)
3. GPU compute
4. GPU→CPU readback

**What if tiles lived entirely in GPU global memory?**

### Design
```
Tile Field State (GPU resident):
├── tile_scores:      (N_tiles,) float32  — in VRAM, always
├── tile_prototypes:  (N_tiles, 64)       — in VRAM, always
├── strategy_buffer:  (N_tiles, K)        — top-K strategies per tile
├── evolve_rng_state: (N_tiles, 4) uint32 — per-tile XORWOW states
└── negative_space:   (N_tiles, 64)       — what doesn't work, GPU-compressed
```

All operations happen on GPU:
- **Evolve:** CUDA kernel reads tile scores, applies mutation via GPU RNG, writes back. No CPU involved.
- **SVD:** Already on GPU. Triggered by CUDA stream event, not CPU orchestration.
- **Pruning:** GPU thrust::partition removes dead tiles in-place.
- **Conservation check:** Warp reduction validates score conservation every N steps.

### Why This Matters
At 2.7B evolves/sec, the 128ns CPU hash is already the bottleneck for small fields. GPU-native eliminates it entirely. The CPU becomes an observer that reads telemetry, not a participant in the hot loop.

### Estimated Speedup
- Current: ~3µs per evolve (CPU hash + GPU dispatch overhead)
- GPU-native: ~0.04µs per evolve (single CUDA kernel, no transfer)
- **~75× speedup on the hot path**

### Risk
- Loss of Rust carapace's proven correctness for hashing
- Harder to debug GPU-resident state
- Need careful VRAM budgeting (6GB is tight for very large fields)

---

## Paradigm 2: Warp-Level Democratic Strategy Voting

### Concept
Each CUDA warp (32 threads) represents one tile. The 32 threads collaboratively:
1. Evaluate 32 candidate strategies simultaneously
2. Vote on the best via warp shuffle (PTX `__shfl_sync`)
3. Commit the winner

### Design
```cuda
__global__ void democratic_evolve(
    float* tile_scores,      // (N_tiles,)
    float* strategy_pool,    // (N_tiles, 32, 64) — 32 candidates per tile
    float* prototypes,       // (N_tiles, 64)
    uint32_t* rng_states     // (N_tiles, 4)
) {
    int tile_id = blockIdx.x;
    int lane = threadIdx.x;  // 0..31
    
    // Each lane generates one candidate strategy
    float my_candidate[64];
    generate_strategy(rng_states, tile_id, lane, my_candidate);
    
    // Score this candidate
    float my_score = dot_product(my_candidate, prototypes[tile_id]);
    
    // Democratic vote: warp finds the best score via butterfly reduction
    // Using __shfl_xor_sync — exactly what lever-runner already has
    #pragma unroll
    for (int mask = 16; mask > 0; mask >>= 1) {
        float other = __shfl_xor_sync(0xFFFFFFFF, my_score, mask);
        my_score = fmaxf(my_score, other);
    }
    
    // Lane 0 commits the winner
    if (lane == 0) {
        tile_scores[tile_id] = my_score;
    }
}
```

### Why This Matters
- **32 strategies evaluated for the price of 1** — perfect SIMD utilization
- No atomics, no shared memory — pure register math via warp shuffle
- Already partially prototyped in lever-runner's PTX code
- Naturally maps to tile field structure: 1 warp = 1 tile

### Estimated Speedup
- 32× strategy exploration per cycle (not 32× wall-clock speedup — already parallel)
- Real win: **deeper exploration per time budget**, meaning better convergence at fixed time

### What Makes This Novel
Standard MCTS explores one path per thread. Warp democracy explores 32 paths and takes the best — a fundamentally different search pattern that exploits the degeneracy we observed (many near-optimal strategies exist).

---

## Paradigm 3: Tensor Core FP16 Tile Compression

### Concept
RTX 4050 has 80 4th-gen tensor cores capable of FP16 matmul at ~97 TFLOPS. We proved rank-1 SVD works for 30% of tiles. What if we use tensor cores directly for tile field compression?

### Design
```
Standard approach:  torch.linalg.svd(matrix)  → O(n³) general SVD
Tensor core approach:
  1. Reshape tile prototypes to (N/32, 32, 64) — batch of 32×64 matrices
  2. FP16 cast: tile_protos_half = tile_protos.half()
  3. Batch matmul via tensor cores:
     - U, S, V = batch_svd_half(tile_protos_half)
     - Tensor cores accelerate the bidiagonalization step
  4. Rank selection: keep top-k singular values where cumulative energy > threshold
  5. Reconstruct: tile_compressed = U[:,:k] @ diag(S[:k]) @ V[:,:k].T
```

The key insight: tensor cores don't do SVD directly, but they accelerate the matrix multiplications inside iterative SVD algorithms (power iteration, randomized SVD). A single tensor core can do a 16×16×16 FP16 matmul in 1 clock.

### Concrete Numbers
- 754 tiles × 64 dims × 2 bytes (FP16) = **96 KB** — fits in L1 cache
- Randomized SVD needs ~5 matrix multiplications → tensor cores process in <1µs
- Current CPU SVD on 754×64: ~800µs
- **~800× speedup for compression step**

### Why This Matters
Compression is currently a periodic maintenance operation. With tensor cores, it becomes cheap enough to run every evolve cycle, enabling **continuous compression** — the tile field is always in its minimal representation.

---

## Paradigm 4: Double-Buffered Async Pipeline (Ryzen Sim + GPU Compile)

### Concept
Ryzen 5900X has 24 threads. RTX 4050 has 2560 CUDA cores. They're currently used sequentially. What if we pipeline them?

### Design
```
Timeline:
─────────────────────────────────────────────────────→ time

CPU Thread Pool (24 threads):
[Sim batch A                                    ][Sim batch C                          ]
                 [Process B results + dispatch C][Sim batch B                          ]

GPU:
                 [Compile A + SVD A + Prune A   ][Compile B + SVD B + Prune B          ]

Stream 0 (default):  [====A====]
Stream 1 (async):                 [====B====]
Stream 0:                                      [====C====]

Result: CPU and GPU never idle. Each is always working on the next batch.
```

### Implementation
```python
import torch

stream_a = torch.cuda.Stream()
stream_b = torch.cuda.Stream()

# Buffer A: CPU fills while GPU processes buffer B
# Buffer B: GPU fills while CPU processes buffer A
# Double buffer swap after each cycle

for cycle in range(N):
    active_stream = stream_a if cycle % 2 == 0 else stream_b
    
    with torch.cuda.stream(active_stream):
        # GPU: compile tiles from previous CPU batch
        gpu_result = gpu_compile_and_svd(cpu_buffer)
    
    # CPU: simulate next batch (overlaps with GPU)
    cpu_buffer = parallel_simulate(n_games=1000, n_threads=24)
    
    torch.cuda.synchronize(active_stream)
    merge_results(gpu_result, cpu_buffer)
```

### Why This Matters
Current pipeline: CPU sim → wait → GPU compute → wait → merge. ~50% of each resource is idle at any time. Double buffering drives utilization toward 100%.

### Estimated Speedup
- **~1.8× throughput** (near-perfect overlap, small sync overhead)
- Not as dramatic as single-kernel paradigms, but easy to implement and composable

---

## Paradigm 5: CUDA Graph for Full Pipeline Capture

### Concept
CUDA graphs record an entire sequence of GPU operations (kernels, transfers, synchronization) into a single executable graph. Launching the graph is ~1µs regardless of complexity — vs. ~10µs per kernel launch.

### Design
```
Current (imperative):
  cudaMalloc → cudaMemcpy → kernel1 → cudaMalloc → kernel2 → cudaMemcpyBack
  Launch overhead: 5 × 10µs = 50µs per cycle

CUDA Graph:
  Record once: [alloc → copy → kernel1 → alloc → kernel2 → readback]
  Replay: 1µs per cycle
```

```python
# Capture
with torch.cuda.graph(graph):
    static_input = torch.zeros(BATCH, 64, device='cuda')
    intermediate = kernel1(static_input)
    scores = kernel2(intermediate)
    static_output = prune(scores)

# Replay (every evolve cycle)
static_input.copy_(new_data)
graph.replay()
result = static_output.clone()
```

### Why This Matters
At 2.7B evolves/sec, kernel launch overhead becomes significant. CUDA graphs eliminate it. Combined with Paradigm 1 (GPU-native), this gives us a **single-dispatch tile field engine** — the entire evolve+compile+prune cycle fires in one GPU command.

### Estimated Speedup
- **~50× reduction in dispatch overhead** (50µs → 1µs)
- Small absolute gain at batch=1024 (overhead is ~2% of compute time)
- **Huge gain at small batch** (overhead dominates at batch=32)

### Synergy
CUDA graphs + warp democracy + GPU-native = **the full monty**. Record the entire pipeline as a graph. Replay at 1µs. CPU never touches tile state.

---

## Paradigm 6: OpenCL Portable Kernels (NVIDIA/AMD/Mali/Intel)

### Concept
All paradigms above are CUDA-specific. OpenCL gives us portable compute across every GPU vendor — critical for deployment beyond the workstation.

### Design
```c
// tile_evolve.cl — works on NVIDIA, AMD, ARM Mali, Intel Xe
__kernel void tile_evolve(
    __global const float* prototypes,   // (N, 64)
    __global float* scores,             // (N,)
    __global const float* candidates,   // (N, K, 64)
    __global uint4* rng_states,         // (N,)
    const int K
) {
    int tile_id = get_global_id(0);
    if (tile_id >= N) return;
    
    float best_score = -INFINITY;
    int best_k = 0;
    
    for (int k = 0; k < K; k++) {
        float score = 0.0f;
        for (int d = 0; d < 64; d++) {
            score += prototypes[tile_id * 64 + d] 
                   * candidates[(tile_id * K + k) * 64 + d];
        }
        if (score > best_score) {
            best_score = score;
            best_k = k;
        }
    }
    
    scores[tile_id] = best_score;
}
```

### Why This Matters
- **Oracle ARM64** has no NVIDIA GPU → needs OpenCL or Vulkan for GPU compute
- **Android deployment** (Loom's eventual target) → Adreno/Mali GPUs, OpenCL or Vulkan
- **Intel GPUs** (potential edge deployment) → OpenCL 3.0 or SYCL
- Write once, run on everything (the dream, at least)

### Reality Check
OpenCL performance is typically 70-90% of CUDA on NVIDIA hardware. On AMD/Mali, it's the only option. The performance gap is acceptable for edge deployment where we just need *any* GPU acceleration.

### Implementation Strategy
1. Write core kernels in OpenCL C
2. Use `cl21` as minimum version (broad support)
3. Auto-tune work-group size per device (NVIDIA: 256, AMD: 64, Mali: 32)
4. Fall back to CPU (Rust carapace) when no GPU available

---

## Paradigm 7: NEON ARM Experiments (Oracle ARM64 / Loom's Box)

### Concept
ARM NEON provides 128-bit SIMD — 4× float32 or 2× float64 per instruction. The Ryzen 5900X has AVX2 (256-bit), but the Oracle ARM64 box is where NEON-specific work happens.

### What Can ONLY Be Tested on ARM

| Experiment | Why ARM-Only |
|-----------|-------------|
| NEON intrinsics for tile hashing | NEON `vmlaq_f32`, `vpaddq_f32` — no x86 equivalent |
| ARM SVE (if available on Ampere A1) | Scalable vectors: 128-2048 bit, runtime-determined width |
| Big.LITTLE scheduling | Cortex-A78C + Cortex-A55 — heterogeneous cores |
| ARM pointer authentication | Cache-tile binding — tie tile address to auth code |
| ARM Memory Tagging (MTE) | Tag tiles with allocation metadata — detect field corruption |
| ARM Scalable Matrix Extension (SME) | Outer product instructions for tile similarity |

### NEON Tile Hash (128ns equivalent)
```rust
// ARM NEON tile hashing — target: <100ns on Cortex-A78C
use std::arch::aarch64::*;

unsafe fn neon_tile_hash(prototype: &[f32; 64], candidate: &[f32; 64]) -> f32 {
    let mut acc = vdupq_n_f32(0.0);
    
    for i in (0..64).step_by(4) {
        let p = vld1q_f32(prototype.as_ptr().add(i));
        let c = vld1q_f32(candidate.as_ptr().add(i));
        acc = vmlaq_f32(acc, p, c);  // fused multiply-add, 4 floats at once
    }
    
    // Horizontal sum: pairwise add
    let sum = vpaddq_f32(acc, acc);  // [a+b, c+d, a+b, c+d]
    let sum = vpaddq_f32(sum, sum);  // [a+b+c+d, ...]
    vgetq_lane_f32(sum, 0)
}
```

### Why This Matters
The Rust carapace's 128ns hash is on x86 (Ryzen). ARM NEON could match or beat this because:
- NEON has FMA as a single instruction (x86 needs FMA3 extension)
- ARM's simpler pipeline has more predictable latency
- Oracle ARM64 has **always-available NEON** (no feature detection needed)

### What Needs NEON Specifically
- **Tile similarity dot products** (the hot inner loop) — NEON FMA processes 4 floats/cycle
- **Score aggregation across tiles** — NEON `vpadd` horizontal adds
- **Conservation law validation** — NEON reduction across tile field
- **FP16 tile storage** — ARM FP16 is native (no conversion overhead like x86)

---

## Paradigm 8: Vulkan Compute for Android/Embedded

### Concept
Vulkan compute shaders are the most portable GPU compute option — works on Android (Adreno, Mali), embedded (Pi GPU), and desktop (all vendors). OpenCL isn't always available on Android.

### Design
```glsl
// tile_evolve.comp
#version 450
layout(local_size_x = 256) in;

layout(binding = 0) buffer Prototypes { float prototypes[]; };
layout(binding = 1) buffer Scores { float scores[]; };
layout(binding = 2) buffer Candidates { float candidates[]; };

layout(push_constant) uniform Push {
    int n_tiles;
    int n_candidates;
} push;

void main() {
    int tile_id = int(gl_GlobalInvocationID.x);
    if (tile_id >= push.n_tiles) return;
    
    float best = -1.0/0.0;
    for (int k = 0; k < push.n_candidates; k++) {
        float score = 0.0;
        for (int d = 0; d < 64; d++) {
            score += prototypes[tile_id * 64 + d] 
                   * candidates[(tile_id * push.n_candidates + k) * 64 + d];
        }
        best = max(best, score);
    }
    scores[tile_id] = best;
}
```

### Why This Matters
- **Android deployment path** for Loom — Adreno 6xx/7xx GPUs support Vulkan 1.1+
- **No vendor lock-in** — same SPIR-V runs on Qualcomm, ARM, Intel, NVIDIA
- **Headless compute** — no display server needed (important for edge boxes)
- **Subgroup operations** (Vulkan 1.1) provide warp-level primitives similar to CUDA shuffle

### Mobile-Specific Considerations
| Constraint | Impact | Mitigation |
|-----------|--------|-----------|
| Thermal throttling | Sustained compute limited to 2-5 minutes | Batch evolve in 30s bursts |
| VRAM (shared RAM) | 2-4 GB total device memory | Keep tile field < 100 MB |
| Power budget | GPU draws 2-5W | FP16 precision, batch=64 |
| Driver quality | Android Vulkan drivers are buggy | Extensive device-specific testing |

---

## Paradigm 9: SYCL/oneAPI for Intel GPUs

### Concept
Intel's oneAPI/SYCL is the path to Intel Arc GPUs and Xeon SP integrated graphics. Niche but potentially interesting for Xeon-based servers.

### Design
```cpp
// tile_evolve_sycl.cpp
#include <sycl/sycl.hpp>

void evolve_tiles(
    sycl::queue& q,
    float* prototypes, float* scores, float* candidates,
    int n_tiles, int n_candidates
) {
    q.parallel_for(sycl::range<1>(n_tiles), [=](sycl::id<1> idx) {
        int tile_id = idx[0];
        float best = -std::numeric_limits<float>::infinity();
        
        for (int k = 0; k < n_candidates; k++) {
            float score = 0.0f;
            for (int d = 0; d < 64; d++) {
                score += prototypes[tile_id * 64 + d]
                       * candidates[(tile_id * n_candidates + k) * 64 + d];
            }
            if (score > best) best = score;
        }
        scores[tile_id] = best;
    });
}
```

### Why This Matters (Low Priority)
Intel GPUs are not in our current hardware roster. But:
- **Intel Xeon SP** servers have integrated compute — potential deployment target
- **Intel Arc** discrete GPUs are cheap and widely available
- **SYCL compiles to CUDA** via DPC++ — one codebase for NVIDIA + Intel
- If we ever deploy on cloud, Intel GPU instances exist (Springs/Gaudi)

### Priority: **Low.** Worth keeping in mind, not worth implementing until there's an Intel GPU in the picture.

---

## Paradigm Comparison Matrix

| # | Paradigm | Platform | Est. Speedup | Effort | Novelty | Priority |
|---|----------|----------|-------------|--------|---------|----------|
| 1 | GPU-native tiles | CUDA | 75× | High | ⭐⭐⭐⭐⭐ | 🔥 High |
| 2 | Warp democracy | CUDA | 32× exploration | Medium | ⭐⭐⭐⭐⭐ | 🔥 High |
| 3 | Tensor core compression | CUDA | 800× (SVD step) | Medium | ⭐⭐⭐⭐ | 🔥 High |
| 4 | Double-buffered async | CUDA | 1.8× | Low | ⭐⭐⭐ | 🔧 Quick win |
| 5 | CUDA graph | CUDA | 50× (dispatch) | Low | ⭐⭐⭐ | 🔧 Quick win |
| 6 | OpenCL portable | Multi | 0.7-0.9× vs CUDA | Medium | ⭐⭐⭐ | 📋 Medium |
| 7 | NEON ARM | ARM64 | Match x86 | Low | ⭐⭐⭐⭐ | 📋 Medium |
| 8 | Vulkan compute | Mobile/Embedded | Portable GPU | High | ⭐⭐⭐ | 📅 Future |
| 9 | SYCL/oneAPI | Intel | Portable | Medium | ⭐⭐ | 📅 Low |

---

## Recommended Implementation Order

### Phase 1: Quick Wins (1-2 days)
1. **CUDA graph capture** — wrap existing lever-runner pipeline
2. **Double-buffered async** — overlap Ryzen sim with GPU compute

### Phase 2: Core GPU-Native (1 week)
3. **GPU-native tile fields** — move tile state to VRAM, CPU observes only
4. **Warp-level democracy** — extend existing PTX shuffle code

### Phase 3: Acceleration (1 week)
5. **Tensor core FP16 compression** — continuous SVD via tensor cores
6. **Benchmark: 1→5 combined** — measure full pipeline

### Phase 4: Portability (ongoing)
7. **NEON ARM** — Rust carapace ARM port with NEON intrinsics
8. **OpenCL kernels** — portable versions of core kernels
9. **Vulkan compute** — when Android target is defined

---

## ARM-Only Experiments

These can **only** be validated on ARM hardware (Oracle ARM64):

1. **NEON FMA tile hashing** — measure actual ns per hash on Cortex-A78C vs Ryzen 128ns
2. **ARM FP16 native arithmetic** — no conversion penalty, measure tile field quality at FP16
3. **ARM SVE auto-vectorization** — if Ampere A1 supports SVE, measure variable-width SIMD
4. **Big.LITTLE tile scheduling** — evolve tiles on big cores, compress on LITTLE cores
5. **ARM MTE tile tagging** — memory tagging for field integrity validation
6. **ARM pointer auth + tile binding** — cryptographically bind tile addresses to content

---

## The Big Picture

The current system is **CPU-first with GPU acceleration bolted on.** The paradigms above flip this: **GPU-first with CPU as orchestrator.** The end state looks like:

```
CPU (Ryzen / ARM):
  ├── Orchestration (schedule, telemetry, persistence)
  ├── Rust carapace for correctness-critical hashing (fallback)
  └── Game simulation (CPU is still faster for small sequential games)

GPU (RTX 4050 / ARM Mali / Intel Xe):
  ├── Tile field state (VRAM-resident)
  ├── Evolve cycle (warp democracy, 1µs dispatch via CUDA graph)
  ├── Continuous compression (tensor cores, FP16 SVD)
  ├── Conservation validation (warp reduction, every cycle)
  └── Pruning (GPU thrust, in-place)
```

The CPU sends **one command per cycle**: "evolve." The GPU does everything else. That's the paradigm shift.

---

*"The negative space is conserved. The GPU merely reveals it faster."*
