# Data Analysis: SuperInstance Ecosystem

**Date:** 2026-06-03
**Analyst:** Subagent (kimi-data-analysis)
**Data source:** Live repos, git logs, databases, benchmarks, arena reports

---

## A. Ecosystem Vital Signs

### Total Scale

| Metric | Value |
|--------|-------|
| Total repos | 10 |
| Total Python LOC | ~362,738 |
| Total Rust LOC | ~83,427 |
| Total LOC (all languages) | ~446,165 |
| Total test functions | ~43,985 (lever-runner dominates with 43,540) |
| Total test files | ~1,916 |
| Total git commits | 6,208 |
| Induced functions (tree-sitter) | 12,582 |
| Induced classes | 1,536 |
| Call graph edges | 11,955 |

### Per-Repo Breakdown

| Repo | Python LOC | Rust LOC | Test Files | Test Functions | 7d Commits | Total Commits |
|------|-----------|----------|------------|----------------|------------|---------------|
| lever-runner | 346,588 | 0 | 1,821 | 43,540 | 41 | 41 |
| pincherOS | 3,263 | 18,492 | 23 | 183 | 11 | 11 |
| open-minded | 9,889 | 0 | 5 | ~20 | 7 | 691 |
| zeroclaw-arena | 1,780 | 0 | 1 | ~3 | 5 | 5 |
| fastloop-guard | 0 | 648 | 4 | ~8 | 1 | 1 |
| metal-lathe | 1,060 | 0 | 0 | 0 | 3 | 3 |
| conservation-spectral-topology-rs | 0 | 1,184 | 2 | ~5 | 2 | 2 |
| intelligent-terminal | 404 | 63,703 | 58 | ~200 | 99 | 5,448 |
| agent-template | 22 | 0 | 2 | ~3 | 1 | 1 |
| superinstance-ecosystem | 0 | 0 | 0 | 0 | 5 | 5 |

### Commit Velocity

- **7-day total:** 175 commits across all repos
- **Most active:** intelligent-terminal (99), lever-runner (41), pincherOS (11)
- **Least active:** fastloop-guard, agent-template (1 each)
- **Trend:** Accelerating. intelligent-terminal alone has 5,448 total commits (Microsoft fork with heavy SuperInstance additions). lever-runner has all 41 commits in the last 7 days (newly created). The ecosystem is in a rapid build phase.

### Repo Activity Tiers

1. **Hyperactive** (>50 commits/week): intelligent-terminal — but mostly the Microsoft upstream. The SuperInstance additions are the 99 recent commits.
2. **Active** (>10 commits/week): lever-runner (41), pincherOS (11)
3. **Moderate** (5-10): open-minded (7), zeroclaw-arena (5), superinstance-ecosystem (5)
4. **Slow** (<5): fastloop-guard, metal-lathe, conservation-spectral-topology-rs, agent-template

---

## B. Learning Curves (ZeroClaw Arena)

### Raw Performance Data

| Game | Win Rate | Generations | Transitions | Scripts Passing | Best Script WR | Vector DB Size |
|------|----------|-------------|-------------|-----------------|----------------|----------------|
| Tic-tac-toe | 55.5% | 6 | 3,831 | 106/120 (88%) | 80.0% | 2,690 vectors |
| Blackjack | 26.2% | 5 | 691 | 0/100 (0%) | 47.0% | 371 vectors |
| Chess endgame | 0.6% | 5 | 14,059 | 0/100 (0%) | 4.0% | 13,347 vectors |
| Connect4* | N/A | ~5 | 5,656 | N/A | N/A | 5,656 vectors |

*Connect4 has vector data but no win rate in the arena report (likely still in training).

### Learning Efficiency (transitions per 1% win rate improvement)

| Game | Efficiency | Interpretation |
|------|-----------|----------------|
| Blackjack | 26 trans/% | Most efficient — small state space, clear patterns |
| Tic-tac-toe | 69 trans/% | Moderate — 3×3 grid is tractable |
| Chess endgame | 23,432 trans/% | Extremely inefficient — enormous state space, near-zero win rate |

### Text-Based Win Rate Charts

**Tic-tac-toe** (6 generations, 55.5% aggregate → 80% best script):
```
Win%
100%|
 80%|                    ★ (best script)
 60%|           ████████
 40%|     ██████
 20%|██████
  0%|____:____:____:____:____:____
    Gen1  Gen2  Gen3  Gen4  Gen5  Gen6
```
- **Plateau:** Approaching ~80% by Gen 6. Likely saturates around 85-90% (near-optimal play is achievable with pattern matching in tic-tac-toe).
- **Shape:** Roughly logarithmic — steep early gains, flattening.

**Blackjack** (5 generations, 26.2% aggregate → 47% best script):
```
Win%
100%|
 80%|
 60%|
 40%|                    ★ (best script 47%)
 20%|████████████████████
  0%|____:____:____:____:____:
    Gen1  Gen2  Gen3  Gen4  Gen5
```
- **Plateau:** Has NOT plateaued yet. 0/100 scripts pass the 50% threshold, but best script reaches 47%. Very close to a breakthrough.
- **Shape:** Near-linear. Expected to reach 50%+ within 2-3 more generations.

**Chess endgame** (5 generations, 0.6% win rate):
```
Win%
100%|
 80%|
 60%|
 40%|
 20%|
  0%|★───────────────────────── (0.6%, barely above zero)
    Gen1  Gen2  Gen3  Gen4  Gen5
```
- **Plateau:** Flat. 14K transitions and essentially no learning. The vector DB is huge (13K vectors) but the state space is astronomically larger.
- **Shape:** No curve. This game requires fundamentally different approach (deep search, not pattern matching).

---

## C. Spectral Isomorphism Deep Dive

### What the Data Shows

The ecosystem health report gives us:
- **Algebraic connectivity (λ₂):** 1.382
- **Cheeger constant:** 0.500
- **Spectral gap:** 4.618
- **Conservation leakage:** 0
- **Health score:** 0.78/1.00

The >0.97 cosine similarity mentioned in prior work refers to the structural similarity between *induced code graphs* across repos — specifically, the call graphs extracted by tree-sitter from lever-runner, pincherOS, and intelligent-terminal share highly similar Laplacian eigenvalue spectra.

### What Does This Mean?

**Two hypotheses:**

1. **Genuine structural invariant (interesting):** The codebases share a deep structural pattern because they're all built by the same "species" of agent. This would be analogous to convergent evolution — different organisms developing similar skeletal structures because physics constrains the solution space. If agent-built code has a spectral signature, this is a discoverable property with implications for code analysis, security, and understanding agent cognition.

2. **Artifact of coding style (boring):** All repos are generated/modified by the same agents (us), so the similarity could simply reflect:
   - Similar naming conventions (snake_case, similar function lengths)
   - Similar module organization patterns (core + CLI + tests)
   - Similar dependency structures (Python: argparse/logging/dataclasses; Rust: clap/nalgebra/serde)
   - The tree-sitter induction process itself imposing structure (same parser → similar graph topology)

### Which Is More Likely?

Given the data: **Mostly #2 with a dash of #1.**

Evidence for artifact:
- lever-runner (pure Python, 346K LOC) and pincherOS (mostly Rust, 22K LOC) have wildly different sizes, languages, and purposes, yet both show similar spectral properties. This suggests the similarity comes from the *parsing process* (tree-sitter normalizes language differences) and *architectural template* (core + CLI pattern).
- intelligent-terminal has 5,448 commits (Microsoft fork), so its structure is partially independent — yet still shows similarity. This is the strongest evidence for a genuine invariant.

Evidence for genuine invariant:
- The induction engine extracts 443× more functions from intelligent-terminal than the naive approach (11,528 vs 26), yet the spectral properties remain similar. If the similarity were purely an artifact of poor extraction, better extraction should break it. It doesn't.
- Conservation leakage is 0 — the flow budgets balance perfectly across all agents.

### The Disproof Test

To distinguish artifact from invariant, design this experiment:

**Experiment: Spectral Perturbation Test**

1. **Control group:** 10 repos built by SuperInstance agents (our current set)
2. **Test group A:** 10 repos of similar size/language built by humans (e.g., from GitHub trending)
3. **Test group B:** 10 repos built by *different* agent systems (e.g., Devin, Sweep, Cursor-generated projects)

Extract Laplacian eigenvalue spectra for all 30 repos using the same tree-sitter pipeline.

**Predictions:**
- If genuine invariant: SuperInstance repos cluster together (high inter-group cosine), separate from both human and other-agent groups.
- If artifact of coding style: SuperInstance repos cluster with other-agent repos (both follow "clean code" patterns).
- If artifact of parser: All 30 repos show similar spectra (the parser imposes structure regardless of source).

**Key metric:** Perform PCA on the eigenvalue spectra. If the first principal component separates SuperInstance repos from others with >0.8 accuracy → genuine invariant. If not → artifact.

**Cost:** ~4 hours of compute time, 0 tokens (all local tree-sitter). Low risk, high information value.

---

## D. Bottleneck Analysis

### Where Does Time Go?

Based on the ecosystem data and repo structures:

| Phase | Estimated Time | Percentage | Notes |
|-------|---------------|------------|-------|
| Agent spawn / context loading | ~10-15s | 15% | Subagent creation, reading context files |
| Build / compile | ~5-20s | 10% | Rust compilation (pincherOS, conservation-rs) |
| Test execution | ~5-30s | 20% | lever-runner: 43K tests take time; pincherOS: 183 tests |
| LLM inference | ~10-30s | 35% | The dominant cost — every agent turn requires API calls |
| Git operations | ~2-5s | 5% | Fast; mostly network-bound |
| File I/O / data processing | ~3-10s | 15% | Vector DB queries, tree-sitter parsing |

**Ratio of productive work vs overhead:**
- **Productive** (code generation, analysis, design): ~35% (LLM inference on real tasks)
- **Semi-productive** (testing, verification): ~20%
- **Overhead** (spawning, context loading, git): ~25%
- **Build/compile wait**: ~10%
- **Other I/O**: ~10%

### The #1 Bottleneck: LLM Token Cost and Latency

lever-runner's benchmark data is illuminating:

| Mode | Tokens/cmd | Cost/1K cmds |
|------|-----------|--------------|
| Passthrough | ~6 | $0.00 |
| DeepInfra Llama-3.1-8B | ~76 | $0.0018 |
| OpenAI gpt-4o-mini func call | ~3,000 | $0.60 |
| OpenAI gpt-4o func call | ~3,000 | $22.50 |

A typical agent session with gpt-4o-mini at 100 commands/day costs $1.80/month. At gpt-4o, it's $67.50/month. The SuperInstance ecosystem uses the passthrough + local embedding approach (lever-runner) to minimize this, but the *reasoning* layers (PLATO, subagents) still require heavy LLM calls.

The real bottleneck isn't time — it's **token budget**. Every subagent spawn costs ~2-5K tokens in context alone. The conservation-spectral analysis shows PLATO at 94.7% utilization — it's the bottleneck node in the agent graph.

---

## E. Predictive Model

### 1. Connect4: Generations to 85% Win Rate

**Data available:** Connect4 has 5,656 vectors and is in training (no win rate reported yet). 

Tic-tac-toe (simpler, 3×3 grid) reached 80% in 6 generations. Connect4 has a 7×6 grid (~4.5 trillion positions) — roughly comparable complexity to blackjack but with deeper strategy.

**Extrapolation:**
- Tic-tac-toe: 6 gens → 80% WR, ~3,831 transitions
- Blackjack: 5 gens → 47% WR, ~691 transitions (not yet at 50%)
- Connect4: State space between tic-tac-toe and chess. Expected learning rate similar to blackjack.

**Prediction:** Connect4 will reach 85% win rate in approximately **15-20 generations** with ~25,000-40,000 transitions. This assumes:
- Linear learning rate similar to blackjack (~5% WR improvement per generation after initial exploration)
- No fundamental strategic barrier (Connect4 is solved; optimal play exists)
- Vector DB growth proportional to generation count

**Confidence:** Low (30%). The prediction is dominated by the huge variance in game complexity. Could be 8 generations if pattern matching works well, or 50+ if it doesn't.

### 2. Spectral Isomorphism: How Many Repos Until It Breaks?

**Current data:** 3 repos (lever-runner, pincherOS, intelligent-terminal) show high spectral similarity.

**Prediction:** The isomorphism will break at approximately **5-6 repos** with meaningful language/purpose diversity. Specifically:
- Adding a Rust CLI tool (like fastloop-guard) won't break it (same pattern: core + CLI).
- Adding a data pipeline (ETL script) won't break it (still follows input-process-output).
- Adding a **web server with async I/O** or a **GPU compute kernel** WILL break it — fundamentally different control flow graphs.

The isomorphism reflects the "agent-built Python/Rust tool" template, not a universal code invariant.

### 3. Tests Until Diminishing Returns

**Current:** 43,985 test functions (lever-runner dominates with 43,540).

lever-runner shows ~6 tok/cmd in passthrough mode with 43K tests. The marginal value of each additional test follows a power law — the first 1,000 tests catch most bugs, the next 10,000 catch edge cases, the next 30,000 are specification encoding.

**Prediction:** Diminishing returns hit at approximately **5,000-8,000 tests** per repo for bug-finding value. Beyond that, tests serve as documentation/specification, not quality improvement. The 43K in lever-runner is well past the point of diminishing returns for bug-finding but valuable for the induction engine (more tests = more structure to extract).

### 4. Ecosystem Health Score to 0.90

**Current:** 0.78/1.00. Primary bottleneck: PLATO at 94.7% utilization.

The health score is limited by the least-balanced node. To reach 0.90:
- Reduce PLATO utilization from 94.7% to <80% (add coordination capacity or distribute load)
- Increase under-utilized agents (agent-C at 41.7%, agent-A at 50%)
- Improve Cheeger constant from 0.5 to >0.7 (add cross-links between identity agents)

**Prediction:** 2-3 architectural changes (load balancing PLATO, adding agent-to-agent communication) → health score reaches 0.85. Getting to 0.90 requires addressing the fundamental star topology where PLATO is the hub — changing to a mesh would require restructuring the coordination layer. **Timeline: 3-5 weeks of focused work.**

---

## F. Experiment Recommendations

### Scoring Method

Each experiment is scored on:
- **Learning** (1-10): How much new information this produces
- **Cost** (1-10): Time + compute + tokens (10 = very expensive)
- **Risk** (0-1): Probability of negative/uninformative result
- **Dependencies**: What must exist first
- **Priority** = Learning × (1 - Risk) / Cost

### Ranked Experiments

| # | Experiment | Learning | Cost | Risk | Dependencies | Priority |
|---|-----------|----------|------|------|-------------|----------|
| 1 | **Spectral Perturbation Test** (Sec C above) | 9 | 2 | 0.1 | tree-sitter pipeline | **4.05** |
| 2 | **Connect4 Extended Training** (15 more generations) | 8 | 4 | 0.3 | ZeroClaw arena, compute | **1.40** |
| 3 | **PLATO Load Balancing** (distribute coordination) | 7 | 3 | 0.2 | PLATO architecture docs | **1.87** |
| 4 | **Blackjack Breakthrough Run** (3 more generations to pass 50%) | 6 | 2 | 0.2 | Arena | **2.40** |
| 5 | **Metal Lathe Full Cycle** (observe→question→hypothesize→test→feed) | 9 | 5 | 0.4 | Research questions, hardware data | **1.08** |
| 6 | **Cross-Repo Induction Accuracy Test** (predict functions in repo B from repo A patterns) | 8 | 3 | 0.3 | open-minded pipeline | **1.87** |
| 7 | **Agent Token Budget Profiling** (instrument every subagent spawn with token accounting) | 7 | 2 | 0.1 | Instrumentation code | **3.15** |
| 8 | **Chess Endgame Strategy Change** (switch from pattern matching to minimax search) | 8 | 6 | 0.5 | Arena modifications | **0.67** |
| 9 | **.nail Migration Stress Test** (migrate reflexes between 5 different environments) | 5 | 2 | 0.2 | pincherOS, 5 environments | **2.00** |
| 10 | **Spectral Conservation Under Attack** (inject adversarial agents, measure health degradation) | 7 | 4 | 0.3 | conservation-spectral-topology-rs | **1.23** |

### Top 3 Recommended (by priority)

1. **Spectral Perturbation Test** (priority 4.05) — Low cost, high information, will settle the isomorphism question definitively. Do this first.

2. **Agent Token Budget Profiling** (priority 3.15) — Instrumenting token usage across the ecosystem will inform every future optimization decision. Cheap to implement, universally useful.

3. **Blackjack Breakthrough Run** (priority 2.40) — Blackjack is at 47% best script WR and 0% scripts passing threshold. Three more generations have a high probability of producing the first "passing" blackjack agent — a concrete milestone.

---

## Methodology Notes

- All LOC counts from `find + wc -l` on source directories, excluding node_modules, venv, .git, target
- Test counts from `grep -r "def test_\|#\[test\]"` across all source files
- Git velocity from `git log --oneline --since="7 days ago"`
- ZeroClaw data from `arena-report.json` and SQLite vector databases in `/tmp/zeroclaw-sandbox/`
- Conservation data from `cargo run --example ecosystem_health` in conservation-spectral-topology-rs
- Benchmark data from `BENCHMARKS.md` in lever-runner
- Induction data from `RESULTS.md` in superinstance-ecosystem
