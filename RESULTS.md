# Results

Real numbers from the SuperInstance ecosystem — measured, not estimated.

## lever-runner

| Metric | Value |
|--------|-------|
| Tests passing | 142 |
| Functions induced | 221 |
| Call graph edges | 918 |
| Token budget per command | ~70 |

## pincherOS

| Metric | Value |
|--------|-------|
| Tests passing | 130 |
| Warnings | 0 |
| Functions induced | 833 |
| Classes induced | 297 |
| Call graph edges | 799 |
| Parsing | tree-sitter (Rust + Python) |

## open-mind

| Metric | Value |
|--------|-------|
| Tests passing | 55+ |
| Components | Induction engine, tripartite synchronizer, integration suite |
| Repos analyzed | 3 (lever-runner, pincherOS, intelligent-terminal) |

## Conservation Law Verification

| Metric | Value |
|--------|-------|
| Ecosystem health score | 0.78 / 1.00 |
| Conservation leakage | 0 (verified) |
| Algebraic connectivity | 1.382 |
| PLATO utilization | 94.7% (bottleneck identified) |
| Implementation | Rust (`conservation-spectral-topology-rs`) |

## intelligent-terminal

| Metric | Value |
|--------|-------|
| Subsystems mapped | 6 |
| Functions induced | 11,528 |
| Classes induced | 1,186 |
| Call graph edges | 10,224 |
| Parsing | tree-sitter (C++, C, Rust, Python, JavaScript) |
| Classification | Tripartite (structure / dynamics / semantics) |

## Induction Table (tree-sitter)

| Repo | Functions | Classes | Vectors | Call Graph |
|------|-----------|---------|---------|------------|
| lever-runner | 221 | 53 | 221 | 932 |
| pincherOS | 833 | 297 | 833 | 799 |
| intelligent-terminal | 11,528 | 1,186 | 11,528 | 10,224 |

> With tree-sitter multi-language parsing, extraction improved from 113→833 (pincherOS, **7.4×**) and 26→11,528 (intelligent-terminal, **443×**).

## Totals

| Metric | Value |
|--------|-------|
| Agents run | 22 |
| Tests across repos | 327+ |
| Repos in ecosystem | 8 |
| Conservation violations | 0 |
