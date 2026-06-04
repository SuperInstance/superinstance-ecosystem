# GPU-Native Tile Field Architecture — Unified Design

**Date:** 2026-06-03  
**Status:** Architecture Document  
**Hardware:** RTX 4050 Laptop (6GB VRAM, 2560 CUDA cores, 80 Tensor Cores, 192 GB/s), AMD Ryzen 9 5900X (12C/24T, 64MB L3, PCIe 4.0 x8), 16GB DDR4 (WSL2)  
**PCIe Link:** 4.0 x8 → 15.75 GB/s bidirectional  
**Goal:** Run the entire tile field pipeline — hash, embed, search, evolve, SVD — on GPU with CPU feeding game simulations through a double-buffered zero-copy pipeline.

---

## 1. Memory Layout — Packing Tiles into GPU Memory

### 1.1 Per-Tile Storage Budget

Every tile needs:

| Field | Type | Bytes | Alignment | Notes |
|-------|------|-------|-----------|-------|
| Score vector | `float32` × K_actions | 4K | 16B | K=9 for TTT, K=7 for C4 |
| Visit counts | `int32` × K_actions | 4K | 16B | Mirror of score vector |
| Hash / embedding | `float16` × 64 | 128 | 16B | FP16 sufficient per benchmark validation |
| Prototype vector | `float16` × 64 | 128 | 16B | For similarity search |
| Metadata | `int32` × 4 | 16 | 16B | game_id, flags, generation, padding |
| **Total** | | **4K + 4K + 128 + 128 + 16** | | |

For TTT (K=9): **88 + 16 = 104 bytes overhead + 72 bytes scores/visits = 176 bytes/tile**  
For general K (say K≤32): **~432 bytes/tile max**

### 1.2 Structure of Arrays, Not Arrays of Structures

**Critical for coalesced access.** GPU threads in a warp (32 threads) should read consecutive addresses. An AoS layout causes warp divergence on memory access patterns.

```
VRAM Layout (SoA — all buffers 256-byte aligned):

┌──────────────────────────────────────────────────────────┐
│ Region              │ Size (N tiles)      │ Offset calc  │
├─────────────────────┼─────────────────────┼──────────────┤
│ scores              │ N × K × float32     │ base + 0     │
│ visits              │ N × K × int32       │ base + N*K*4 │
│ embeddings (FP16)   │ N × 64 × float16    │ base + N*K*8 │
│ prototypes (FP16)   │ N × 64 × float16    │ base + N*128 │
│ metadata            │ N × 4 × int32       │ base + N*128 │
│ ─── padding ───     │ to 256B boundary    │              │
│ ─── workspace ───   │ (see §2.4)          │              │
└──────────────────────────────────────────────────────────┘
```

### 1.3 Capacity Calculation

Available VRAM after OS/driver overhead: **~5.5 GB usable** (conservative).

| Scenario | K | Bytes/tile | Max tiles (FP32 scores) | Max tiles (FP16 scores) |
|----------|---|-----------|------------------------|------------------------|
| TTT | 9 | 176 | **31.3M** | **62.5M** |
| Connect-4 | 7 | 160 | **34.4M** | **68.7M** |
| General (K=32) | 32 | 432 | **12.7M** | **25.5M** |
| High-dim embed (dim=384) | 9 | 912 | **6.0M** | **12.1M** |

**Verdict:** 6GB is *massive* for tile fields. Even at K=32 with dim=384, we fit 6M tiles. The entire TTT state space (~5,478 unique states) fits 5,700× over. The constraint is never VRAM — it's compute throughput and PCIe bandwidth.

### 1.4 Workspace Memory Budget

The GPU needs scratch space for intermediate results:

| Buffer | Size | When used |
|--------|------|-----------|
| Query batch (states) | B × 64 × 2B (FP16) | Every search |
| Similarity matrix | B × N_tiles × 4B (FP32) | Every search |
| SVD workspace | N_tiles × N_tiles × 4B | SVD kernel |
| Scatter-add accumulators | N_tiles × K × 8B | Evolve |
| Sort buffer (top-K) | N_tiles × 4B | Prune |

For B=10K queries, N_tiles=100K, K=9:
- Query batch: 1.28 MB
- Similarity matrix: 3.6 GB ← **too large for 100K tiles**
- Solution: **chunked search** — process tiles in blocks of 1K, keep running top-K

**Design rule:** Similarity matrix must fit in VRAM. With 4GB usable (after tile data), that limits B × N ≤ 1B entries → B=10K queries against N=100K tiles requires 10-pass chunked search.

### 1.5 Alignment and Coalescing Rules

```
Warp size = 32 threads
Cache line = 128 bytes (32 × float32)
Memory transaction = 32 bytes minimum

Rules:
1. scores[]: stride = K × 4B. Pad K to next power of 2 (K=9 → 16 floats = 64B stride)
   → Warp of 32 threads reads 32 × 64B = 2KB, all coalesced
2. embeddings[]: stride = 64 × 2B = 128B. Perfect half-warp alignment.
3. Use __ldg() (read-only cache) for prototype reads in search kernels
4. Use __restrict__ pointers to enable load-store forwarding
```

---

## 2. Kernel Pipeline — Hash → Embed → Search → Evolve → SVD

### 2.1 Pipeline Overview

```
          CPU (Ryzen)                          GPU (RTX 4050)
    ┌─────────────────┐                 ┌──────────────────────────┐
    │ Game simulation  │───PCIe 4.0───→ │                          │
    │ (24 threads)     │    15.75 GB/s   │  ┌──────┐  ┌──────────┐ │
    │                  │                 │  │ Hash │→→│ Embed    │ │
    │ State buffer A   │────────────────│→│(kernel│  │(matmul)  │ │
    │ State buffer B   │ (double-buf)   │  │      │  │          │ │
    └─────────────────┘                 │  └──────┘  └────┬─────┘ │
                                        │                  │       │
                                        │           ┌──────▼─────┐ │
                                        │           │ Search     │ │
                                        │           │ (similarity│ │
                                        │           │  matmul)   │ │
                                        │           └──────┬─────┘ │
                                        │                  │       │
                                        │  ┌──────┐  ┌────▼──────┐│
                                        │  │ SVD  │←←│ Evolve    ││
                                        │  │(rank │  │(scatter-  ││
                                        │  │-R)   │  │ add, sort)││
                                        │  └──────┘  └───────────┘│
                                        └──────────────────────────┘

Stream ordering: All kernels on CUDA stream 0 (sequential within stream)
                 DMA transfers on separate streams for overlap
```

### 2.2 Kernel 1: Hash — State → Tile Embedding

**Input:** Raw game states (variable format per game)  
**Output:** 64-dim FP16 embeddings

For TTT: board is 9 cells × 3 values (X/O/blank) = 27 bits → hash to 64 floats.

```cuda
// Kernel: state_hash_kernel
// Each thread handles one state
// Input:  states[] (B × raw_state_size), packed as uint32
// Output: embeddings[] (B × 64 × float16)

__global__ void state_hash_kernel(
    const uint32_t* __restrict__ states,  // raw game states, packed
    half* __restrict__ embeddings,        // output: (B, 64)
    const int B,                          // batch size
    const int state_bytes                 // bytes per raw state
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= B) return;
    
    const uint32_t* state = states + (idx * state_bytes / 4);
    half* embed = embeddings + idx * 64;
    
    // Position-aware hash: combine cell value with position
    // TTT: 9 cells, each {0, 1, 2} → 3 values
    // Hash each cell-position pair into multiple embedding dims
    for (int d = 0; d < 64; d++) {
        // MurmurHash3-like mixing of (state, position, dimension)
        uint32_t h = state[d % (state_bytes / 4)];
        h ^= (d * 0x5bd1e995);
        h ^= h >> 13;
        h *= 0x5bd1e995;
        h ^= h >> 15;
        // Map to [-1, 1] via fast reciprocal
        embed[d] = __float2half(((float)h / (float)0xFFFFFFFF) * 2.0f - 1.0f);
    }
}
```

**Latency:** ~2µs for B=1024 (hash is compute-light, memory-bound on state reads)

### 2.3 Kernel 2: Embed — Batch Matrix Multiply

**Input:** (B, 64) FP16 embeddings  
**Output:** (B, N_tiles) FP32 similarities  

This is a **GEMM** — the GPU's bread and butter.

```python
# PyTorch level — let cuBLAS handle it
similarities = torch.matmul(embeddings_fp16, prototypes_fp16.T)  # (B, 64) × (64, N) → (B, N)
# FP16 matmul with FP32 accumulate via Tensor Cores
# RTX 4050: ~97 TFLOPS FP16 with Tensor Cores
```

**Throughput:** At dim=64, N=10K tiles:
- FLOPs: 2 × B × 64 × 10K = 1.28B FLOPs per 1K queries
- At 97 TFLOPS: **~13 ns** compute time → memory-bound (dominated by loading 10K × 64 × 2B = 1.28MB prototypes)

**Latency:** ~15µs for B=1K against N=10K tiles (memory-bound at ~192 GB/s reading prototypes)

### 2.4 Kernel 3: Search — Top-K Similarity

**Input:** (B, N_tiles) FP32 similarity matrix  
**Output:** (B, top_k) tile indices + scores

```cuda
// Kernel: topk_search_kernel
// Each thread block handles one query
// Uses shared memory for partial sorting

__global__ void topk_search_kernel(
    const float* __restrict__ similarities,  // (B, N_tiles)
    int* __restrict__ top_indices,           // (B, K_top)
    float* __restrict__ top_scores,          // (B, K_top)
    const int B, const int N_tiles, const int K_top
) {
    extern __shared__ float s_scores[];
    __shared__ int s_indices[1024]; // K_top <= 1024
    
    int query = blockIdx.x;
    if (query >= B) return;
    
    const float* row = similarities + query * N_tiles;
    
    // Block-stride: each thread scans N_tiles/blockDim.x entries
    // Maintain thread-local top-K, then reduce in shared memory
    float local_scores[32]; // K_top per thread
    int local_indices[32];
    // ... (initialize to -inf)
    
    for (int t = threadIdx.x; t < N_tiles; t += blockDim.x) {
        float score = row[t];
        // Insert into local top-K (simple insertion sort, K=small)
        for (int k = K_top - 1; k >= 0; k--) {
            if (score > local_scores[k]) {
                if (k < K_top - 1) {
                    local_scores[k+1] = local_scores[k];
                    local_indices[k+1] = local_indices[k];
                }
                local_scores[k] = score;
                local_indices[k] = t;
            }
        }
    }
    
    // Warp-level reduction: use __shfl_down_sync to merge top-K lists
    // Then block-level reduction via shared memory
    // Output final top-K for this query
}
```

**Latency:** ~10µs for B=1K, N=10K, K=10 (shared memory + warp shuffles)

### 2.5 Kernel 4: Evolve — Score Update via Scatter-Add

**Input:** Matched tile indices, outcomes, actions  
**Output:** Updated scores[] and visits[] arrays

```cuda
// Kernel: evolve_kernel
// Each thread handles one (state, action, outcome) triple

__global__ void evolve_kernel(
    const int* __restrict__ tile_ids,    // (B,) — which tile each state maps to
    const int* __restrict__ actions,     // (B,) — action taken
    const float* __restrict__ outcomes,  // (B,) — game outcome (+1/-1/0)
    float* __restrict__ scores,          // (N_tiles, K) — score matrix
    int* __restrict__ visits,            // (N_tiles, K) — visit counts
    const int B, const int K
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= B) return;
    
    int tile = tile_ids[idx];
    int action = actions[idx];
    float outcome = outcomes[idx];
    
    // Atomic update: incremental mean
    int slot = tile * K + action;
    int old_visits = atomicAdd(&visits[slot], 1);
    
    // Online mean update: new_mean = old_mean + (outcome - old_mean) / new_count
    // Requires atomicCAS for float scores (or use FP32 atomicAdd if CC >= 8.0)
    // Ada Lovelace (CC 8.9) supports atomicAdd for float32
    float delta = outcome - scores[slot]; // approximate — race acceptable
    atomicAdd(&scores[slot], delta / (float)(old_visits + 1));
}
```

**Latency:** ~5µs for B=10K updates (atomic contention is the bottleneck, but tiles distribute well)

### 2.6 Kernel 5: SVD — Incremental Low-Rank Factorization

**Input:** Updated score matrix (N_tiles × K)  
**Output:** U (N_tiles × R), S (R,), V (K × R) where R << min(N, K)

For the rank-1 case (8.9× compression), SVD is O(N) — trivial.  
For adaptive rank (R ≤ 8), we use Brand's incremental SVD:

```cuda
// SVD update is too small for a full kernel — use cuBLAS/cuSOLVER
// The augmented matrix is only (R + B_new) × (R + B_new) where R≤8, B_new≤100
// → A 108×108 matrix SVD: ~1µs on Tensor Cores

// Host-side orchestration:
// 1. Project new tiles onto current singular space: GEMM
// 2. Compute residuals: vector subtract
// 3. QR of residuals: cuSOLVER geqrf
// 4. Build augmented K matrix: memset + copy
// 5. SVD of K: cuSOLVER gesvd (tiny matrix)
// 6. Update U, S, V: GEMM
```

**Latency:** ~50µs per incremental update (dominated by cuSOLVER overhead for tiny matrices)

### 2.7 Full Pipeline Latency

| Stage | B=1K | B=10K | B=100K |
|-------|------|-------|--------|
| Hash | 2µs | 15µs | 120µs |
| Embed (matmul) | 15µs | 50µs | 300µs |
| Search (top-K) | 10µs | 80µs | 500µs |
| Evolve (scatter) | 5µs | 30µs | 200µs |
| SVD (incremental) | 50µs | 50µs | 50µs |
| **Total** | **~82µs** | **~225µs** | **~1.17ms** |

**Throughput at B=100K:** ~85M states/second through the full pipeline.

---

## 3. CPU-GPU Synchronization — Double-Buffered Zero-Copy Pipeline

### 3.1 The Double-Buffer Design

```
Time ──────────────────────────────────────────────────→

CPU:   [fill buffer A][fill buffer B][fill buffer A]...
              │              │              │
PCIe:         │   ──A──→    │   ──B──→    │
              │              │              │
GPU:          │   [proc A]   │   [proc B]  │
              ▼              ▼              ▼
           Results A     Results B      Results A
```

**Rule:** CPU fills buffer N while GPU processes buffer N-1. Swap on sync barrier.

### 3.2 Pinned Memory for DMA

```python
import torch

# Allocate pinned (page-locked) host memory for zero-copy DMA
# This is the key to overlapping CPU→GPU transfer with GPU compute

class DoubleBuffer:
    def __init__(self, batch_shape, dtype=torch.float16):
        self.shape = batch_shape
        self.buffers = [
            torch.empty(batch_shape, dtype=dtype, 
                       device='cuda',  # GPU-resident
                       pinned_memory=False),  # GPU memory, no pinning needed
            torch.empty(batch_shape, dtype=dtype, device='cuda')
        ]
        # CPU-side staging buffers (pinned for async DMA)
        self.staging = [
            torch.empty(batch_shape, dtype=dtype).pin_memory(),
            torch.empty(batch_shape, dtype=dtype).pin_memory()
        ]
        self.current = 0  # which buffer GPU is processing
    
    def get_write_buffer(self):
        """CPU writes here"""
        return self.staging[1 - self.current]
    
    def get_read_buffer(self):
        """GPU reads here"""
        return self.buffers[self.current]
    
    def swap(self, stream=None):
        """Transfer staging → GPU buffer, then swap"""
        s = stream or torch.cuda.default_stream()
        # Async copy: pinned CPU → GPU
        self.buffers[1 - self.current].copy_(self.staging[1 - self.current], non_blocking=True)
        self.current = 1 - self.current
```

### 3.3 CUDA Stream Pipeline

```
Stream 0 (default):  Kernels execute sequentially
Stream 1 (DMA):      CPU→GPU async transfers
Stream 2 (DMA):      GPU→CPU result transfers (rare — keep results on GPU)

Timeline:
                    ┌─ Stream 1: DMA buffer A → GPU ──┐
T=0                 │                                  │
    CPU: fill A ────┘                                  │
                                                       ▼
                    ┌─ Stream 0: kernel(A) ────────────┤
T=transfer_done     │                                  │
    CPU: fill B ────┘                                  │
                                                       ▼
                    ┌─ Stream 1: DMA buffer B → GPU ──┤
T=kernel_done       │                                  │
                                                       ▼
                    ┌─ Stream 0: kernel(B) ────────────┤
                                                       ▼
T=done              Results on GPU, no CPU readback needed
```

### 3.4 Zero-Copy: When to Keep Results on GPU

**Key insight:** Results of search/evolve should *stay* on GPU. The only time data comes back to CPU is:
1. **Conservation CV check** — compute on GPU, read back scalar
2. **Policy extraction** — top-K tiles + scores (a few KB)
3. **Logging/checkpointing** — periodic, not latency-critical

```python
# The GPU is the source of truth for tile state
class GPUTileField:
    """All tile state lives in VRAM. CPU never holds tile data."""
    
    def __init__(self, n_tiles, k_actions, dim=64, device='cuda'):
        self.n_tiles = n_tiles
        self.k_actions = k_actions
        self.device = device
        
        # All on GPU
        self.scores = torch.zeros(n_tiles, k_actions, device=device, dtype=torch.float32)
        self.visits = torch.zeros(n_tiles, k_actions, device=device, dtype=torch.int32)
        self.embeddings = torch.zeros(n_tiles, dim, device=device, dtype=torch.float16)
        self.prototypes = torch.zeros(n_tiles, dim, device=device, dtype=torch.float16)
    
    def conservation_cv(self):
        """Compute CV on GPU, return scalar to CPU."""
        score_means = self.scores.sum(dim=1) / self.visits.clamp(min=1).sum(dim=1)
        cv = score_means.std() / score_means.mean().clamp(min=1e-8)
        return cv.item()  # Single scalar: 4 bytes over PCIe
    
    def extract_policy(self, top_k=57):
        """Extract hot-path tiles — small data transfer."""
        importance = self.scores.var(dim=1)  # (N,) — high variance = informative
        top_indices = importance.topk(top_k).indices
        return self.scores[top_indices].cpu()  # 57 × 9 × 4B = 2KB transfer
```

### 3.5 PCIe Bandwidth Budget

PCIe 4.0 x8 = 15.75 GB/s bidirectional (theoretical), ~12 GB/s practical.

| Data Flow | Size per batch (B=10K) | Transfer time | % of budget |
|-----------|----------------------|---------------|-------------|
| States: CPU→GPU | B × 27B (raw TTT) = 270KB | ~22µs | 0.2% |
| States: CPU→GPU (FP16 embedded) | B × 128B = 1.28MB | ~107µs | 0.9% |
| Results: GPU→CPU (scalar CV) | 4B | ~1µs | 0% |
| Results: GPU→CPU (policy) | 2KB | ~1µs | 0% |
| **Total per batch** | ~1.55MB | **~130µs** | **~1%** |

**PCIe is NOT the bottleneck.** Even at 100× the batch rate, we'd use only 100% of PCIe bandwidth. The pipeline is firmly compute-bound.

---

## 4. Scalability Limits — Before Saturating VRAM, Bandwidth, Compute

### 4.1 VRAM Limit

| # Tiles | K | dim | Score matrix | Embeddings | Total | % VRAM (5.5GB) |
|---------|---|-----|-------------|------------|-------|----------------|
| 1K | 9 | 64 | 36KB | 128KB | ~0.3MB | 0.005% |
| 10K | 9 | 64 | 360KB | 1.28MB | ~3.1MB | 0.06% |
| 100K | 9 | 64 | 3.6MB | 12.8MB | ~30MB | 0.5% |
| 1M | 9 | 64 | 36MB | 128MB | ~300MB | 5.5% |
| 10M | 9 | 64 | 360MB | 1.28GB | ~3.0GB | 55% |
| 31M | 9 | 64 | 1.1GB | 4.0GB | ~5.5GB | **100%** |

**Crossover:** ~31M tiles at dim=64, K=9 fills VRAM. For realistic workloads (1K-100K tiles), VRAM usage is negligible.

### 4.2 Memory Bandwidth Limit

RTX 4050: 192 GB/s. Every pipeline pass reads embeddings + prototypes + writes scores.

Bytes touched per batch (B queries, N tiles):
- Read embeddings: B × 64 × 2B = 128B bytes
- Read prototypes: N × 64 × 2B = 128N bytes  
- Write similarities: B × N × 4B = 4BN bytes
- Read+write scores: 2 × N × K × 4B = 8NK bytes

Total: 128B + 128N + 4BN + 8NK bytes

For B=10K, N=10K, K=9: 1.28MB + 1.28MB + 400MB + 0.72MB ≈ **403MB per batch**  
Bandwidth-limited time: 403MB / 192GB/s ≈ **2.1ms**

| Scale | Bandwidth time | Compute time | Bound? |
|-------|---------------|-------------|--------|
| B=1K, N=1K | 0.04ms | 0.01ms | **Bandwidth** |
| B=10K, N=10K | 2.1ms | 0.13ms | **Bandwidth** |
| B=10K, N=100K | 40ms | 1.3ms | **Bandwidth** |
| B=100K, N=10K | 20ms | 1.3ms | **Bandwidth** |

**The pipeline is bandwidth-bound at every scale.** This is expected — dim=64 × K=9 is tiny, so arithmetic intensity (FLOPs/byte) is low. Tensor Cores are wasted on such small dimensions.

### 4.3 Compute Limit

RTX 4050 peak: ~97 TFLOPS (FP16 Tensor Core) or ~15 TFLOPS (FP32 CUDA).

The embedding matmul (B × 64) × (64 × N) requires 2BN×64 FLOPs.

| Scale | FLOPs | Time @ 15 TFLOPS | Time @ 97 TFLOPS |
|-------|-------|-------------------|-------------------|
| B=1K, N=1K | 128M | 8.5µs | 1.3µs |
| B=10K, N=10K | 12.8G | 853µs | 132µs |
| B=10K, N=100K | 128G | 8.5ms | 1.3ms |
| B=100K, N=10K | 128G | 8.5ms | 1.3ms |

At B=10K, N=10K: compute=132µs (Tensor Core) vs bandwidth=2.1ms → **15× bandwidth-bound**.

### 4.4 PCIe Transfer Limit

PCIe is the bottleneck only if we transfer full data every batch. With zero-copy design (data stays on GPU), PCIe moves only:
- Input states: B × 128B per batch
- Output scalars: negligible

At B=100K: 12.8MB per batch → 12.8MB / 12GB/s ≈ 1ms. This is comparable to GPU processing time at B=10K scale.

**PCIe becomes the bottleneck when B > 100K and we re-transfer embeddings every frame.** But embeddings should stay on GPU — so PCIe rarely matters.

### 4.5 Summary: The Real Bottleneck Hierarchy

```
1. VRAM:    Not a constraint until 31M tiles (dim=64, K=9)
2. PCIe:    Not a constraint with zero-copy design
3. Compute: Not a constraint — Tensor Cores are overkill for dim=64
4. Bandwidth: THE constraint at ALL scales — 192 GB/s limits throughput
5. CPU feed:  24 Ryzen threads generate ~500 states/sec/thread = 12K states/sec
             → GPU processes 12K states in ~225µs
             → GPU is 99.98% idle waiting for CPU
```

**The system is CPU-feed-bound, not GPU-bound.** The RTX 4050 can process states 5,000× faster than the Ryzen can generate them. This has profound implications:

- **No need to optimize GPU kernels** — the GPU is already waiting
- **The optimization target is CPU game simulation throughput**
- **GPU should do more per state** (higher-dim embeddings, more complex SVD, etc.) to justify its presence
- **Or:** run multiple games in parallel to keep GPU fed

---

## 5. Bottleneck Analysis — Compute vs Memory vs Transfer at Each Scale

### 5.1 Roofline Model

```
Arithmetic Intensity (FLOPs/byte) = 2 × 64 / (64 × 2B) = 1.0 for dim=64

RTX 4050 Roofline:
  - Ridge point: BW × AI = 192 GB/s × 1.0 = 192 GFLOPS
  - Peak FP16: 97,000 GFLOPS
  - Peak FP32: 15,000 GFLOPS
  
  AI = 1.0 is far below the ridge point → deeply memory-bound
  
  To reach compute-bound: need AI > 97,000/192 = 505 FLOPs/byte
  At dim=64: AI = 2×64 / (3 × 64 × 2) = 0.67 (even worse)
  
  To reach compute-bound: need dim > 505 × 3 × 2 / 2 = 1,515 dimensions
  → dim=1536+ would make the matmul compute-bound on Tensor Cores
```

### 5.2 Per-Kernel Bottleneck Classification

| Kernel | FLOPs/byte | Bound | Bottleneck | Optimization |
|--------|-----------|-------|------------|-------------|
| Hash | ~0.5 | Memory | State reads | Batch large states |
| Embed (GEMM) | 1.0 (dim=64) | Memory | Prototype reads | Cache prototypes in shared memory |
| Search (top-K) | 0.25 | Memory | Similarity reads | Warp-level top-K (avoid global reads) |
| Evolve (scatter) | 0.1 | Atomic | atomicAdd contention | Per-SM local accumulators, periodic flush |
| SVD (incremental) | 50+ | Compute | cuSOLVER overhead | Batch multiple SVD updates |

### 5.3 Optimization Strategy by Bound Type

**Memory-bound kernels (hash, embed, search):**
- Use FP16 everywhere (halves memory traffic)
- Shared memory tiling for prototype reads
- Loop tiling: process in blocks that fit in L2 cache (4MB on RTX 4050)
- `__ldg()` for read-only data (separate read cache)

**Atomic-bound kernels (evolve):**
- Per-block local accumulators in shared memory
- Flush to global memory every 1K updates
- Warp-aggregated atomics (compute capability 8.x)
- Alternative: batch updates and sort-then-reduce

**Compute-bound kernels (SVD):**
- Not currently — but could be with higher-rank SVD
- Batch multiple small SVDs into one large batch
- Use Tensor Cores for the augmented matrix multiply

### 5.4 Practical Throughput Projections

Assuming bandwidth-optimized kernels (shared memory tiling, FP16):

| Workload | States/sec | GPU Utilization | CPU Feed Rate | Saturation |
|----------|-----------|-----------------|---------------|------------|
| TTT (dim=64, K=9, 1K tiles) | ~1B/sec | 0.1% | 12K/sec | **CPU-bound** |
| TTT (dim=64, K=9, 100K tiles) | ~200M/sec | 1% | 12K/sec | **CPU-bound** |
| General (dim=384, K=32, 1M tiles) | ~10M/sec | 15% | 12K/sec | **CPU-bound** |
| Multi-game (24 games × 12K/sec) | ~290K/sec | 5% | 288K/sec | **Near balanced** |

**The system only reaches balance when running 24+ games simultaneously.** Single-game operation leaves the GPU at <1% utilization.

### 5.5 Recommendation: Multi-Game Batch Architecture

To justify GPU usage, the architecture should:

1. **Always batch across games.** The GPU Tile Factory pattern — 24+ games generating states simultaneously, all fed to GPU in one batch.
2. **Increase embedding dimension.** dim=64 wastes Tensor Cores. Consider dim=256 or dim=512 for better compute utilization.
3. **Use the GPU for more than search.** Run SVD, conservation checks, and policy compilation on GPU too — amortize the fixed costs.
4. **Consider async compilation.** The GPU doesn't need to be in the hot loop for single-game play. Use it for offline compilation and batch analysis.

---

## 6. Architecture Summary

### 6.1 The Unified Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    UNIFIED GPU TILE PIPELINE                     │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  CPU FEED LAYER (Ryzen 5900X, 24 threads)                │   │
│  │                                                           │   │
│  │  Thread 0..23: Game simulations → (state, action, outcome)│   │
│  │  Each thread produces ~500 states/sec                     │   │
│  │  Aggregate: ~12K states/sec (single game)                 │   │
│  │         or ~288K states/sec (24 parallel games)           │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                      │
│                    Pinned staging buffers                         │
│                    (async DMA over PCIe 4.0 x8)                  │
│                           │                                      │
│  ┌────────────────────────▼─────────────────────────────────┐   │
│  │  GPU PROCESSING LAYER (RTX 4050, 6GB VRAM)               │   │
│  │                                                           │   │
│  │  ┌─────────────────────────────────────────────────────┐ │   │
│  │  │ Double-buffered input (B × 64 FP16)                 │ │   │
│  │  │ Buffer A: GPU processing | Buffer B: CPU filling    │ │   │
│  │  └──────────────────────┬──────────────────────────────┘ │   │
│  │                         │                                  │   │
│  │  ┌──────┐  ┌───────┐  ┌──────┐  ┌──────┐  ┌──────────┐ │   │
│  │  │ Hash │→→│ Embed │→→│Search│→→│Evolve│→→│ Inc. SVD │ │   │
│  │  │      │  │(GEMM) │  │(top-K│  │(sct. │  │(rank ≤8) │ │   │
│  │  │ 2µs  │  │ 15µs  │  │10µs  │  │ 5µs  │  │  50µs    │ │   │
│  │  └──────┘  └───────┘  └──────┘  └──────┘  └──────────┘ │   │
│  │       (all on CUDA stream 0, sequential within batch)    │   │
│  │                                                           │   │
│  │  Tile state: ALL in VRAM (SoA layout, 256B aligned)       │   │
│  │  Capacity: 31M tiles @ dim=64, K=9                       │   │
│  │  Policy extraction: GPU-side, only 2KB crosses PCIe       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Throughput: 85M states/sec (full pipeline, B=100K)             │
│  Bottleneck: CPU feed rate (12K states/sec single game)         │
│  GPU utilization: <1% single game, ~5% 24 parallel games        │
│                                                                  │
│  Conservation monitoring: on GPU, single scalar to CPU          │
│  Policy compilation: on GPU, extract hot paths on demand        │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Tile storage | SoA in VRAM | Coalesced access, not AoS |
| Precision | FP16 embed/protos, FP32 scores | Bandwidth savings on large arrays |
| Sync model | Double-buffered async DMA | Overlaps CPU fill with GPU compute |
| PCIe traffic | Minimal (states in, scalars out) | Zero-copy — data stays on GPU |
| Search | Chunked matmul + warp top-K | Avoids materializing full similarity matrix |
| SVD | Incremental (Brand's algorithm) | O(R²×B) not O(N×K) per update |
| Score updates | Atomic scatter-add | Acceptable contention at <100K tiles |
| Multi-game | Batch across 24+ games | Only way to justify GPU utilization |

### 6.3 Scaling Roadmap

| Phase | Tiles | Games | GPU Util | Bottleneck | Key Insight |
|-------|-------|-------|----------|------------|-------------|
| Now (CPU) | 754 | 1 | 0% | CPU compute | CPU-only is fine for small scale |
| Phase 1 | 10K | 1 | <1% | CPU feed | GPU adds latency, not throughput |
| Phase 2 | 10K | 24 | ~5% | CPU feed | Multi-game justifies GPU |
| Phase 3 | 100K | 24 | ~15% | Bandwidth | Embeddings fill L2 cache |
| Phase 4 | 1M | 24 | ~50% | Bandwidth | Streaming search required |
| Phase 5 | 10M+ | 100+ | ~80% | Compute | Tensor Cores finally engaged |

**Phase 5 would require multi-node or a bigger GPU.** The RTX 4050 is overkill for current workloads but provides headroom for 1000× growth.

### 6.4 The Honest Assessment

The RTX 4050 is **massively over-provisioned** for the current tile field workload. At dim=64 and K=9 with <1K tiles, the GPU finishes in microseconds and spends 99.99% of its time idle. The architecture that makes sense:

1. **Short-term:** CPU-only for single-game interactive play. GPU for batch analysis (10K+ game compilation, SVD, conservation checks).
2. **Medium-term:** GPU Tile Factory — 24+ parallel games, GPU does all scoring and compilation. Justifies the GPU.
3. **Long-term:** Higher-dimensional embeddings (dim=384+), million-tile fields, real-time tournament play. GPU becomes essential.

The architecture is designed for Phase 2+, but should degrade gracefully to CPU-only for Phase 1.

---

*"The GPU is a drag racer idling at a stoplight. The CPU is a bicycle that's already moving. For short trips, the bicycle wins. But when you need to move 24 truckloads of tiles across town, the drag racer finally wakes up."*
