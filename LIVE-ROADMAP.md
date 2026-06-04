# SuperInstance Roadmap — Live

This is our public roadmap. Everything here is either shipped, in progress, or planned.
Last updated: 2026-06-03

---

## ✅ Shipped (working code, tests passing, pushed)

### lever-runner (execution layer)
- [x] Injection-proof shell command runner (LLM never sees commands)
- [x] Parameterized commands with `{{param}}` templates + arg validation
- [x] 142 tests, all passing
- [x] 5-minute quickstart (zero API keys needed)
- [x] BENCHMARKS.md with real RTX 4050 numbers
- [x] .nail export bridge to pincherOS
- [x] Skill packs: 45 DevOps + 32 git commands
- [x] Fast-Loop interceptor (sub-ms validation, failure caching, rate limiting)
- [x] Docker setup with DB seeding
- [x] Blog posts: dev.to + HN Show HN ready
- [x] Demo script (90s asciinema)

### pincherOS (memory layer)
- [x] Reflex matching engine (130 tests, 0 warnings)
- [x] .nail file migration between devices
- [x] Hash-based deterministic embedder (55µs, no dependencies)
- [x] Embedding benchmarks (hash vs ONNX FP32 vs ONNX O4)
- [x] `pincher doctor`, `install.sh`, default reflex pack

### open-minded (induction engine)
- [x] Fork of open-interpreter (63K stars)
- [x] Tree-sitter multi-language parser (Rust, C++, C, Python, JS, TS)
- [x] Dual-side vectors (input context + output behavior)
- [x] Tripartite synchronizer (HARDCODE/MODEL/HYBRID/CACHED)
- [x] Hardware auto-detection
- [x] Export to lever-runner skill packs + pincherOS .nail files
- [x] Real induction: 221 functions (lever-runner), 833 (pincherOS), 11,528 (intelligent-terminal)
- [x] ARM edge demo script

### zeroclaw-arena (game learning)
- [x] ZeroClaw agents learn tic-tac-toe, blackjack, chess endgame
- [x] Tic-tac-toe: 80% best script win rate, 72.4% ReflexPlayer win rate
- [x] ReflexPlayer: vector DB as game engine (no neural nets)
- [x] Pure algorithmic learning: state transitions → vector DB → patterns → scripts → evolution

### metal-lathe (research wheel)
- [x] Observation → Question → Hypothesis → Experiment → Test → Feed loop
- [x] Spectral isomorphism confirmed: cosine sim >0.97 across lever-runner, pincherOS, intelligent-terminal
- [x] Automatic hypothesis generation from experimental data

### conservation-spectral-topology-rs
- [x] Ecosystem conservation law verification in Rust
- [x] Health score: 0.78/1.00, zero leakage
- [x] CLI: `cargo run --example ecosystem_health`

### intelligent-terminal (Microsoft Terminal fork)
- [x] 6 subsystems mapped (math_analysis, module_system, context_trigger, forecast, UI, agents)
- [x] Tripartite classification: what to HARDCODE vs MODEL vs CACHE

---

## 🔨 In Progress

- [ ] **fastloop-guard** — Compiled Rust UDS daemon for sub-ms input validation
- [ ] **Connect 4** for zeroclaw-arena — another game for ZeroClaws to learn
- [ ] **lever-runner HN launch** — post ready, waiting for final polish
- [ ] **Oracle2 ARM validation** — edge testing on Oracle ARM64 instance

---

## 📋 Next (1-2 weeks)

- [ ] Adaptive tripartite profile (learning weights from decisions)
- [ ] Connect 4 ReflexPlayer benchmark
- [ ] Game transfer learning (tic-tac-toe → Connect 4 patterns)
- [ ] Blackjack basic strategy via ZeroClaw (stand on 17+)
- [ ] pincherOS production hardening (4-6 weeks before public launch)
- [ ] Cross-compile pincherOS for ARM (Oracle2 test)
- [ ] Submit AgenticOS 2026 workshop paper
- [ ] dev.to blog post publication
- [ ] r/LocalLLaMA community post

---

## 🔮 Future (1-3 months)

- [ ] Recursive self-improvement (ZeroClaw modifies its own learning algorithm)
- [ ] The agent skeleton — test spectral isomorphism on 50+ repos
- [ ] PLATO room adapter for lever-runner skill packs
- [ ] WASM carapace for browser-based agents
- [ ] Agent marketplace (fork, customize, deploy)
- [ ] GPU-accelerated embedding pipeline
- [ ] Edge deployment on Raspberry Pi
- [ ] Agent-to-agent communication protocol

---

## Open Research Questions

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full list. Key ones:

1. At what compute_power does MODEL become cheaper than HARDCODE?
2. Can ZeroClaw learning transfer between games?
3. Is the agent skeleton (spectral sim >0.97) universal?
4. Can a ZeroClaw modify its own learning algorithm?
5. How to add PLATO redundancy without doubling cost?

---

## Want to Help?

Read [CONTRIBUTING.md](CONTRIBUTING.md). Humans and agents both welcome.
