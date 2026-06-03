# Architecture

Technical deep-dive into how the four layers connect.

## Data Flow

```
Human Input
    │
    ▼
┌──────────────────┐
│  Intent Extraction │  ← PLATO (or lightweight classifier)
│  "deploy staging"  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Reflex Match     │  ← pincherOS
│  cache hit? → done │  (skip everything if matched)
└────────┬─────────┘
         │ miss
         ▼
┌──────────────────┐
│  Command Match    │  ← lever-runner skill pack
│  → deploy(env=X)  │  parameterized, ~70 tokens
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Execution        │  ← lever-runner
│  sandboxed shell  │  injection-proof
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Cache Write      │  ← pincherOS
│  .nail file       │  intent → command mapping saved
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Distillation     │  ← PLATO (periodic)
│  compress history │  extract reusable patterns
└──────────────────┘
```

## API Surface by Layer

### lever-runner

```
run(intent: string, context?: SkillPack) → ExecutionResult
validate(command: ParameterizedCommand) → ValidationResult
registerSkillPack(pack: SkillPack) → void
```

Core invariant: **every** execution passes through parameterized command matching. Raw strings never touch the shell.

### pincherOS

```
match(intent: string) → CacheResult | null
write(intent: string, result: ExecutionResult) → NailFile
export(format: "nail") → NailFile[]
migrate(from: NailFile, to: PincherInstance) → void
```

Core invariant: cache reads are O(1)-ish via reflex matching. No LLM call on cache hits.

### PLATO

```
createRoom(agents: Agent[], config: RoomConfig) → Room
assignEnsign(room: Room, watch: WatchCondition) → Ensign
distill(history: Interaction[]) → DistilledKnowledge
escalate(from: Agent, to: Agent, context: any) → void
```

Core invariant: rooms own their agents. Agents don't talk to each other directly — rooms mediate.

### git-native agents

```
fork(template: Repo) → AgentRepo
branch(agent: AgentRepo, behavior: string) → Branch  # new behavior variant
evolve(agent: AgentRepo, via: PullRequest) → Agent   # merge = learning
revert(agent: AgentRepo, to: Commit) → Agent         # rollback = forgetting
```

Core invariant: agent state IS git state. If it's not committed, it doesn't exist.

## Integration Points

### lever-runner ↔ pincherOS

The `.nail` file is the bridge. After lever-runner executes a command, it (or pincherOS) writes a `.nail` file capturing:

- The original intent (human-readable)
- The matched command (parameterized)
- The execution result (stdout, exit code, duration)
- A reflex hash for O(1) matching

On the next invocation, pincherOS checks the reflex cache before lever-runner does any work. Cache hit → instant response, no LLM call, no execution.

### pincherOS ↔ PLATO

PLATO reads `.nail` files to understand what an agent has been doing. It distills interaction patterns into higher-level knowledge — not just "this command worked" but "this *class* of commands works, and here's the pattern."

Distilled knowledge feeds back into pincherOS as enriched cache entries with broader matching scope.

### PLATO ↔ git-native agents

PLATO rooms assign work to agents. Agents execute via lever-runner, cache via pincherOS. When an agent learns something (new skill, better command), it commits to its repo. PLATO can then review the commit (as a PR) and merge it into the agent's identity.

Evolution loop: execute → cache → distill → commit → PR → merge → evolve.

### lever-runner ↔ git-native agents

Skill packs live in the agent's repo. `agent.yaml` defines which skill packs the agent uses. Forking the agent = forking its capabilities. Adding a skill pack = adding a branch.

## The .nail File Format

```yaml
# A .nail file — the bridge between execution and memory
version: 1
reflex:
  hash: "sha256:a1b2c3..."          # intent fingerprint
  pattern: "deploy to {env}"         # parameterized pattern
  confidence: 0.94
execution:
  command: "deploy(env=staging)"     # lever-runner parameterized command
  skill_pack: "core"                 # which skill pack matched
  tokens_used: 68                    # tokens consumed
  exit_code: 0
  duration_ms: 234
context:
  agent: "my-deploy-agent"           # git-native agent identity
  room: "devops"                     # PLATO room (if applicable)
  timestamp: "2025-01-15T10:30:00Z"
```

Properties:
- **Portable**: copy a `.nail` file between pincherOS instances, cache works everywhere
- **Auditable**: every cached action has a full provenance chain
- **Composable**: PLATO reads `.nail` files to build distillation, writes back enriched entries

## How git-native Agents Compose

```
Template Repo
    │
    ├── fork ──→ Agent A (branch: "deploy-skills")
    │               │
    │               ├── PR: add k8s skill pack ──→ merge → Agent A evolves
    │               └── PR: add rollback logic ──→ merge → Agent A evolves
    │
    ├── fork ──→ Agent B (branch: "monitoring")
    │               │
    │               └── cherry-pick from Agent A → Agent B gains deploy skills
    │
    └── fork ──→ Agent C (minimal)
                    │
                    └── PLATO assigns Agent C to room → Agent C learns from room distillation
```

This is evolution via git. Fork = speciation. Merge = learning. Cherry-pick = knowledge transfer. Revert = forgetting. The git log IS the agent's memory.

## Conservation Laws as Resource Governance

PLATO enforces conservation laws — invariants that must hold across all agent behavior:

1. **Token conservation**: total tokens consumed ≤ budget. If an agent is burning tokens, PLATO throttles.
2. **Action conservation**: every action must produce a `.nail` cache entry. No orphan executions.
3. **Identity conservation**: every action is attributable to an agent repo. No anonymous commands.
4. **Evolution conservation**: every behavior change goes through PR. No direct-to-main commits.

These aren't just guidelines — PLATO verifies them. Violations trigger escalation to the room owner (the human).

## Extending the Stack

To add a new layer:

1. Define its API surface (inputs, outputs, invariants)
2. Identify integration points with existing layers
3. Ensure it produces `.nail`-compatible output (if it executes)
4. Ensure it reads `.nail` files (if it reasons about execution)
5. Make it git-native (if it has identity/state)

The architecture is designed to be extended, not replaced. New layers slot in; existing layers don't change.

## Tripartite Synchronizer Decision Matrix

The tripartite synchronizer classifies every system into three orthogonal dimensions:

| Dimension | Role | Measures |
|-----------|------|----------|
| **Structure** | What it is | Types, modules, AST topology |
| **Dynamics** | What it does | Call graphs, data flow, control flow |
| **Semantics** | What it means | Intent, invariants, conservation laws |

Decision rule: a change is safe iff all three dimensions agree. If structure says "add function" but dynamics says "no callers" or semantics says "violates invariant", the change is rejected.

This applies at every level — from individual PRs to cross-repo coordination.

## open-mind Induction/Deduction Loop

```
  Source Code (lever-runner, pincherOS, ...)
      │
      ▼
  ┌─────────────┐
  │  Induction   │  Extract functions, vectors, call graphs
  │  (bottom-up) │  from real codebases
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │  Tripartite  │  Classify into structure / dynamics / semantics
  │  Mapping     │  Build cross-repo topology
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │  Conservation│  Verify invariants hold across the topology
  │  Checking    │  (Rust-powered spectral analysis)
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │  Deduction   │  Derive new commands, skill packs, agent behaviors
  │  (top-down)  │  from verified structure
  └──────┬──────┘
         │
         ▼
    New code, new agents, new skill packs
    → fed back into induction
```

The loop is continuous. Every commit to any repo triggers re-induction, re-verification, and potentially new deductions.

## intelligent-terminal Tripartite Map

The intelligent-terminal was analyzed via open-mind induction and classified into 6 subsystems:

| Subsystem | Type | Functions | Call Edges |
|-----------|------|-----------|------------|
| Terminal Core | Structure | 8 | 24 |
| Input Handler | Dynamics | 5 | 16 |
| Output Renderer | Dynamics | 4 | 12 |
| Command Parser | Structure | 3 | 10 |
| History Manager | Semantics | 3 | 12 |
| Plugin Host | Semantics | 3 | 8 |

Total: 26 functions induced, 82 call graph edges, tripartite-classified.

## Conservation Law Verification Results

Verified via `conservation-spectral-topology-rs` (Rust):

| Law | Status | Notes |
|-----|--------|-------|
| Token conservation | ✅ Verified | Budget bounds enforced |
| Action conservation | ✅ Verified | Every action produces `.nail` entry |
| Identity conservation | ✅ Verified | All actions attributable to agent repos |
| Evolution conservation | ✅ Verified | All changes via PR, no direct-to-main |
| Conservation leakage | ✅ 0 | No invariant violations detected |

Overall ecosystem health: **0.78 / 1.00**
Algebraic connectivity: **1.382** (strong cross-repo coupling)
PLATO utilization: **94.7%** (identified as bottleneck for scaling)
