# Beta Tester Recruitment & Cycling Plan
## pincherOS + lever-runner

---

## Phase 1: Inner Circle (Week 1)
### Who: People already in the SuperInstance orbit
- OpenClaw Discord regulars
- Anyone who starred SuperInstance repos
- AI agent Twitter mutuals

### What to send:
- Personal DM: "Hey, I built something weird. It's an OS for AI agents that learns your commands and stops calling the LLM for stuff it already knows. Want to break it?"
- 1-paragraph pitch, link to repo, no docs to read
- Ask for ONE thing: "Install it and tell me what confused you"

### pincherOS pitch:
> "pincherOS is what happens if Docker and a hermit crab had a baby that hates API bills. You teach your agent skills once. Next time, it runs them locally at 50ms for $0. The LLM only fires when something is genuinely new. Works on a Raspberry Pi."

### lever-runner pitch:
> "lever-runner is a 70-token AI command runner. You type 'check disk usage', it runs df -h. No tool schemas, no JSON, no 5000-token context windows. The LLM never sees your shell. It self-improves hourly. There's a skill pack marketplace."

---

## Phase 2: Targeted Communities (Week 2-3)

### r/LocalLLaMA
- **Why**: Obsessed with running things locally, reducing token costs, edge deployment
- **Angle**: "I made an agent OS that caches learned behaviors in a vector DB. Known intents run at 50ms with zero LLM calls. Works on a Pi 4."
- **Tone**: Technical, show the architecture diagram, post benchmarks

### r/selfhosted
- **Why**: Love running things on their own hardware, hate recurring costs
- **Angle**: "Self-hosted AI agent that gets cheaper the more you use it. No cloud dependency. Pack it up, move it to another machine."
- **Tone**: Practical, "here's my setup" style

### r/rust
- **Why**: 22K lines of well-structured Rust with real architecture
- **Angle**: "Built an agent OS in Rust with ONNX embeddings, SQLite reflex store, PID resource control, bwrap sandboxing"
- **Tone**: Code-first, show the crate structure

### r/devops + r/kubernetes
- **Why**: lever-runner is basically an intent-based ops assistant
- **Angle**: "Your on-call junior that never fat-fingers a command. Teaches itself from your runbooks."
- **Tone**: Problem-solution, "here's what 3am looks like with and without this"

### Lobsters
- **Why**: Technical audience that appreciates novel systems work
- **Angle**: Systems-level framing, "vector DB as execution runtime"
- **Tone**: Academic-ish, reference the architecture decisions

## Phase 3: Content Flywheel (Week 3-4)

### Blog Post 1: "I accidentally built Docker for AI agents"
- pincherOS origin story
- The reflex caching insight
- Benchmarks: first run vs 50th run

### Blog Post 2: "How I cut my AI agent's token usage by 95%"
- lever-runner vs tool-calling comparison
- Real numbers from the benchmark
- The self-improvement loop

### Blog Post 3: "Running an AI agent on a Raspberry Pi for $0/month"
- pincherOS + lever-runner together
- Full deployment walkthrough
- PID controller keeping it alive under memory pressure

### Video Demo: "Teaching an AI agent in 30 seconds"
- Screen recording: install, teach 3 commands, watch them execute instantly
- No narration needed — just terminal + speed

---

## Beta Tester Onboarding Flow

### For pincherOS:
1. `git clone` + `cargo build` (or download binary)
2. `pincher teach "list files" --action "ls -la"`
3. `pincher do "show me the files"`
4. Watch it match and execute in 50ms
5. `pincher pack` → move to another machine → `pincher unpack`
6. Agent still knows everything

### For lever-runner:
1. `curl install.sh | bash` (pulls Ollama, embeddings, seeds DB)
2. `/teach "show docker containers" | docker ps` in Telegram
3. `/do check containers`
4. Watch: ~70 tokens, instant execution
5. `/status` to see trust scores
6. Come back in an hour — auto_promote has improved things

### What to measure from beta testers:
- Time from clone to first successful execution
- Number of reflexes taught in first session
- Token usage (lever-runner) or LLM call savings (pincherOS)
- Confusion points / error messages
- Device diversity (Pi? Mac? Linux? Windows?)
- Migration success rate (pincherOS)

---

## Beta Tester Cycling

### Round 1 (Week 1): 5-10 inner circle
- Goal: Does it even install? Does the core loop work?
- Fix: install bugs, unclear error messages, missing deps

### Round 2 (Week 2): 15-25 community recruits
- Goal: Does the value proposition land? Do they teach >10 reflexes?
- Fix: UX friction, docs gaps, edge cases

### Round 3 (Week 3): 50+ via blog posts + HN
- Goal: Scale test. Diverse hardware. Skill pack sharing.
- Fix: Performance at scale, skill pack compatibility, migration edge cases

### Round 4 (Week 4+): Public launch
- HN post, Reddit posts, Twitter thread
- All bugs from R1-R3 fixed
- Killer demo video ready
- Skill pack marketplace seeded

---

## Quick Wins to Add Before Beta

### pincherOS:
- [ ] `pincher doctor` command that checks install health
- [ ] Pre-built binaries (cross-compiled for Pi, Mac, Linux)
- [ ] Example reflex pack (docker, git, file ops)
- [ ] One-command install: `curl -fsSL ... | bash`

### lever-runner:
- [ ] Docker image for easy deployment
- [ ] Web UI (even basic) for non-Telegram users
- [ ] Skill pack standardization (JSON schema)
- [ ] Public skill pack repo seeded with 10+ packs
- [ ] `lever-runner doctor` for debugging
