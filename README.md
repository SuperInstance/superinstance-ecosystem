# SuperInstance Ecosystem

> Teach once, run forever. The LLM never sees your shell.

## Architecture

```
                              SuperInstance Stack
 ┌──────────────────────────────────────────────────────────────────┐
 │  User / Agent                                                    │
 │      │                                                           │
 │      ▼                                                           │
 │  ┌──────────────┐    ┌─────────────────┐    ┌────────────────┐  │
 │  │ lever-runner  │───▶│  Rust Carapace   │───▶│ tile-cuda      │  │
 │  │ (Python)      │    │  128ns hash      │    │  (CUDA + PTX)  │  │
 │  │ 202 tests     │    │  1.73µs embed    │    ├────────────────┤  │
 │  │               │    │                  │    │ tile-opencl    │  │
 │  └──────┬───────┘    └────────┬─────────┘    │  (OpenCL)      │  │
 │         │                     │               ├────────────────┤  │
 │         │                     │               │ tile-neon      │  │
 │         │                     │               │  (ARM NEON)    │  │
 │         │                     │               └────────────────┘  │
 │         │                     │                                   │
 │         │         ┌───────────┴────────────┐                     │
 │         │         │                        │                     │
 │         ▼         ▼                        ▼                     │
 │  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐      │
 │  │ lever-runner │  │ compiled-    │  │ fastloop-guard     │      │
 │  │ -wasm        │  │ policy-c     │  │ (Rust UDS cache    │      │
 │  │ (71KB gzip)  │  │ (µC / bare)  │  │  daemon)           │      │
 │  └──────────────┘  └──────────────┘  └───────────────────┘      │
 │                                                                  │
 │  ┌─────────────────────────────────────────────────────────────┐ │
 │  │ pincherOS — reflex caching, .nail state, 130+ tests        │ │
 │  ├─────────────────────────────────────────────────────────────┤ │
 │  │ tile-compiler — policy → GPU kernel pipeline, 109 tests    │ │
 │  ├─────────────────────────────────────────────────────────────┤ │
 │  │ open-minded — induction engine, tripartite synchronizer    │ │
 │  ├─────────────────────────────────────────────────────────────┤ │
 │  │ conservation-spectral-topology-rs — conservation laws (Rust)│ │
 │  ├─────────────────────────────────────────────────────────────┤ │
 │  │ captains-log — i2i coordination, session tracking          │ │
 │  └─────────────────────────────────────────────────────────────┘ │
 └──────────────────────────────────────────────────────────────────┘

 Hardware: Forgemaster (RTX 4050) + Loom (ARM64)
```

## Repos

| Repo | What it does | Lang | Tests |
|------|-------------|------|-------|
| [lever-runner](https://github.com/SuperInstance/lever-runner) | Injection-proof command runner, 70 tokens/cmd, skill packs | Python | 202 |
| [pincherOS](https://github.com/SuperInstance/pincherOS) | Reflex caching, `.nail` state files, portable agent memory | Python | 130+ |
| [tile-compiler](https://github.com/SuperInstance/tile-compiler) | Policy → GPU kernel compilation pipeline | Python | 109 |
| [zeroclaw-arena](https://github.com/SuperInstance/zeroclaw-arena) | Multi-agent arena for zero-trust competition | — | — |
| [lever-runner-carapace](https://github.com/SuperInstance/lever-runner-carapace) | Rust core: 128ns hash, 1.73µs embedding | Rust | — |
| [lever-runner-wasm](https://github.com/SuperInstance/lever-runner-wasm) | Browser runtime, 71KB gzip | WASM | — |
| [tile-cuda](https://github.com/SuperInstance/tile-cuda) | CUDA + PTX kernel backend | CUDA/PTX | — |
| [tile-opencl](https://github.com/SuperInstance/tile-opencl) | OpenCL kernel backend (portable GPU) | OpenCL | — |
| [tile-neon](https://github.com/SuperInstance/tile-neon) | ARM NEON SIMD backend (mobile/edge) | C/ASM | — |
| [compiled-policy-c](https://github.com/SuperInstance/compiled-policy-c) | Compiled policy for microcontrollers & bare metal | C | — |
| [ptx-bench](https://github.com/SuperInstance/ptx-bench) | PTX microbenchmarks, register pressure analysis | PTX | — |
| [fastloop-guard](https://github.com/SuperInstance/fastloop-guard) | UDS cache daemon, hot-path acceleration | Rust | — |
| [conservation-spectral-topology-rs](https://github.com/SuperInstance/conservation-spectral-topology-rs) | Conservation law verification, spectral topology | Rust | — |
| [open-minded](https://github.com/SuperInstance/open-minded) | Induction engine, tripartite synchronizer, code→knowledge | — | 55+ |
| [intelligent-terminal](https://github.com/SuperInstance/intelligent-terminal) | Tripartite-classified terminal subsystem (MS fork) | C++/C/Rust/JS | — |
| [captains-log](https://github.com/SuperInstance/captains-log) | Cross-repo coordination, i2i session tracking | — | — |
| [superinstance-ecosystem](https://github.com/SuperInstance/superinstance-ecosystem) | This repo — architecture, roadmap, integration | — | — |

## Real Numbers

Measured on real hardware. Not benchmarks. Not estimates.

| Metric | Value | Where |
|--------|-------|-------|
| Hash throughput | 3.2M/sec (0.3µs) | lever-runner-carapace |
| Embedding latency | 1.73µs | Rust Carapace |
| Vector search | 14.6µs / 1K vectors | lever-runner |
| GPU crossover | 10K vectors (GPU wins) | tile-cuda |
| WASM binary | 71KB gzip | lever-runner-wasm |
| Token budget | ~70 / command | lever-runner |
| Ecosystem tests | 327+ | across repos |
| Conservation violations | 0 | conservation-spectral-topology-rs |

## The Paradigm

```
  Traditional:  User → LLM → shell → chaos
  SuperInstance: User → lever-runner → verified command → result
                         ↑
                    LLM designs the command
                    but never touches the shell
```

The LLM proposes. lever-runner disposes. Every command is parameterized, bounded, auditable. You teach a skill once; it runs forever. No prompt injection, no escaping, no surprise `rm -rf`.

The GPU stack takes this further: policy compiled to CUDA/OpenCL/NEON kernels, a Rust carapace hitting 128ns hashes, and a UDS cache daemon for the hot path. The same agent code runs on an RTX 4050, in a browser via WASM, or on a microcontroller via compiled C.

## Hardware

- **Forgemaster** — x86 workstation, RTX 4050, CUDA host
- **Loom** — ARM64, NEON target, edge inference

---

[All repos](https://github.com/SuperInstance?tab=repositories) · [Architecture](ARCHITECTURE-V2.md) · [Roadmap](LIVE-ROADMAP.md) · [Contributing](CONTRIBUTING.md)
