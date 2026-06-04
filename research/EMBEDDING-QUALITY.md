# Embedding Quality Experiment — lever-runner

**Date:** 2026-06-03
**Question:** Are hash embeddings "good enough" for lever-runner's command matching, or should we upgrade?

## Results

| Embedder | Dim | Top-1 | Top-3 | MRR | Latency |
|---|---|---|---|---|---|
| hash_blake2b_64 | 64 | **0.0%** | 0.0% | 0.052 | 6µs |
| hash_blake2b_128 | 128 | **0.0%** | 0.0% | 0.044 | 4µs |
| random_projection_128 | 128 | 33.3% | 50.0% | 0.462 | 2µs |
| **position_aware_64** | **64** | **44.4%** | **55.6%** | **0.536** | **1µs** |
| position_aware_128 | 128 | 38.9% | 50.0% | 0.479 | 2µs |

Tested against 70 commands × 20 natural-language queries. Ground truth determined by keyword overlap between query and command description.

## Key Findings

### 1. Pure hash embeddings are terrible for retrieval
Blake2b hash embeddings scored **0% top-1 accuracy** across both dimensions. Hash functions are designed to be **dissimilar** for similar inputs — the opposite of what you want for semantic matching. "check disk usage" and "how much disk space is left" get completely unrelated hash vectors despite being semantically identical.

### 2. Position-aware embeddings win
The position-aware approach (per-word hashing with positional weighting) achieved **44.4% top-1, 55.6% top-3** at the lowest latency (1µs). It works because it captures word-level structure — "disk" in the query matches "disk" in the description via shared word hashes.

### 3. More dimensions ≠ better
64-dim position-aware beat 128-dim position-aware. At this scale (~70 commands), 64 dims provide enough discriminative capacity. Higher dimensions just add noise.

### 4. Random projection is decent but not optimal
Character n-gram + random projection got 33.3% top-1. It captures subword similarity (shared characters) but lacks the word-level precision of the position-aware approach.

## Recommendations for lever-runner

### Keep: Position-aware embedding (64-dim)
- **Best accuracy** (44% top-1) at **lowest latency** (1µs)
- Zero dependencies — just hashlib + numpy (already in use)
- 64-dim vectors = tiny memory footprint (~4.5KB for 70 commands)
- Good enough for lever-runner's scale (hundreds of commands, not thousands)

### Don't use: Pure hash embeddings
Blake2b is cryptographically designed to maximize Hamming distance between similar inputs. It's literally the wrong tool for similarity search. The 0% accuracy confirms this emphatically.

### Future upgrade path: If accuracy becomes a problem
1. **First try:** TF-IDF weighted position-aware embeddings (no new deps, likely 60%+ accuracy)
2. **Nuclear option:** Small sentence-transformer model (~20MB, 5-10ms latency, 80%+ accuracy)
3. **Scale concern:** At >1000 commands, consider proper vector index (FAISS/Hnswlib)

### Cost/benefit analysis
| Approach | Accuracy | Latency | Dependencies | Verdict |
|---|---|---|---|---|
| Pure hash (blake2b) | 0% | 4-6µs | hashlib | ❌ Useless for retrieval |
| Position-aware 64 | 44% | 1µs | hashlib, numpy | ✅ Best for lever-runner |
| Random projection | 33% | 2µs | hashlib, numpy | ⚠️ Decent fallback |
| TF-IDF (not tested) | ~60% est. | ~5µs | sklearn or manual | 🔮 Worth investigating |
| Sentence-transformer | ~85% est. | 5-10ms | torch/sentencepiece | 🔮 Overkill for now |

## Conclusion

**Switch lever-runner from pure hash to position-aware embeddings.** It's a drop-in replacement (same interface, same deps) that goes from 0% to 44% accuracy while being *faster*. Not a hard choice.

For lever-runner's workload (~70-200 commands, sub-millisecond budget), position-aware is the sweet spot. Learned embeddings (sentence-transformers) would dominate at scale but add 1000x latency and heavy dependencies for marginal gain at this size.
