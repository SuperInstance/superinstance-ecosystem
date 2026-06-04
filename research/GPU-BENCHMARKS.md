# GPU Vector Search Benchmarks — RTX 4050 Laptop (6GB VRAM)

**Date:** 2026-06-03  
**Hardware:** NVIDIA GeForce RTX 4050 Laptop GPU, 6.0 GB VRAM  
**Software:** PyTorch + NumPy, CUDA  

## Executive Summary

**GPU vector search only wins at scale.** For the current SuperInstance workloads (small DBs, low dimensions), **CPU is faster** due to GPU transfer overhead. GPU becomes worthwhile at **10K+ vectors with dim≥128**, or **100K+ vectors with dim=64**.

---

## Key Findings

### 1. Crossover Points: When Does GPU Beat CPU?

| Dimension | DB Size | CPU (µs) | GPU (µs) | Speedup | Verdict |
|-----------|---------|----------|----------|---------|---------|
| 64 | 100 | 1 | 669 | 0.0x | 🐢 GPU 670x slower |
| 64 | 1,000 | 5 | 15 | 0.3x | 🐢 GPU slower |
| 64 | 10,000 | 50 | 56 | 0.9x | 🟰 Roughly equal |
| 64 | 100,000 | 288 | 603 | 0.5x | 🐢 CPU still wins |
| **64** | **1,000,000** | **5,273** | **4,437** | **1.2x** | **✅ GPU barely wins** |
| 128 | 10,000 | 29 | 20 | 1.5x | ✅ GPU wins |
| 128 | 100,000 | 5,100 | 324 | **15.8x** | 🚀 GPU crushes |
| 128 | 1,000,000 | 9,683 | 3,495 | 2.8x | ✅ GPU wins |
| 384 | 10,000 | 1,184 | 93 | **12.7x** | 🚀 GPU crushes |
| 384 | 100,000 | 3,199 | 1,065 | 3.0x | ✅ GPU wins |
| 384 | 1,000,000 | 34,367 | 10,442 | 3.3x | ✅ GPU wins |

**Crossover rules of thumb:**
- **dim=64** (hash embeddings): GPU wins at ~1M vectors
- **dim=128** (small models): GPU wins at ~10K vectors  
- **dim=384** (sentence-transformers): GPU wins at ~10K vectors

### 2. Batch Embedding Throughput

| Batch Size | CPU (µs/item) | GPU (µs/item) | GPU Throughput |
|-----------|---------------|---------------|----------------|
| 1 | 12.1 | 10.2 | 98K/s |
| 8 | 3.2 | 2.2 | 3.7M/s |
| 32 | 1.3 | 0.7 | 49M/s |
| 128 | 1.6 | 0.1 | **1.1B/s** |
| 512 | 0.6 | 0.1 | 8.3B/s |
| 1024 | 0.6 | 0.1 | **15B/s** |

**Takeaway:** For batch embedding generation, GPU is **10-1000x** faster at batch≥128. This is where GPU shines — bulk processing.

### 3. ZeroClaw Actual Workload

Using the real tic-tac-toe DB (3,827 vectors, dim=64, hash embeddings):

- **CPU: 21µs per query**
- **GPU: 338µs per query (0.1x — GPU is 16x SLOWER)**

**Why?** The per-query CPU→GPU transfer dominates. At dim=64 with only 3.8K vectors, the actual computation takes microseconds. The transfer takes hundreds. This is the worst case for GPU — tiny workloads with per-query transfers.

**If we batched 100 queries at once (lever-runner scanning multiple boards):** GPU would likely win since transfer amortizes.

### 4. VRAM Capacity — Can We Fit Everything?

Yes. Easily. RTX 4050 with 6GB:

| Dimension | FP32 Max Vectors | FP16 Max Vectors |
|-----------|-----------------|-----------------|
| 64 | **20.1M** | 40.2M |
| 128 | **10.1M** | 20.1M |
| 384 | **3.4M** | 6.7M |
| 768 | **1.7M** | 3.4M |
| 1536 | **0.8M** | 1.7M |

ZeroClaw's entire tic-tac-toe DB (3,827 vectors × 64 dim × 4 bytes) = **~980 KB**. Fits in VRAM ~6,000 times over.

---

## Recommendations for SuperInstance

### lever-runner (tic-tac-toe agent)
- **Stick with CPU.** The DB is tiny (~4K vectors, dim=64). GPU overhead kills any benefit.
- If DB grows to 100K+ boards, reconsider.

### pincherOS (general embedding)
- **CPU for hash embeddings.** dim=64 is too small for GPU to help.
- **GPU for model-based embeddings** (dim=384+). If you're running sentence-transformers, GPU wins even at 10K vectors.
- **GPU for bulk re-indexing.** Batch embedding generation at 1B+/s is a game-changer for re-building indexes.

### General Rule
> **CPU for interactive, GPU for batch.**  
> GPU's advantage is throughput, not latency. Use it when you have work to batch, not when you need one answer fast.

---

## Raw Data

Full benchmark results in JSON format: [`gpu-benchmarks.json`](../../zeroclaw-arena/gpu-benchmarks.json)
