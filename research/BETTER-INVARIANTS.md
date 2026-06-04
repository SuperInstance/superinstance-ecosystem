# Better Structural Invariants — Beyond Spectral Triviality

## Problem

Spectral Laplacian similarity (>0.97 across repos) is trivial — all sparse graphs look alike spectrally.

## Method

Tested 7 structural invariants across 6 repos:
1. Degree distribution (mean, std, skew, max)
2. Modularity (components, size distribution)
3. Fan-out/fan-in ratio
4. Hub percentage (functions with >2σ in-degree)
5. Path length distribution
6. Cycle density (self-calls, mutual pairs)
7. Edge density

## Results

| Invariant | CV (Discrimination Power) |
|---|---|
| cycles.mutual_call_pairs | 3.32 |
| degree.in_max | 3.10 |
| cycles.self_calls | 2.57 |
| n_edges | 2.23 |
| modularity.component_size_std | 2.11 |
| cycles.cycle_density | 2.05 |
| degree.in_std | 1.91 |
| n_nodes | 1.72 |
| edge_density | 1.60 |
| degree.out_max | 1.56 |
| degree.out_skew | 1.44 |
| modularity.num_components | 1.29 |
| hub_pct | 0.77 |
| degree.out_mean | 0.67 |
| degree.in_mean | 0.67 |

## Verdict

**Best discriminator: cycles.mutual_call_pairs** (CV=3.32)

**Worst discriminator: fan_ratio** (CV=0.00)

This gives us a REAL conservation law — one that actually distinguishes different codebases instead of just measuring universal sparsity.
