# GRAND-INTEGRATION.md — Deep Synthesis of All Research

**Date:** 2026-06-03  
**Status:** Executive Synthesis — contradictions exposed, experiment sequenced  
**Sources:** GPU-PARADIGMS.md, GPU-ARCHITECTURE.md, DEPLOYMENT-TOPOLOGY.md, CROSS-LANGUAGE-SCHEMAS.md, metal benchmarks

---

## 1. Viable vs Inviable Paradigms (With Evidence)

### VIABLE — Build These

| Paradigm | Evidence | Why Viable |
|----------|----------|------------|
| **CPU-first for <50K vectors** | Hash: 128ns, embed: 1.73µs, search: 1.47ms at 10K. GPU crossover at ~10K. | Proven metal numbers. The Rust carapace dominates at current scale. |
| **GPU batch factory (24+ games)** | Tensor cores FP16 19.6× faster. GPU 6.8× at 1M vectors. | Only justifies GPU at multi-game scale. Single-game GPU is overkill. |
| **Embedding search (NOT hash search)** | Hash search FAILS on paraphrases — Gate 2 is mandatory. | Hard empirical result. Hash is a Gate 1 filter, never the final answer. |
| **WASM browser target** | 71KB gzip. Wire format defined. Test vectors specified. | Smallest viable deployment. Cross-language schemas guarantee correctness. |
| **ARM NEON inference** | 4-core Ampere A1 has 24GB RAM → 100K vectors in-memory at ~25MB. | Deployment topology confirms ARM as Loom's box. No GPU needed for inference. |
| **ESP8266 compiled policies** | 80KB RAM is tight but tile-compiler output fits in 50-200KB flash. | Only viable as a pre-compiled target. No runtime compute. |
| **Double-buffered async pipeline** | PCIe 4.0 x8 = 15.75 GB/s. Data transfer is ~1% of bandwidth at B=10K. | Quick win. Easy to implement. 1.8× throughput for free. |
| **Incremental SVD (Brand's)** | Rank-1 captures 8.9× compression; viable at 30% of tiles. GPU does tiny 108×108 SVD in ~1µs. | Already proven. Incremental is the right algorithm. |

### INViable / Premature — Don't Build These Yet

| Paradigm | Evidence | Why Not |
|----------|----------|---------|
| **GPU-native tile fields (Paradigm 1)** | Architecture doc proves GPU utilization is **<1% for single game**. CPU feed rate = 12K states/sec; GPU processes 85M/sec. | GPU is 7000× over-provisioned. Moving tiles to VRAM adds complexity for zero throughput gain at current scale. Build when hitting 100K+ tiles or 24+ parallel games. |
| **Tensor core FP16 compression (Paradigm 3)** | Claimed 800× speedup on SVD. But incremental SVD on a 108×108 matrix is already 1µs. 800× of 1µs = 1.25ns — impossible (memory latency alone is ~100ns). | The SVD step is already trivially fast. Tensor core speedup is real but applies to an already-negligible cost. Over-engineering. |
| **CUDA graph capture (Paradigm 5)** | "50× reduction in dispatch overhead." But dispatch overhead is 50µs per cycle, and GPU is idle 99.99% of the time anyway. | Saving 49µs on a GPU that's waiting 100ms for CPU data is pointless. Only matters at Phase 5 (10M+ tiles, 100+ games). |
| **Warp democracy (Paradigm 2)** | "32× strategy exploration." But strategy space is degenerate — conservation law proves many near-optimal strategies exist. | Deeper search in a degenerate space doesn't improve outcomes. The conservation law makes most strategies equivalent. Exploration is cheap; the space is small. |
| **OpenCL portable kernels** | No OpenCL hardware in the stack. Oracle ARM64 has no GPU. ESP8266 has no GPU. Browser uses WASM. | No target needs it. Build when deploying to AMD/Mali hardware — which isn't on any roadmap. |
| **Vulkan compute (Paradigm 8)** | Android is "Loom's eventual target" — no concrete timeline. Mobile Vulkan drivers are buggy. | Speculative. The 30-second thermal throttle makes sustained compute impossible. Revisit when there's a real Android deployment. |
| **SYCL/oneAPI (Paradigm 9)** | No Intel GPU in the hardware roster. The doc itself rates it "Low priority." | Agreed. Don't build. |

---

## 2. Deployment Scenario → Paradigm Mapping

| Scenario | Tiles | Games | Right Paradigm | Wrong Paradigm |
|----------|-------|-------|---------------|----------------|
| **Interactive single-game (TTT)** | <1K | 1 | CPU Rust carapace + numpy embed | GPU anything — latency dominates, GPU adds overhead |
| **Batch analysis / compilation** | 1K-50K | 1 | CPU brute-force embed search (1.47ms at 10K) | GPU — only marginally faster, not worth the setup |
| **Multi-game factory (24 games)** | 10K-100K | 24 | GPU batch matmul + tensor cores FP16 | CPU — can't handle 24× throughput |
| **Loom's box (ARM inference)** | 100K cached | N/A | NEON cosine similarity, CPU-only | GPU — no GPU on ARM64. OpenCL — no device. |
| **Browser policy viewer** | N/A | N/A | WASM, 71KB gzip, scalar cosine | SIMD — not portable in WASM yet |
| **Edge ESP8266** | Compiled binary only | N/A | Pre-compiled C from tile-compiler | Any runtime compute — 80KB RAM |
| **Cloud VPS cold standby** | 10K cached | N/A | SSE/AVX scalar, 1GB RAM | CUDA — no GPU on €3 VPS |

**Key insight:** The system has **six distinct compute profiles** and no single paradigm covers them all. The fallback chain (CUDA → OpenCL → NEON → SSE → Scalar) is correct architecturally but OpenCL can be dropped — nothing in the stack uses it.

---

## 3. Contradictions Between Documents

### Contradiction 1: GPU Utilization

- **GPU-PARADIGMS.md** (Hermes): Proposes 9 GPU paradigms, rates 3 as "🔥 High" priority. Implies GPU is essential.
- **GPU-ARCHITECTURE.md** (Seed Pro): Proves GPU utilization is **<1% for single game**, 99.99% idle. Explicitly states "the GPU is a drag racer idling at a stoplight."
- **Resolution:** Architecture doc is correct. GPU paradigms doc is ideation without grounding in the feed-rate bottleneck. Most GPU paradigms should be shelved until multi-game factory is real.

### Contradiction 2: SVD Performance Claims

- **GPU-PARADIGMS.md:** Claims "800× speedup for compression step" via tensor cores. Estimates current CPU SVD at ~800µs.
- **GPU-ARCHITECTURE.md:** Shows incremental SVD on a 108×108 matrix takes ~1µs (already using cuSOLVER for tiny matrices).
- **Resolution:** The 800µs figure is for full SVD on all tiles. Incremental SVD reduces this to ~1µs. Tensor core speedup on 1µs is meaningless. Both docs agree incremental SVD is the right approach — but the 800× claim is misleading because it compares full-SVD-on-CPU to tensor-core-SVD, when the real comparison should be incremental-SVD-on-CPU vs incremental-SVD-on-GPU (both ~1-50µs).

### Contradiction 3: Deployment Complexity vs Reality

- **DEPLOYMENT-TOPOLOGY.md:** Defines 5 platforms (workstation, ARM64, ESP8266, browser, cloud VPS) with full deployment procedures.
- **CROSS-LANGUAGE-SCHEMAS.md:** Defines wire format, IPC protocol, WASM API, CUDA kernel interface, test vectors, error codes.
- **Reality:** Only **workstation** and **WASM** have implementation. ARM64 has SSH access but no deployed code. ESP8266 is a concept. Cloud VPS doesn't exist.
- **Resolution:** The schemas are good forward engineering. But building multi-platform deployment before validating the core pipeline on one platform is premature. Ship workstation + WASM first.

### Contradiction 4: Hash vs Embedding for Gate 2

- **Metal benchmarks:** Hash search FAILS on paraphrases. Embedding search is essential.
- **GPU-ARCHITECTURE.md:** Pipeline starts with Hash kernel (state → embedding), then Embed kernel (matmul). Treats hash as a distinct step from embedding.
- **GPU-PARADIGMS.md:** Paradigm 1 proposes GPU-native hashing to eliminate the CPU round-trip.
- **Resolution:** The "hash" in the architecture is actually embedding generation (a position-aware hash that produces 64 floats). It's not the same as the BLAKE3 hash used for Gate 1 exact matching. The naming is confusing. **BLAKE3 hash → Gate 1 exact match. Position-aware embedding → Gate 2 fuzzy match.** Both are needed but serve different gates.

### Contradiction 5: VRAM Budget

- **GPU-ARCHITECTURE.md:** Claims 5.5GB usable VRAM, fits 31M tiles at dim=64.
- **GPU-ARCHITECTURE.md (workspace section):** Similarity matrix for B=10K × N=100K = 3.6GB — "too large."
- **Resolution:** Tile storage is tiny but workspace for full-batch similarity search is enormous. Chunked search is mandatory at 100K+ tiles. The 31M tile capacity is misleading — you can store them but can't search them in one pass.

---

## 4. Integration Build Order with Dependencies

```
Phase 0: FOUNDATION (prerequisites for everything)
├── 0a. Cross-language test vectors + conformance harness
│   └── Depends on: nothing (CROSS-LANGUAGE-SCHEMAS.md §5)
│   └── Validates: bit-identical BLAKE3, float32, wire format across Rust/Python/WASM
├── 0b. Wire format implementation in Rust + Python
│   └── Depends on: 0a (test vectors to validate against)
│   └── Implements: tile binary format from CROSS-LANGUAGE-SCHEMAS.md §1
└── 0c. UDS IPC protocol (fastloop-guard)
    └── Depends on: 0a
    └── Implements: request/response schemas from §2

Phase 1: CORE PIPELINE (single-machine, workstation only)
├── 1a. Rust carapace: BLAKE3 hash + position-aware embedding (128ns target)
│   └── Depends on: 0a (hash test vectors)
│   └── Status: EXISTS — proven at 128ns
├── 1b. Gate 2: embedding search (numpy brute-force, <50K vectors)
│   └── Depends on: 1a (embeddings), 0b (wire format)
│   └── Status: EXISTS — 1.73µs embed, 1.47ms search at 10K
├── 1c. Gate 3: LLM deep loop (lever-runner)
│   └── Depends on: 0c (IPC to fastloop-guard)
│   └── Status: EXISTS — 500ms-2s depending on LLM
└── 1d. End-to-end three-gate integration test
    └── Depends on: 1a + 1b + 1c
    └── Produces: validated single-game pipeline

Phase 2: WASM PORT (first deployment beyond workstation)
├── 2a. Rust → wasm32 compilation (lever-runner-wasm)
│   └── Depends on: 0a (conformance harness in WASM)
│   └── Target: 71KB gzip (proven)
├── 2b. Browser policy viewer UI
│   └── Depends on: 2a
└── 2c. Static hosting + CDN
    └── Depends on: 2b

Phase 3: ARM64 DEPLOYMENT (Loom's box)
├── 3a. Cross-compilation toolchain setup
│   └── Depends on: 0a (ARM test vectors)
├── 3b. NEON embedding benchmark (Experiment 1 from DEPLOYMENT-TOPOLOGY.md)
│   └── Depends on: 3a
├── 3c. Full three-gate smoke test on ARM64 (Experiment 7)
│   └── Depends on: 3b
└── 3d. Policy sync: workstation → ARM64 (git-based)
    └── Depends on: 3c

Phase 4: GPU BATCH FACTORY (when multi-game is needed)
├── 4a. Double-buffered async pipeline (quick win, 1.8× throughput)
│   └── Depends on: 1d (stable CPU pipeline)
├── 4b. GPU batch embedding search (cuBLAS matmul)
│   └── Depends on: 4a
├── 4c. Multi-game state aggregation (24 games → 1 GPU batch)
    └── Depends on: 4b
└── 4d. Tensor core FP16 for batch inference
    └── Depends on: 4c

Phase 5: EDGE (ESP8266) — only after Phase 3 validates policies
├── 5a. Tile-compiler: policy → C binary
│   └── Depends on: 1d (validated policies)
└── 5b. ESP8266 flash + OTA update
    └── Depends on: 5a

DEFERRED: GPU-native tiles, warp democracy, CUDA graphs, OpenCL, Vulkan, SYCL
```

---

## 5. THE ONE Experiment

### **Multi-Game GPU Batch Factory End-to-End Benchmark**

**What:** Run 24 simultaneous TTT/C4 games, aggregate all state queries into one GPU batch, measure end-to-end throughput and compare to 24× single-game CPU throughput.

**Why this one experiment confirms/invalidates most hypotheses:**

| Hypothesis | What This Experiment Tests |
|------------|---------------------------|
| GPU is worth the overhead | If 24-game GPU batch isn't ≥5× faster than 24× CPU, GPU is dead weight |
| Tensor cores help at dim=64 | Measure FP16 vs FP32 matmul at dim=64 — if <2× speedup, tensor cores are irrelevant |
| CPU feed rate is the bottleneck | If GPU processes batch in <1ms while CPU takes 100ms to generate states, confirmed |
| Double-buffering helps | A/B test with and without — measure GPU idle time |
| Multi-game is viable | If state aggregation adds >10% overhead, the architecture is wrong |
| The crossover at 10K vectors holds | Run at 1K, 10K, 100K vectors and plot the crossover curve — validate or refute |
| Embedding quality survives FP16 | Compare FP32 vs FP16 search accuracy — if >1% quality loss, FP16 is premature |

**Implementation:**
```python
# One experiment to rule them all
import torch, time, numpy as np

def run_the_experiment(n_games=24, n_tiles_list=[1000, 10000, 100000],
                       dims=[64, 128, 256, 384], precisions=['fp32', 'fp16']):
    results = {}
    for n_tiles in n_tiles_list:
        for dim in dims:
            for precision in precisions:
                dtype = torch.float16 if precision == 'fp16' else torch.float32
                
                # Generate tile prototypes (simulating compiled knowledge)
                prototypes = torch.randn(n_tiles, dim, device='cuda', dtype=dtype)
                
                # Simulate 24 games each producing 500 states
                batch = n_games * 500  # 12,000 queries
                queries = torch.randn(batch, dim, device='cuda', dtype=dtype)
                
                # GPU batch search
                torch.cuda.synchronize()
                t0 = time.perf_counter()
                similarities = torch.matmul(queries, prototypes.T)
                top_scores, top_indices = similarities.topk(10, dim=1)
                torch.cuda.synchronize()
                gpu_ms = (time.perf_counter() - t0) * 1000
                
                # CPU equivalent
                proto_cpu = prototypes.float().cpu().numpy()
                query_cpu = queries.float().cpu().numpy()
                t0 = time.perf_counter()
                sims = query_cpu @ proto_cpu.T
                cpu_ms = (time.perf_counter() - t0) * 1000
                
                # Quality check: do FP16 and FP32 agree on top-K?
                if precision == 'fp16':
                    fp32_proto = prototypes.float()
                    fp32_sims = torch.matmul(queries.float(), fp32_proto.T)
                    _, fp32_idx = fp32_sims.topk(10, dim=1)
                    agreement = (top_indices == fp32_idx).float().mean().item()
                else:
                    agreement = 1.0
                
                key = f"tiles={n_tiles}_dim={dim}_{precision}"
                results[key] = {
                    'gpu_ms': gpu_ms,
                    'cpu_ms': cpu_ms,
                    'speedup': cpu_ms / gpu_ms,
                    'fp16_agreement': agreement,
                    'gpu_util_pct': 0,  # Would need nsys for real measurement
                }
                print(f"{key}: GPU={gpu_ms:.1f}ms CPU={cpu_ms:.1f}ms "
                      f"speedup={cpu_ms/gpu_ms:.1f}× FP16_agree={agreement:.4f}")
    return results
```

**Success criteria:**
- GPU speedup ≥5× at n_tiles=100K (justifies GPU pipeline)
- FP16 agreement ≥99.5% (justifies FP16 for storage)
- Dim=64 is bandwidth-bound (validates roofline analysis)
- Dim=384 approaches compute-bound (validates Tensor Core engagement)

**Failure modes and what they mean:**
- GPU speedup <2× at all scales → abandon GPU pipeline, CPU-only is correct
- FP16 agreement <95% → FP16 is premature, stick with FP32
- Dim=64 is compute-bound → roofline analysis is wrong, re-examine kernel
- CPU feed can't saturate GPU at 12K states/sec → confirmed CPU-bound, GPU is premature

---

## 6. Honest Assessment: What's Over-Engineered, What's Missing

### Over-Engineered

1. **9 GPU paradigms (GPU-PARADIGMS.md).** The GPU processes in <1ms what takes the CPU 100ms to generate. Eight of nine paradigms solve a problem that doesn't exist yet. The document is intellectually interesting but practically premature.

2. **5-platform deployment topology.** Only 2 platforms (workstation, browser) have any implementation. Building ESP8266 and cloud VPS deployment procedures before the core pipeline is validated is cart-before-horse.

3. **Tensor core FP16 compression for SVD.** The incremental SVD on a 108×108 matrix takes ~1µs. Tensor cores would make it ~0.1µs. Saving 0.9µs on a step that runs once per batch is invisible.

4. **CUDA kernel interface in cross-language schemas.** No CUDA kernel exists. Defining the ABI before the algorithm is premature abstraction.

5. **Warp-level democratic voting.** Elegant idea, but the conservation law makes strategy search degenerate. More exploration in a degenerate space yields diminishing returns.

### Missing

1. **Real multi-game orchestration.** Every doc assumes 24 simultaneous games but none describes how to aggregate states from independent game loops into one GPU batch. This is the **critical missing piece** — the scheduler that collects (state, action, outcome) triples from 24 game threads and presents them as a single batch.

2. **FP16 quality validation.** Architecture doc assumes FP16 is fine for embeddings. Metal benchmarks show hash search fails on paraphrases — but no data on whether FP16 embeddings preserve cosine similarity ranking. The one experiment above tests this, but it's not been done yet.

3. **Conservation law implications.** Multiple docs mention that "score magnitudes are Penrose-conserved; strategies are degenerate." But no doc explores what this means for the architecture. If strategies are degenerate, you don't need 32-way warp democracy — you need 1 good strategy. The architecture should exploit degeneracy, not fight it.

4. **Latency budget for the full three-gate stack on real workloads.** Every doc quotes micro-benchmarks. Nobody has run 1000 real shell-command queries through Gate 1 → Gate 2 → Gate 3 and measured the distribution. The 250µs "confirmed" cache-hit latency is for a single well-formed query. Real queries will have misses, LLM timeouts, cache cold starts.

5. **Failure mode analysis.** What happens when: GPU driver crashes? ARM64 loses network? ESP8266 gets a corrupted policy? The fallback chain exists in theory but no doc tests degraded-mode operation.

6. **Cost analysis.** RTX 4050 draws 35-140W. The ARM64 box costs nothing (Oracle free tier). Running GPU batch 24/7 costs real electricity. No doc compares the cost/performance of GPU batch vs just buying a bigger ARM instance.

7. **Actual tile-compiler output.** Described as compiling policies to C for ESP8266. But no doc shows a real input/output example. What does a "compiled policy" look like? A decision tree? A lookup table? A neural network? This is the deliverable for edge deployment and it's undefined.

---

## The Bottom Line

**The system is CPU-feed-bound at every realistic scale.** The GPU is 7000× over-provisioned. The correct architecture for right now:

1. **CPU Rust carapace** for Gate 1 (hash) + Gate 2 (embedding search) — proven at 128ns/1.73µs
2. **GPU** reserved for batch analysis and multi-game factory — not in the hot loop
3. **WASM** as the first "other platform" — 71KB, works everywhere
4. **ARM64** as inference-only — NEON cosine, no GPU needed

Build Phase 0-2. Run THE experiment. Let data decide Phase 4.

Everything else is a fascinating engineering exercise that should stay in the `research/` folder until the data says otherwise.

---

*"Ship the bicycle. The drag racer can wait in the garage."*
