# Spectral Perturbation Test Results

**Date:** 2026-06-03
**Experiment:** #1 ranked from data analysis — testing if spectral isomorphism (>0.97 cosine similarity) is genuine or artifact

## Hypothesis

The data analysis found that spectral isomorphism across repos was "mostly an artifact of coding style and parser normalization." This experiment tests whether the similarity survives perturbations that should destroy style-based artifacts while preserving genuine structural invariants.

## Method

Four perturbation tests on call graphs from 3 Python repos (lever-runner, zeroclaw-arena, metal-lathe) + 2 Rust repos (pincherOS, fastloop-guard). Rust repos had 0 edges due to parser limitations (Rust function call extraction is harder), so results are from the 3 Python repos.

Signature method: Eigenvalue histogram (32 bins over [0,2]) + 12 graph-level statistics, normalized to unit vector.

## Results

### Baseline Similarity

| Pair | Cosine Similarity |
|------|------------------|
| lever-runner ↔ zeroclaw-arena | 0.9998 |
| lever-runner ↔ metal-lathe | 0.9964 |
| zeroclaw-arena ↔ metal-lathe | 0.9980 |

### Test 1: Randomized Function Names (preserve structure)

| Pair | Original | Perturbed | Delta |
|------|----------|-----------|-------|
| lever-runner ↔ zeroclaw-arena | 0.9998 | 0.9994 | -0.0004 |
| lever-runner ↔ metal-lathe | 0.9964 | 0.9977 | +0.0014 |
| zeroclaw-arena ↔ metal-lathe | 0.9980 | 0.9995 | +0.0015 |

**Average change: 0.0011**

### Test 2: Randomized Call Patterns (preserve function count)

| Pair | Original | Perturbed | Delta |
|------|----------|-----------|-------|
| lever-runner ↔ zeroclaw-arena | 0.9998 | 0.9993 | -0.0005 |
| lever-runner ↔ metal-lathe | 0.9964 | 0.9944 | -0.0020 |
| zeroclaw-arena ↔ metal-lathe | 0.9980 | 0.9914 | -0.0065 |

### Test 3: Vector Noise (direct perturbation)

Even at 50% noise level, similarity stays >0.999. The eigenvalue histogram bins are extremely sparse — most eigenvalues cluster near 0, making the normalized histogram dominated by a few bins regardless of noise.

## Verdict

**ISOMORPHISM IS GENUINE** — but with a critical caveat.

### What the data says

Randomizing function names changes similarity by only **0.0011** on average. This is definitively not a naming artifact. The spectral signature is genuinely capturing something structural.

### The critical caveat

The "something structural" is almost certainly **graph sparsity**. Here's the evidence:

1. **Even randomizing call patterns barely changes similarity** (max delta: -0.0065). If the invariant were about specific topological structure (e.g., presence of hubs, modularity), scrambling edges should destroy it.

2. **50% vector noise doesn't change similarity**. This means the signature has near-zero information content — it's dominated by a single dimension (the "empty bins" count).

3. **The eigenvalue histograms are nearly identical** because all call graphs are sparse (~5-8 calls per function, in graphs of 20-87 nodes). The normalized Laplacian eigenvalue distribution of any sparse graph looks the same: mostly values near 0 and 2, with a thin spread in between.

### Revised interpretation

The >0.97 similarity is **genuine but trivially explained**: it reflects the universal sparsity pattern of call graphs, not a deep structural invariant. All software call graphs are sparse directed graphs with similar degree distributions. Their Laplacian eigenvalue distributions are therefore nearly identical, regardless of what the code actually does.

This is like saying "all novels have similar word frequency distributions" — true, genuine, not an artifact, but also not revealing of deep structure.

### What would be genuinely interesting

Finding repos where the spectral signature *differs* meaningfully — e.g., comparing a highly modular codebase to a monolithic one, or comparing across paradigms (OOP vs functional). The current test shows the metric can't distinguish these.

## Files

- Experiment script: `~/repos/conservation-spectral-topology-rs/experiments/spectral_perturbation.py`
- Raw results: `~/repos/conservation-spectral-topology-rs/experiments/spectral_perturbation_results.json`
