#!/bin/bash
# SuperInstance Ecosystem Health Check
# Runs tests across all repos and produces a unified report.

set -e

ECOSYSTEM_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPOS=("lever-runner" "pincherOS" "zeroclaw-arena" "fastloop-guard" 
       "conservation-spectral-topology-rs" "metal-lathe" "agent-template")
REPORT="$ECOSYSTEM_ROOT/health-report.json"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "=== SuperInstance Ecosystem Health Check ==="
echo "Time: $TIMESTAMP"
echo ""

TOTAL_TESTS=0
TOTAL_PASSED=0
TOTAL_FAILED=0
RESULTS=""

for REPO in "${REPOS[@]}"; do
    REPO_PATH="$HOME/repos/$REPO"
    if [ ! -d "$REPO_PATH" ]; then
        echo "⚠️  $REPO: not found"
        continue
    fi
    
    echo "--- $REPO ---"
    cd "$REPO_PATH"
    
    # Detect test runner
    if [ -f "Cargo.toml" ]; then
        # Rust project
        OUTPUT=$(cargo test 2>&1) || true
        PASSED=$(echo "$OUTPUT" | grep -oP '\d+ passed' | head -1 | grep -oP '\d+' || echo "0")
        FAILED=$(echo "$OUTPUT" | grep -oP '\d+ failed' | head -1 | grep -oP '\d+' || echo "0")
        WARNINGS=$(echo "$OUTPUT" | grep -c "warning" || echo "0")
        echo "  Rust: $PASSED passed, $FAILED failed, $WARNINGS warnings"
    elif [ -f "pyproject.toml" ] || [ -f "setup.py" ] || [ -f "src/__init__.py" ]; then
        # Python project
        if [ -d ".venv" ]; then
            source .venv/bin/activate
        fi
        OUTPUT=$(python3 -m pytest tests/ -q --tb=no 2>&1) || true
        PASSED=$(echo "$OUTPUT" | grep -oP '\d+ passed' | head -1 | grep -oP '\d+' || echo "0")
        FAILED=$(echo "$OUTPUT" | grep -oP '\d+ failed' | head -1 | grep -oP '\d+' || echo "0")
        echo "  Python: $PASSED passed, $FAILED failed"
    else
        echo "  Unknown project type"
        PASSED=0
        FAILED=0
    fi
    
    TOTAL_TESTS=$((TOTAL_TESTS + PASSED + FAILED))
    TOTAL_PASSED=$((TOTAL_PASSED + PASSED))
    TOTAL_FAILED=$((TOTAL_FAILED + FAILED))
    
    RESULTS="$RESULTS{\"repo\":\"$REPO\",\"passed\":$PASSED,\"failed\":$FAILED},"
done

# Generate JSON report
cat > "$REPORT" << EOF
{
  "timestamp": "$TIMESTAMP",
  "total_tests": $TOTAL_TESTS,
  "total_passed": $TOTAL_PASSED,
  "total_failed": $TOTAL_FAILED,
  "health_score": $(python3 -c "print(round($TOTAL_PASSED / max($TOTAL_TESTS, 1), 2))"),
  "repos": [${RESULTS%,}]
}
EOF

echo ""
echo "=== Summary ==="
echo "Total: $TOTAL_PASSED passed / $TOTAL_TESTS tests"
echo "Health: $(python3 -c "print(round($TOTAL_PASSED / max($TOTAL_TESTS, 1) * 100, 1))")%"
echo "Report: $REPORT"
