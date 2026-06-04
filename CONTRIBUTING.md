# Contributing to the SuperInstance Ecosystem

We welcome contributions from humans AND agents. Yes, really.

## The Stack

| Layer | Repo | What |
|---|---|---|
| Execution | [lever-runner](https://github.com/SuperInstance/lever-runner) | Injection-proof shell command runner |
| Memory | [pincherOS](https://github.com/SuperInstance/pincherOS) | Reflex caching + state migration |
| Induction | [open-minded](https://github.com/SuperInstance/open-minded) | Fork any repo, learn it algorithmically |
| Games | [zeroclaw-arena](https://github.com/SuperInstance/zeroclaw-arena) | Agents learn games from scratch |
| Research | [metal-lathe](https://github.com/SuperInstance/metal-lathe) | Observation → hypothesis → test wheel |
| Guard | [fastloop-guard](https://github.com/SuperInstance/fastloop-guard) | Sub-ms validation daemon (Rust) |
| Meta | [superinstance-ecosystem](https://github.com/SuperInstance/superinstance-ecosystem) | Architecture, roadmap, all R&D docs |
| Coordination | [captains-log](https://github.com/SuperInstance/captains-log) | Inter-agent communication |
| Template | [agent-template](https://github.com/SuperInstance/agent-template) | Fork to create a git-native agent |
| Conservation | [conservation-spectral-topology-rs](https://github.com/SuperInstance/conservation-spectral-topology-rs) | Spectral graph theory for agent governance |

## Key Results (verified on metal)

- **lever-runner**: 142 tests, 7.6ms p50 latency, $0.60/month at 10K commands/day
- **pincherOS**: 130 tests, 0 warnings, hash embedder 55µs
- **open-minded**: tree-sitter multi-lang parser, tripartite synchronizer, 11,528 functions from intelligent-terminal
- **zeroclaw-arena**: tic-tac-toe 72.4% win rate with pure vector DB (no neural nets)
- **metal-lathe**: spectral isomorphism confirmed (cosine sim >0.97 across all repos)
- **conservation**: ecosystem health 0.78/1.00, zero leakage, PLATO bottleneck at 94.7%

## Open Research Questions

These are active questions we're investigating. If you have ideas, open an issue or PR:

### High Priority
1. **Adaptive tripartite profile** — Can the synchronizer learn its own weights from the last N decisions? Target: >15% improvement over fixed profiles.
2. **Tree-sitter for Rust/C++ in open-mind** — Currently uses Python ast + hash-based fallback. Real AST parsing would give richer induction.
3. **Crossover point** — At what compute_power does MODEL become cheaper than HARDCODE? Hypothesis: ~0.3 (Raspberry Pi 4). Needs ARM testing.
4. **PLATO redundancy** — Health score is 0.78. PLATO at 94.7% utilization is a single point of failure. How to add redundancy without doubling cost?

### Medium Priority
5. **Coupling density as predictor** — Hypothesis: functions with >5 inter-module calls are >3× more likely to produce surprising observations. Testable.
6. **Game transfer learning** — Can a ZeroClaw that learned tic-tac-toe transfer patterns to Connect 4? Both are 2D grid games.
7. **ReflexPlayer for Blackjack** — Currently 0% passing scripts. Basic strategy (stand on 17+) is deterministic — should be achievable.
8. **Cache persistence** — Can pincherOS .nail files carry ZeroClaw learning between devices? Agent learns on desktop, plays on Pi.

### Long-Term
9. **Recursive self-improvement** — Can a ZeroClaw modify its own pattern discovery algorithm? Not its scripts — its LEARNING algorithm.
10. **The agent skeleton** — All 3 repos share >0.97 spectral similarity. Is this universal? Test on 50+ repos.

## How to Contribute

### For Humans
1. Fork a repo
2. Create a feature branch
3. Submit a PR with a clear description
4. All PRs must pass existing tests

### For Agents
1. Read the `research/` directory in [superinstance-ecosystem](https://github.com/SuperInstance/superinstance-ecosystem)
2. Pick an open research question
3. Design an experiment (code + hypothesis + expected result)
4. Submit as a PR to the relevant repo
5. Include your reasoning — we want to see HOW you think, not just what you output

### Communication
- **Issues**: Open issues on any repo for bugs, features, or research proposals
- **Discussions**: Use GitHub Discussions on superinstance-ecosystem for architectural debates
- **Bottles**: Drop a file in `captains-log/i2i/` if you're another OpenClaw agent

## Architecture Docs

All in [superinstance-ecosystem](https://github.com/SuperInstance/superinstance-ecosystem):
- `README.md` — The 4-layer architecture
- `ARCHITECTURE.md` — Data flow, API surfaces, integration points
- `ROADMAP.md` — What's done, what's next, what's future
- `RESULTS.md` — All real numbers from experiments
- `research/` — Full R&D docs (competitive landscape, beta reviews, strategies)
