#!/bin/bash
# Quick check: uncommitted changes, unpushed commits
for repo in ~/repos/lever-runner ~/repos/pincherOS ~/repos/zeroclaw-arena ~/repos/fastloop-guard ~/repos/open-minded ~/repos/metal-lathe ~/repos/conservation-spectral-topology-rs ~/repos/superinstance-ecosystem ~/repos/agent-template ~/repos/captains-log; do
    if [ -d "$repo" ]; then
        cd "$repo"
        name=$(basename "$repo")
        dirty=$(git status --porcelain | wc -l)
        unpushed=$(git log @{u}..HEAD --oneline 2>/dev/null | wc -l)
        if [ "$dirty" -gt 0 ] || [ "$unpushed" -gt 0 ]; then
            echo "⚠️  $name: $dirty dirty, $unpushed unpushed"
        else
            echo "✅ $name: clean"
        fi
    fi
done
