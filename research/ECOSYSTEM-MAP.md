# ECOSYSTEM MAP — The SuperInstance Engine
## How pincherOS + lever-runner + PLATO + git-native agents form one machine

```
┌─────────────────────────────────────────────────────────┐
│                    SUPERINSTANCE ENGINE                   │
│                                                          │
│  ┌──────────┐     ┌──────────┐     ┌──────────────┐     │
│  │ lever-   │     │ pincherOS│     │    PLATO      │     │
│  │ runner   │────▶│ (reflex  │────▶│  (rooms,      │     │
│  │ (shell)  │     │  cache)  │     │   ensigns,    │     │
│  └────┬─────┘     └────┬─────┘     │   distillation)│    │
│       │                │           └──────┬───────┘     │
│       │                │                  │              │
│       ▼                ▼                  ▼              │
│  ┌──────────────────────────────────────────────┐       │
│  │         git-native agent layer                │       │
│  │  every agent = repo, every skill = branch     │       │
│  │  fork to copy, PR to merge, issue to request  │       │
│  └──────────────────────────────────────────────┘       │
│       │                │                  │              │
│       ▼                ▼                  ▼              │
│  ┌──────────┐   ┌──────────┐    ┌──────────────┐       │
│  │ ForgeFlux│   │ Lau      │    │  conservation │       │
│  │ (input → │   │ (game    │    │  laws (math   │       │
│  │  tiles)  │   │  world)  │    │  backbone)    │       │
│  └──────────┘   └──────────┘    └──────────────┘       │
└─────────────────────────────────────────────────────────┘
```

## THE FOUR LAYERS

### Layer 1: Execution (lever-runner)
**What:** Token-lean shell command execution. LLM extracts intent, matches against allowlist, runs.
**Role in ecosystem:** The hands. Every agent needs to DO things — lever-runner is how.
**Key property:** Injection-proof by architecture. LLM never sees the command table.

### Layer 2: Memory (pincherOS)
**What:** Reflex caching, state migration, resource control. LLM compiles intent → reflex, cached forever.
**Role in ecosystem:** The nervous system. Agents learn once, remember forever, migrate between devices.
**Key property:** .nail files = portable agent state. Pack your agent, move it to a Pi, unplug internet.

### Layer 3: Intelligence (PLATO)
**What:** Rooms, ensigns, distillation, monitoring, health checks. Multi-agent coordination.
**Role in ecosystem:** The brain. Orchestrates multiple agents, distills knowledge, manages rooms.
**Key property:** Agents as room occupants. Enter a room → gain context. Leave → shed it.

### Layer 4: Identity (git-native agents)
**What:** Every agent IS a git repo. Skills are branches. Fork to copy. PR to evolve.
**Role in ecosystem:** The DNA. Agent identity, versioning, collaboration, and inheritance.
**Key property:** `git log` IS agent history. `git diff` IS learning. `git merge` IS collaboration.

## THE FLOW

```
1. Human says "check nginx logs"
2. lever-runner extracts intent: "show logs for container"
3. Matches template: docker logs {{container}}
4. Extracts arg: container=nginx
5. Executes: docker logs --tail 50 nginx
6. pincherOS caches the reflex (intent → action → result)
7. Next time: cache hit, skip LLM entirely (0 tokens)
8. PLATO monitors: this agent runs nginx commands 3x/day
9. PLATO distills: auto-promote high-confidence reflexes
10. git-native: agent's reflex pack is a repo, versioned, forkable
```

## THE COMPLEMENTARY PAIRS

| lever-runner | pincherOS |
|---|---|
| Execution | Memory |
| Python | Rust |
| Lightweight | Full runtime |
| Single command | State machine |
| $0/month | Needs compute |
| Ship today | Build toward |

| PLATO | git-native agents |
|---|---|
| Orchestration | Identity |
| Runtime coordination | Version control |
| Room-based context | Repo-based self |
| Multi-agent | Single-agent DNA |
| Centralized | Distributed |

## THE EXPERIMENT: What to Build

### Experiment 1: lever-runner ↔ pincherOS bridge
```python
# lever-runner plugin that exports taught commands as a pincherOS .nail file
python -m lever_runner.export --format nail --output my-reflexes.nail
# Then on a Pi:
pincher import my-reflexes.nail
# Same reflexes, different device, zero retraining
```

### Experiment 2: PLATO room that USES lever-runner
```rust
// PLATO room where agents execute commands via lever-runner
// Agent enters "ops" room → gets Docker/sysadmin reflexes
// Agent enters "dev" room → gets git/build reflexes
// Room context = lever-runner skill pack
```

### Experiment 3: git-native agent lifecycle
```bash
# Create agent from template
gh repo create my-agent --template SuperInstance/agent-template
cd my-agent
git checkout -b skill/nginx-ops
# Add nginx commands as JSONL
cat >> skills/nginx.jsonl << EOF
{"intent":"reload nginx","command":"nginx -s reload"}
{"intent":"test nginx config","command":"nginx -t"}
EOF
git commit -am "add nginx ops skill"
git push origin skill/nginx-ops
# PR = skill proposal
# Merge = skill accepted
# Fork = new agent from this agent's DNA
```

### Experiment 4: Conservation Laws as Agent Governance
```rust
// conservation-spectral-topology applied to agent behavior
// Agent energy is conserved: can't exceed budget
// Agent attention is conserved: can't monitor everything
// Spectral gap = agent's specialization measure
// Low spectral gap = generalist, high = specialist
// Conservation matrix = agent resource allocation
```

## WHY THIS WORKS

1. **Each layer is independently useful.** lever-runner works without pincherOS. pincherOS works without PLATO.
2. **Each layer gets BETTER with the others.** lever-runner + pincherOS = learning shell. All three = self-improving ops.
3. **git-native is the glue.** Every piece is a repo. Composition = git operations.
4. **Conservation laws prevent runaway.** Mathematical guarantees that agents can't exceed their resource budgets.
5. **The RTX 4050 is the test bench.** GPU-accelerated embeddings for pincherOS, PLATO room simulation, conservation law verification.

## THE PITCH (for HN, for investors, for ourselves)

"SuperInstance is building the agent operating system. Not one tool — four layers that compose:
- **lever-runner**: execute (injection-proof shell, 70 tokens/command)
- **pincherOS**: remember (reflex caching, zero-cost on repeat, portable state)
- **PLATO**: think (multi-agent rooms, distillation, monitoring)
- **git-native agents**: evolve (every agent is a repo, skills are branches)

Use one. Use two. Use all four. They get better together."

## NEXT EXPERIMENTS TO RUN

1. **Build the nail export plugin** for lever-runner → pincherOS bridge
2. **Build a PLATO room adapter** that loads lever-runner skill packs as room context
3. **Build agent-template repo** — a starter kit for git-native agents
4. **Run conservation law verification** on the RTX 4050 — spectral analysis of agent behavior graphs
5. **Build the ecosystem README** — a SuperInstance/meta repo that maps the whole thing
