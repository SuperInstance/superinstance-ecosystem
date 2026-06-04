# Technical Deep Dive: SuperInstance Repos

**Date:** 2026-06-03
**Analyst:** Subagent (technical-deep-dive)
**Source:** Actual source code review — not READMEs

---

## 1. pincherOS (~22K lines, mostly Rust)

### 1.1 Crate Structure

Two workspace crates + a Python sidecar:

| Crate | Purpose | Lines (approx) |
|-------|---------|-----------------|
| `pincher-core` | Library: reflex engine, embedding, DB, security, migration, immunology, sandbox, resource control, RPC | ~5K+ Rust |
| `pincher-cli` | Thin CLI (`pincher` binary) using `clap` | ~200 Rust |
| `pincher-infer/` | Python sidecar for LLM refinement (separate `pyproject.toml`) | Not deeply analyzed |

Feature flags in `pincher-core`:
- `onnx` — pulls in `ort` + `ndarray` for real ONNX inference
- `landlock` — Linux-only kernel sandboxing via `landlock` crate
- `wasmtime` — WASM runtime for carapace guest modules (future)

**Important:** The codebase is mid-migration from a legacy architecture to a new one. `lib.rs` marks `engine.rs`, `embedder.rs`, and `types.rs` as deprecated. The canonical path is `reflex::ReflexEngine`, `embed::Embedder`.

### 1.2 Reflex Lifecycle: teach → embed → match → execute → learn

**Teach** (`ReflexEngine::teach`):
1. Check if intent already exists (string match). If so, update its embedding.
2. Embed the intent string → 384-dim vector.
3. Insert into SQLite `reflexes` table with UUID, confidence=0.5.

**Match** (`matcher::match_reflex`):
1. Embed the incoming intent.
2. Fast path: exact string match → return `MatchResult::Exact` with real cosine similarity.
3. Slow path: `sqlite-vec` ANN search → top-5 candidates → re-rank with cosine similarity.
4. Three-tier classification:
   - **Exact** (≥ 0.80 cosine) — short-circuit, execute directly
   - **Similar** (≥ 0.55) — execute with LLM refinement hint
   - **Novel** (< 0.55) — no match, needs new reflex

**Execute** (`ReflexEngine::execute_reflex`):
1. **Security gate**: VetoEngine checks action against rules (ForbiddenCommand, ForbiddenPath, etc.)
2. **Built-in dispatch**: 10 built-in intents (`system.info`, `file.read`, `file.write`, `process.list`, `process.kill`, `network.ping`, `git.status`, `git.diff`, `docker.ps`, `env.get`)
3. **SQL execution**: Only static SELECT queries allowed. Dynamic `{{input}}` interpolation is **prohibited**. Non-SELECT must go through sandbox.
4. Post-execution: increment invoke count, log action with latency.

**Learn** (confidence update):
- `confidence::update_confidence` uses multiplicative model:
  - Success: `+5% of gap toward 1.0` → asymptotic approach
  - Failure: `-10% of current value` → exponential decay
- Clamped to [0.01, 0.99]
- Three execution paths: Direct (> 0.80), Confirm (0.55–0.80), LlmRoute (< 0.55)

### 1.3 Migration System (QTR Protocol, .nail Format)

**QTR Protocol** (`migration/qtr.rs`) — three phases:
1. **Quiesce**: Checkpoint WAL, end all sessions — make DB consistent
2. **Transfer**: Copy file + compute BLAKE3 hash
3. **Resume**: Probe new shell environment, save profile to DB

**.nail Format** (`migration/pack.rs`):
- `tar.zst` archive containing: `reflexes.db`, `identity.json`, `config.toml`, `manifest.json`
- `NailManifest` with version, fingerprint, timestamp, reflex count, BLAKE3 checksums
- `AgentIdentity` (name), `AgentConfig` (model preferences), `AgentPreferences`
- Pack: serialize DB → build manifest → compress to tar.zst
- Unpack: decompress → verify checksums → validate fingerprint → load DB

**Fingerprinting** (`migration/fingerprint.rs`):
- `ShellFingerprint`: hostname, OS, CPU count, RAM, GPU
- `compatibility_score()` computes a 0–1 compatibility between two fingerprints
- Used to assess migration viability between environments

### 1.4 Immunology Module

This is a security/anomaly detection system with a biological metaphor:

**Antigen Detection** (`immunology/antigen.rs`):
- Regex-based pattern matching against known threats
- Four antigen kinds: `PromptInjection`, `MaliciousAction`, `ResourceAbuse`, `StaleReflex`
- ~28 prompt injection patterns (instruction overrides, system prompt extraction, role manipulation, jailbreak, DAN mode, etc.)
- ~12 malicious action patterns (command injection, SQL injection, path traversal)
- Confidence scoring: base threshold + multi-match boost (0.15 per additional match)
- Resource abuse: rate limit (default 60/min)

**Immune Memory** (`immunology/memory.rs`):
- Antibodies = learned rejection patterns stored in SQLite
- Lifecycle: creation from high-confidence antigens → activation (generation count increment) → decay (prune after inactivity if generation < 3)
- `is_blocked()` checks input against all antibodies, auto-activates matches
- Pruning: removes antibodies with `last_seen < cutoff AND generation_count < 3`

**Self-healing**: The module is designed to flag stale reflexes for LLM recompilation (done by pincher-infer sidecar, not internally).

### 1.5 Embedder — ONNX Details

**Model**: `all-MiniLM-L6-v2` (sentence-transformers), INT8 quantized ONNX from HuggingFace
- **Dimensions**: 384
- **Inference**: `ort` crate (ONNX Runtime) with GraphOptimizationLevel::Level3, 2 threads
- **Tokenizer**: Custom `SimpleTokenizer` — whitespace + punctuation split, chunked subword tokenization (4-char chunks with `##` prefix), hash-based token ID assignment, max_length=128, [CLS]/[SEP] tokens
- **Pooling**: Mean pooling over non-padding tokens (using attention mask), then L2 normalization
- **Fallback**: When ONNX unavailable → `deterministic_embedding()` using SHA-256 trigram hashing + word hashing + global hash, L2 normalized. This ensures teach-then-match works even without the model.
- **Download**: `curl -L` from HuggingFace to `~/.pincher/models/`

**Critical observation**: The custom tokenizer is *not* a proper WordPiece/BPE tokenizer. It splits on whitespace, chunks into 4-char subwords, and hashes to token IDs. This means the ONNX model receives different token distributions than it was trained on. The fallback hash-based embeddings are deterministic but semantically meaningless — they're for operational continuity, not quality.

### 1.6 Sandbox/Capability System Depth

**Three-layer defense:**

1. **VetoEngine** (`security/veto.rs`): Deterministic pre-execution rule engine. Rules: ForbiddenCommand (substring), ForbiddenPath, MaxFileSize (100MB), RequireCapability, ForbiddenPattern. Default rules block `rm -rf /`, `mkfs`, `dd`, system paths (`/etc`, `/sys`, `/proc`, `/boot`, `/dev`), network tools (`curl`, `wget`, `ssh`, `nc`), and package managers. Rules loadable from TOML.

2. **Bubblewrap Sandbox** (`sandbox/bwrap.rs`): If `bwrap` is on PATH, commands run inside a Linux namespace sandbox with restricted filesystem mounts, no network by default, executable whitelist. **Fails closed** — if `bwrap` not found, execution is refused entirely (no unsandboxed fallback).

3. **Built-in Reflex Safety**: Each built-in has its own hardening:
   - `file.read`: canonicalizes paths, blocks `/etc/shadow`, `/root/.ssh`, etc.
   - `file.write`: restricted to `/tmp`, `/var/tmp`, relative paths
   - `process.kill`: blocks PIDs ≤ 100 and self
   - `env.get`: allowlist of safe env vars only
   - SQL actions: no `{{input}}` interpolation, only static SELECTs

4. **Capability Tokens** (`capability/`): Manifest-based permission system with signed tokens (structure exists, integration appears incomplete)

5. **Landlock** (optional feature): Linux kernel-level sandboxing via landlock LSM

### 1.7 PID Controller for Resource Homeostasis

**ResourceController** (`resource/pid.rs`):
- Classic PID controller tuned for RAM utilization
- Gains: kp=2.0, ki=0.1, kd=0.5, target=75% RAM utilization
- Anti-windup: integral clamped to [-1.0, 1.0]
- Three runtime modes based on RAM:
  - **Normal** (< 80%): Full LLM + reflex engine
  - **Light** (80–90%): Reduced context window
  - **Critical** (> 90%): Reflex-only, LLM unloaded
- Control actions: `Maintain`, `UnloadLLM`, `ReduceContextWindow`, `LoadLLM`

### 1.8 Key Technical Risks / Unfinished Parts

1. **Custom tokenizer vs. ONNX model**: The `SimpleTokenizer` doesn't use WordPiece. Token IDs are hash-derived, not from MiniLM's actual vocabulary. This means ONNX embeddings may be significantly worse than the Python sentence-transformers equivalent. The quality of the entire reflex matching system depends on embedding quality.

2. **Legacy code still present**: `engine.rs`, `embedder.rs`, `types.rs` are deprecated but not removed. Risk of divergence or confusion.

3. **ReflexEngine owns Connection**: No connection pooling, no async DB access. SQLite is synchronous. The RPC server (`rpc/server.rs`) exists but the engine itself isn't designed for concurrent access.

4. **VetoEngine::default() uses hardcoded rules**: The `with_defaults()` constructor creates rules in code, not loaded from config. Runtime rule updates require restart unless `load_rules()` is called explicitly.

5. **carapace/ and wasmtime**: The carapace module (host.rs, guest.rs, capability.rs) exists for WASM-based guest modules, but the `wasmtime` feature appears unfinished — no substantive guest execution logic.

6. **dynamics/ and veto/ duplication**: Both `dynamics/veto.rs` and `security/veto.rs` exist. The dynamics module appears to be a research prototype for ML-based command dynamics.

7. **cognitive/ research prototype**: `docs/research/prototypes/cognitive/` contains phantom.rs, actualization.rs — clearly experimental, not production code.

8. **No telemetry/metrics**: No Prometheus, OpenTelemetry, or structured metrics. Only tracing spans.

9. **SQLite-vec for ANN**: Uses sqlite-vec extension for vector search. For large reflex tables (>10K), ANN quality and latency are unknown.

10. **pincher-infer sidecar**: The Python sidecar responsible for LLM refinement is separate and not deeply integrated — the Rust core only flags "needs LLM" but doesn't call it.

---

## 2. lever-runner (~4.6K lines, Python)

### 2.1 Orchestrator Flow: request → LLM intent → embed → LanceDB → sandbox → trust update

**`orchestrator.do()`**:
1. `extract_intent(user_request)` → LLM call → compressed 3-8 word phrase
2. `store.find_best(phrase, top_k=3)` → LanceDB vector search
3. Filter by trust floor (default 40.0): eligible = matches above floor, or top-1
4. Pick lowest L2 distance among eligible
5. Similarity floor check (default 0.55): if below, return "no match"
6. `run_command(chosen.command)` → subprocess in `/tmp/lever-runner/<sid>/`
7. `store.update_trust(id, success=...)` → +1.5 on success, -4.0 on failure, clamped [0, 100]
8. Return `DoResult` with full accounting

**Entry points**: `bot.py` (Telegram), `cli.py` (CLI), `http_api.py` (HTTP POST)

### 2.2 auto_promote Self-Improvement Loop

Designed to run hourly via cron. Two jobs per chat:

**Promote Winners**:
- Commands with `success_count > 20` and `trust_score < 90` → +10 trust
- Clamped at 100

**Rewrite Losers**:
- Commands with `trust_score < 30` and `failure_count ≥ 5` → candidates
- If `REMOTE_LLM_API_KEY` is set, sends to remote LLM (default Claude 3.5 Sonnet) asking for a corrected command
- Inserts fix at trust=40, soft-deletes old row
- If no remote key, just logs candidates (safe for fresh installs)

**Multi-chat sweep**: `_iter_chat_tables()` discovers all `commands_*` tables in LanceDB and runs both jobs on each.

### 2.3 Skill Pack Format and Import/Export

**Format**: JSONL, one JSON object per line:
```json
{"intent_phrase": "show disk usage", "command": "df -h"}
```
Optional fields: `trust_score`, `success_count`, `failure_count`

**Import** (`seed_import.py`):
- Reads JSONL from file or stdin
- Options: `--trust` (default starting trust), `--reset` (drop table), `--skip-existing`
- Embeddings computed locally on import (batch encoded via sentence-transformers)

**Export** (`seed_export.py`):
- Dumps table to JSONL, embeddings NOT included
- `--min-trust` filter, `--include-stats` for trust/success/failure counts

**Initial seeding**: `init_db.py` contains ~66 seed commands. Each new chat gets these bulk-imported on first use via `CommandStore._seed_from_init_db()`.

### 2.4 Provider Fallback Chain Implementation

**Primary backend**: Configured via `LLM_BACKEND` env var (default: "minimax")

**Fallback chain** (`_resolve_fallback_chain`):
1. Read `LLM_FALLBACKS` env var (default: "deepinfra")
2. Exclude primary from chain
3. Filter to known backends
4. Always append "passthrough" as last resort

**Full resolution**: [primary] + [fallback1, fallback2, ...] + [passthrough]

**Per-backend config**:
- Each backend has defaults in `BACKEND_DEFAULTS` dict (base_url, model, key_envs)
- API key resolution: explicit kwarg → `LLM_API_KEY` → backend-specific env vars
- Per-backend env overrides: `LLM_<BACKEND>_BASE_URL`, `LLM_<BACKEND>_MODEL`
- **Important**: Primary's `LLM_BASE_URL`/`LLM_MODEL` are NOT applied to fallbacks (prevents URL leaking)

**Error handling**:
- Timeout/ConnectionError → continue to next
- HTTP 429/5xx → continue to next
- HTTP 401 → skip to next (key may be expired)
- HTTP 4xx (other) → raise (config bug, will fail everywhere)
- Missing API key → skip to next

**Passthrough**: The raw user request (normalized) becomes the intent phrase. Zero tokens. Complete provider outage degrades gracefully.

### 2.5 Per-Chat Isolation Model

**v0.2 architecture**: Each Telegram chat gets its own LanceDB table named `commands_<chat_id>`.

- `_table_name_for(chat_id)`: sanitizes to alphanumeric+underscore, falls back to "default"
- Legacy migration: v0.1.x `commands` table auto-renamed to `commands_default`
- Each chat starts with the 66-command seed pack (bulk import on first `CommandStore()` construction)
- `auto_promote` sweeps all chat tables independently
- Schema seed row (`id="__schema_seed__"`) bootstraps table schema, excluded from all queries

### 2.6 Token Economics — The ~70-90 Token Claim

**What the README claims**: "< 200 tokens per executed command (target; real production cost is ~70–90 with a hosted LLM, ~6 with passthrough)"

**What the code actually does**:

1. **LLM call** (~60 in / ~8 out):
   - System prompt: ~55 words ≈ ~60 tokens (the SYSTEM_PROMPT asking for 3-8 word phrase compression)
   - User message: varies, but typically short
   - Output: 3-8 words ≈ ~8 tokens
   - **Total: ~70 tokens** for the LLM call

2. **Embedding**: MiniLM-L6-v2 embedding of the intent phrase — counted separately, ~12 tokens equivalent per the token_logger

3. **Total per command**: ~70 (LLM) + ~12 (embedding) ≈ **~82 tokens**

**The ~70-90 claim is real and accurate for the happy path.** It's achieved because:
- The LLM only sees a tiny system prompt (~60 tokens) + the user's message
- No tool schemas, no examples, no chain-of-thought
- max_tokens=32 on the LLM call
- The embedding is a local operation, not an LLM call

**With passthrough**: 0 LLM tokens + ~6 embedding tokens ≈ **~6 tokens**. This is literally free if you skip the LLM.

**Comparison point**: Tool-calling agents routinely embed 1.5K–8K tokens of tool schemas per turn. lever-runner's ~82 tokens is a ~20-100x reduction.

**Benchmark** (`benchmark.py`): Forces passthrough mode, runs 20 tasks, measures intent + embed tokens. Target: < 200 tokens. In passthrough mode this is trivially met since the LLM is skipped.

### 2.7 Key Technical Risks / Unfinished Parts

1. **Sandbox is "just a directory"**: The executor creates `/tmp/lever-runner/<sid>/` and runs `subprocess.run(command, shell=True, executable="/bin/bash")`. This is a chdir sandbox, not a namespace/capability sandbox. There's no filesystem isolation beyond working directory — commands can still `cd /` or access any path. Compare pincherOS's bubblewrap sandbox.

2. **SQL injection in LanceDB queries**: `store.update_trust()` uses `f"id = '{row_id}'"` in LanceDB `where` clauses. The `soft_delete()` similarly uses `f"id = '{row_id}'"`. While LanceDB's SQL is limited, the pattern is concerning if row IDs are ever user-controlled (they're UUIDs, so risk is low in practice).

3. **`shell=True` in executor**: The subprocess uses `shell=True` with user-taught commands. While commands are pre-approved (they come from the LanceDB table), a compromised table (via seed import or LLM rewrite) could contain arbitrary shell commands with no additional sandboxing.

4. **No authentication on HTTP API**: `http_api.py` exposes a POST endpoint with no auth check. The Telegram bot checks `ALLOWED_USER_ID` but the HTTP interface doesn't.

5. **Thread safety**: `CommandStore` uses a `threading.Lock` for `update_trust` only. Other operations (teach, find_best, list_all) are not synchronized. Race conditions possible under concurrent access.

6. **LanceDB limitations**: `read_consistency_interval=0` (forced freshness) may have performance costs. LanceDB doesn't support rename, so the legacy migration creates a new table + drops old (data copy).

7. **Embedding model loaded per-CommandStore**: `_get_embedder()` creates a new `SentenceTransformer` instance. If multiple CommandStore instances exist (one per chat), each loads the model independently (~80MB RAM each). No global singleton.

8. **auto_promote rewrite trust**: Rewritten commands start at trust=40 (`TRUST_REWRITTEN`), which is below the default trust floor of 40.0 — so they're exactly at the borderline. A single failure would drop them below the floor. Consider starting at 50 or 55.

9. **No schema versioning**: The LanceDB table schema is implicit (defined by the first row). No migration path if fields are added/changed.

10. **fallback chain logs but doesn't alert**: Provider failures in the fallback chain are logged as warnings but there's no alerting or circuit-breaker. Repeated provider outages will silently degrade to passthrough.

---

## 3. Comparative Analysis

| Dimension | pincherOS | lever-runner |
|-----------|-----------|--------------|
| **Language** | Rust (core) + Python (sidecar) | Python |
| **Embedding DB** | SQLite + sqlite-vec | LanceDB |
| **Embedding model** | ONNX MiniLM-L6-v2 (custom tokenizer) | sentence-transformers MiniLM-L6-v2 (proper tokenizer) |
| **Sandboxing** | Bubblewrap namespaces + Landlock + veto rules | chdir to /tmp session dir |
| **Security layers** | 4+ (veto, sandbox, built-in safety, immunology) | 1 (pre-approved command table) |
| **LLM integration** | Sidecar only for refinement | Direct HTTP call for intent extraction |
| **Self-improvement** | Confidence decay + immunology | Trust scores + auto_promote with LLM rewrite |
| **Migration** | Full QTR protocol + .nail archives | JSONL seed import/export |
| **Multi-tenancy** | None visible | Per-chat LanceDB tables |
| **Embedding quality** | Likely degraded (custom tokenizer) | Proper (sentence-transformers) |
| **Maturity** | Early prototype, architectural ambition | Simpler, more complete for its scope |

### The Core Insight

Both projects share the same thesis: **separate the LLM from command execution**. The LLM should compress intent, not generate commands. Commands come from a pre-approved vector-searchable table.

pincherOS is the more ambitious attempt — it wants to be a full "post-model OS" with immunology, sandboxing, capability systems, and migration. But it's earlier and has fundamental issues (custom tokenizer).

lever-runner is pragmatic and more complete within its scope. It's a working Telegram bot with real token economics. Its sandbox is weaker, but its embedding quality is better and its operational model is simpler.

Both are early-stage software from the same org (SuperInstance) exploring the "intent-to-command" space from different angles.
