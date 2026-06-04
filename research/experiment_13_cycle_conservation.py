#!/usr/bin/env python3
"""
Experiment 13: Cycle Conservation Across Code Evolution
Tests whether cycle metrics are more stable than edge/node counts across commits.
"""
import json
import numpy as np
from pathlib import Path

data = json.loads(Path(Path.home() / "repos/conservation-spectral-topology-rs/experiments/cycle_conservation_results.json").read_text())

timeline = data["timeline"]

# Group by repo (each repo has sequential commits)
# lever-runner: first 4 entries, zeroclaw-arena: next 4
repos_commits = {
    "lever-runner": timeline[0:4],   # HEAD, cec100a, 151803e, c666abb
    "zeroclaw-arena": timeline[4:8], # HEAD, f3d5293, 5ba0736, 482df51
}

metrics = ["n_functions", "total_edges", "self_calls", "mutual_pairs", "cycle_density", "hub_count", "edge_density"]

print("=" * 72)
print("EXPERIMENT 13: Cycle Conservation Across Code Evolution")
print("=" * 72)

for repo_name, commits in repos_commits.items():
    print(f"\n### {repo_name} ({len(commits)} commits) ###\n")
    print(f"{'Metric':<20} {'CV':>8} {'Range':>15} {'Stability':>10}")
    print("-" * 60)
    
    for metric in metrics:
        values = [c[metric] for c in commits]
        mean = np.mean(values)
        std = np.std(values)
        cv = std / mean if mean > 0 else 0
        
        # Stability: 1 - CV (higher = more conserved)
        stability = 1 - min(cv, 1)
        
        status = "✅ CONSERVED" if cv < 0.1 else ("⚠️ moderate" if cv < 0.3 else "❌ variable")
        print(f"  {metric:<18} {cv:>8.3f} {min(values):>7.1f}-{max(values):<7.1f} {stability:>10.3f}  {status}")

# Compute deltas between consecutive commits
print("\n\n### Consecutive Commit Deltas ###\n")

for repo_name, commits in repos_commits.items():
    print(f"\n{repo_name}:")
    for metric in metrics:
        deltas = []
        for i in range(1, len(commits)):
            prev = commits[i-1][metric]
            curr = commits[i][metric]
            if prev > 0:
                delta = abs(curr - prev) / prev
                deltas.append(delta)
        avg_delta = np.mean(deltas) if deltas else 0
        print(f"  {metric:<18} avg delta: {avg_delta:.3f}")

# Verdict
print("\n\n### VERDICT ###\n")

cycle_metrics = ["self_calls", "mutual_pairs", "cycle_density"]
structure_metrics = ["n_functions", "total_edges", "hub_count", "edge_density"]

for repo_name, commits in repos_commits.items():
    cycle_cvs = []
    struct_cvs = []
    for metric in cycle_metrics:
        values = [c[metric] for c in commits]
        mean = np.mean(values)
        cv = np.std(values) / mean if mean > 0 else 0
        cycle_cvs.append(cv)
    for metric in structure_metrics:
        values = [c[metric] for c in commits]
        mean = np.mean(values)
        cv = np.std(values) / mean if mean > 0 else 0
        struct_cvs.append(cv)
    
    avg_cycle_cv = np.mean(cycle_cvs)
    avg_struct_cv = np.mean(struct_cvs)
    
    if avg_cycle_cv < avg_struct_cv:
        print(f"  {repo_name}: ✅ Cycle metrics MORE STABLE (CV={avg_cycle_cv:.3f} vs {avg_struct_cv:.3f})")
    else:
        print(f"  {repo_name}: ❌ Cycle metrics LESS STABLE (CV={avg_cycle_cv:.3f} vs {avg_struct_cv:.3f})")

print("\n" + "=" * 72)
