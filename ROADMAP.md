# Roadmap

## Now (ships today)

- ✅ **lever-runner**: parameterized commands, skill packs, Docker, web dashboard, 142 tests
- ✅ **pincherOS**: reflex matching, `.nail` migration, 130 tests passing, 0 warnings
- ✅ **lever-runner ↔ pincherOS bridge** (`.nail` export)
- ✅ **agent-template** repo for git-native agents
- ✅ **open-mind** induction engine (55+ tests, tripartite synchronizer, integration tests)
- ✅ **tripartite synchronizer** decision matrix (structure / dynamics / semantics)
- ✅ **conservation law verification** (Rust — `conservation-spectral-topology-rs`)
- ✅ **intelligent-terminal** tripartite analysis (6 subsystems, 26 functions classified)
- ✅ **hardware auto-detection** in lever-runner
- ✅ **captains-log** for cross-repo coordination

## Next (4-6 weeks)

- **PLATO** room adapter for lever-runner skill packs
- **pincherOS**: deterministic embeddings, sandbox wiring, production hardening
- Multi-agent coordination via PLATO rooms
- Scale PLATO past 94.7% utilization bottleneck

## Soon (2-3 months)

- GPU-accelerated embedding pipeline
- WASM carapace for browser-based agents
- Edge deployment on Raspberry Pi

## Future

- Agent marketplace (fork, customize, deploy)
- Cross-repo evolution via open-mind deduction loop
- Real-time tripartite monitoring dashboard

## Ecosystem Map

```
                        ┌──────────┐
                        │  PLATO   │
                        │ Rooms ·  │
                        │ Ensigns  │
                        └────┬─────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
   ┌──────┴──────┐   ┌──────┴──────┐   ┌──────┴──────┐
   │ lever-runner │   │  pincherOS  │   │  open-mind   │
   │  Execution   │◄──►│   Memory    │   │  Induction   │
   └──────┬──────┘   └─────────────┘   └──────┬──────┘
          │                                    │
   ┌──────┴──────┐                     ┌──────┴──────┐
   │intelligent- │                     │conservation- │
   │  terminal   │                     │spectral-topo │
   └─────────────┘                     └─────────────┘
          │
   ┌──────┴──────┐
   │agent-template│  captains-log (coordination)
   │  Identity    │
   └─────────────┘
```
