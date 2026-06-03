# SuperInstance Ecosystem

SuperInstance is building the agent operating system. Not one tool — four layers that compose.

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   PLATO                          │
│           Intelligence & Coordination            │
│         rooms · ensigns · distillation           │
├─────────────────────────────────────────────────┤
│              git-native agents                    │
│             Identity & Evolution                  │
│       fork → branch → PR → merge = life          │
├─────────────────────────────────────────────────┤
│                 pincherOS                         │
│              Memory & Caching                     │
│        reflex matching · .nail state files        │
├─────────────────────────────────────────────────┤
│               lever-runner                        │
│            Execution & Safety                     │
│     injection-proof shell · 70 tokens/cmd         │
└─────────────────────────────────────────────────┘
```

## The Four Layers

### lever-runner — Execution
An injection-proof command runner that constrains LLM output to parameterized commands. Each command is ~70 tokens — small enough to audit, safe enough to trust. Ships with skill packs (pre-built command sets), Docker support, and a web dashboard. This is the hands.

→ [lever-runner](https://github.com/SuperInstance/lever-runner)

### pincherOS — Memory
Reflex caching for agents. Matches incoming intents against a cache of previous interactions, returning instant results when the pattern fits. State lives in portable `.nail` files. 130+ tests passing. This is the spinal cord — fast, automatic, no thinking required.

→ [pincherOS](https://github.com/SuperInstance/pincherOS)

### PLATO — Intelligence
Multi-agent coordination through rooms, ensigns (lightweight watchers), and distillation (compressing interaction history into reusable knowledge). PLATO orchestrates the higher-order behavior — which agent handles what, when to escalate, how to learn. This is the cortex.

→ [PLATO](https://github.com/SuperInstance/PLATO)

### git-native agents — Identity
Every agent IS a git repository. Fork a template, customize behavior on branches, evolve through pull requests. Merge = learning. Revert = forgetting. This is identity as infrastructure — auditable, forkable, composable.

→ [agent-template](https://github.com/SuperInstance/agent-template)

## Complementary Pairs

| Layer | Role | Complements |
|-------|------|-------------|
| lever-runner | Do things safely | pincherOS remembers what was done |
| pincherOS | Cache reflexes | lever-runner executes cached plans |
| PLATO | Think about thinking | git-native agents persist the thinking |
| git-native agents | Identity & history | PLATO coordinates between identities |

## Getting Started

### Step 1: Try lever-runner (3 commands, zero config)

```bash
git clone https://github.com/SuperInstance/lever-runner.git
cd lever-runner
./run --skill-pack core  # starts the command runner
```

No API keys needed for local testing. The runner accepts natural language, constrains it to safe commands, executes them.

### Step 2: Add pincherOS for memory

```bash
git clone https://github.com/SuperInstance/pincherOS.git
cd pincherOS
# Export reflexes as .nail files
pincher export --format nail --output ./reflexes/
```

The `.nail` files bridge lever-runner and pincherOS — lever-runner writes execution state, pincherOS reads it for reflex matching.

### Step 3: Build a git-native agent

```bash
# Fork the template
gh repo fork SuperInstance/agent-template --clone
cd agent-template
# Customize on a branch
git checkout -b my-agent
# Edit agent.yaml, commit, push — that's your agent
```

### Step 4: Run PLATO rooms (multi-agent coordination)

```bash
git clone https://github.com/SuperInstance/PLATO.git
cd PLATO
# Create a room with multiple agents
plato room create --agents "./my-agent,./lever-runner" --task "monitor and respond"
```

## Token Math

The whole point: agents that run lean.

| Approach | Tokens per action | Caching | Safety |
|----------|------------------|---------|--------|
| Raw LLM → shell | 500-2000 | None | Injection-vulnerable |
| lever-runner alone | ~70 | None | Injection-proof |
| lever-runner + pincherOS | ~5 (cache hit) | Reflex | Injection-proof |
| Full stack | ~5-70 | Reflex + distilled | Injection-proof + coordinated |

A full-stack agent uses **35-140x fewer tokens** than naive LLM→shell execution. That's the difference between a toy and a production system.

## What Ships vs. What's Planned

**Ships today:**
- lever-runner: parameterized commands, skill packs, Docker, web dashboard, 142 tests
- pincherOS: reflex matching, `.nail` migration, 130 tests passing
- open-mind: induction engine, tripartite synchronizer, conservation verification
- agent-template: forkable git-native agent template
- intelligent-terminal: tripartite-classified subsystems
- conservation-spectral-topology-rs: Rust conservation law verification

**In progress:**
- PLATO room adapter

**Planned:**
- GPU-accelerated embedding pipeline
- WASM carapace for browser-based agents
- Edge deployment (Raspberry Pi)
- Agent marketplace

## Real Induction Results

Live numbers from automated codebase analysis via the open-mind induction engine:

| Repo | Functions | Vectors | Call Graph |
|------|-----------|---------|------------|
| lever-runner | 221 | 221 | 918 |
| pincherOS | 113 | 113 | 308 |
| intelligent-terminal | 26 | 26 | 82 |

### Conservation Law Verification

| Metric | Value |
|--------|-------|
| Ecosystem health | 0.78 / 1.00 |
| PLATO utilization | 94.7% (bottleneck) |
| Conservation leakage | 0 (verified) |
| Algebraic connectivity | 1.382 |

Total: **22 agents** run across ecosystem, **327+ tests** passing.

## Repos

| Repo | Layer | Status |
|------|-------|--------|
| [lever-runner](https://github.com/SuperInstance/lever-runner) | Execution | Shipping |
| [pincherOS](https://github.com/SuperInstance/pincherOS) | Memory | Shipping |
| [PLATO](https://github.com/SuperInstance/PLATO) | Intelligence | In development |
| [agent-template](https://github.com/SuperInstance/agent-template) | Identity | Shipping |
| [open-mind](https://github.com/SuperInstance/open-mind) | Induction | Shipping |
| [intelligent-terminal](https://github.com/SuperInstance/intelligent-terminal) | Terminal | Shipping |
| [conservation-spectral-topology-rs](https://github.com/SuperInstance/conservation-spectral-topology-rs) | Verification | Shipping |
| [captains-log](https://github.com/SuperInstance/captains-log) | Coordination | Shipping |
| [superinstance-ecosystem](https://github.com/SuperInstance/superinstance-ecosystem) | Meta | This repo |

## License

Each layer has its own license. Check individual repos.
