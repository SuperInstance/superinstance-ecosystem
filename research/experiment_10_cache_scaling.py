#!/usr/bin/env python3
"""
Experiment 10: Failure Cache Hit-Rate Scaling
Simulates query distribution and measures cache hit rate vs cache size.
"""
import numpy as np
import hashlib
import struct

# Position-aware embedding (same as lever-runner)
def position_aware_embed(text, dim=64):
    words = text.lower().split()
    vec = np.zeros(dim)
    for i, word in enumerate(words):
        h = int(hashlib.md5(word.encode()).hexdigest(), 16)
        for j in range(dim):
            phase = (h >> (j % 32)) & 1
            pos_weight = 1.0 / (1.0 + i)  # earlier words weighted more
            vec[j] += pos_weight * (1 if phase else -1)
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec

# Generate synthetic command corpus
commands = [
    "check disk usage", "list running processes", "show memory stats",
    "restart nginx", "check nginx status", "tail error logs",
    "show network connections", "kill process by name", "find large files",
    "check cpu temperature", "mount external drive", "unmount drive",
    "create backup", "restore from backup", "schedule cron job",
    "check uptime", "show logged in users", "change file permissions",
    "compress directory", "extract archive", "search file contents",
    "count lines in file", "sort file by column", "remove empty lines",
    "download file from url", "upload file to server", "sync directories",
    "check port status", "open firewall port", "block ip address",
    "show routing table", "trace route to host", "dns lookup",
    "ping remote host", "check ssl certificate", "generate ssh key",
    "add user account", "delete user account", "modify user group",
    "check disk io", "show swap usage", "clear page cache",
    "list docker containers", "start docker container", "stop all containers",
    "pull docker image", "build docker image", "check container logs",
    "run python script", "install python package", "create virtual environment",
    "run database query", "backup database", "restore database",
    "check table sizes", "list database users", "optimize table",
    "show git status", "commit all changes", "push to remote",
    "create new branch", "merge branch", "resolve merge conflict",
    "show git log", "diff between commits", "stash changes",
    "compile rust project", "run cargo test", "update dependencies",
    "format code", "lint codebase", "run type checker",
    "start development server", "run test suite", "generate documentation",
    "deploy to staging", "deploy to production", "rollback deployment",
    "check application health", "show error rates", "profile performance",
]  # 75 commands

# Generate query variations (simulating natural language)
query_templates = [
    "how do I {cmd}", "show me {cmd}", "what is the {cmd}",
    "{cmd} please", "run {cmd}", "can you {cmd}",
    "I need to {cmd}", "help with {cmd}", "{cmd} for this system",
    "execute {cmd}", "{cmd} now", "quick {cmd}",
]

def generate_queries(n=10000, zipf_alpha=1.5):
    """Generate queries with Zipf distribution (common commands dominate)."""
    n_commands = len(commands)
    # Zipf weights
    ranks = np.arange(1, n_commands + 1)
    weights = 1.0 / ranks**zipf_alpha
    weights /= weights.sum()
    
    queries = []
    command_indices = []
    for _ in range(n):
        cmd_idx = np.random.choice(n_commands, p=weights)
        cmd = commands[cmd_idx]
        template = np.random.choice(query_templates)
        query = template.format(cmd=cmd)
        queries.append(query)
        command_indices.append(cmd_idx)
    return queries, command_indices

np.random.seed(42)
queries, true_indices = generate_queries(10000, zipf_alpha=1.5)

# Pre-compute command embeddings
cmd_embeddings = np.array([position_aware_embed(cmd) for cmd in commands])

# Simulate cache growth
print("=" * 72)
print("EXPERIMENT 10: Failure Cache Hit-Rate Scaling")
print("=" * 72)

cache_sizes = [100, 500, 1000, 2500, 5000, 7500, 10000]
thresholds = [0.7, 0.8, 0.9, 0.95]

# Use first N queries to build cache, rest to test
# (simulating temporal ordering: cache grows as system runs)
results = []

print(f"\n{'Cache Size':>10} {'Threshold':>10} {'Hit Rate':>10} {'Correct':>10} {'Latency_saved':>15}")
print("-" * 60)

for threshold in thresholds:
    for cache_size in cache_sizes:
        if cache_size >= len(queries):
            continue
        
        # Build cache from first cache_size queries
        cache_embeddings = []
        cache_labels = []
        seen = set()
        for i in range(cache_size):
            emb = position_aware_embed(queries[i])
            cache_embeddings.append(emb)
            cache_labels.append(true_indices[i])
        
        cache_embeddings = np.array(cache_embeddings)
        
        # Test on remaining queries
        hits = 0
        correct = 0
        total_tested = min(2000, len(queries) - cache_size)
        
        for i in range(cache_size, cache_size + total_tested):
            q_emb = position_aware_embed(queries[i])
            sims = cache_embeddings @ q_emb
            best_idx = np.argmax(sims)
            best_sim = sims[best_idx]
            
            if best_sim >= threshold:
                hits += 1
                if cache_labels[best_idx] == true_indices[i]:
                    correct += 1
        
        hit_rate = hits / total_tested
        precision = correct / hits if hits > 0 else 0
        
        print(f"{cache_size:>10} {threshold:>10.2f} {hit_rate:>10.1%} {precision:>10.1%} {hits * 0.5:>12.0f}s saved")
        results.append((cache_size, threshold, hit_rate, precision))

# Find optimal configuration
print("\n\n### Optimal Configurations ###\n")
best_per_threshold = {}
for cache_size, threshold, hit_rate, precision in results:
    score = hit_rate * precision  # combined metric
    if threshold not in best_per_threshold or score > best_per_threshold[threshold][2]:
        best_per_threshold[threshold] = (cache_size, hit_rate, score)

for threshold in sorted(best_per_threshold.keys()):
    cache_size, hit_rate, score = best_per_threshold[threshold]
    print(f"  threshold={threshold:.2f}: best cache={cache_size}, hit_rate={hit_rate:.1%}, score={score:.3f}")

# Verdict
print("\n\n### VERDICT ###\n")

# Find max hit rate
max_hit = max(results, key=lambda x: x[2] * x[3])
print(f"  Best hit rate: {max_hit[2]:.1%} at cache_size={max_hit[0]}, threshold={max_hit[1]}")
print(f"  Precision at best: {max_hit[3]:.1%}")

if max_hit[2] >= 0.80:
    print(f"  ✅ HYPOTHESIS CONFIRMED: Cache hit rate reaches 80%+ at {max_hit[0]} entries")
elif max_hit[2] >= 0.60:
    print(f"  ⚠️ PARTIAL: Cache hit rate reaches {max_hit[2]:.0%} but not 80%")
else:
    print(f"  ❌ HYPOTHESIS REJECTED: Cache hit rate plateaus at {max_hit[2]:.0%}")

print("\n" + "=" * 72)
