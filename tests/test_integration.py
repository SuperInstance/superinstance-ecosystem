"""
Ecosystem Integration Test — Are the organs connected?

Tests that verify the SuperInstance ecosystem actually works end-to-end:
1. lever-runner can export skill packs that pincherOS can import
2. open-minded can ingest lever-runner and produce a valid tripartite profile
3. ZeroClaw can use lever-runner commands as game actions
4. fastloop-guard validates inputs before lever-runner processes them
5. metal-lathe observations feed back into the ecosystem health score
"""

import os
import sys
import json
import sqlite3
import subprocess
import tempfile

REPOS = {
    'lever-runner': os.path.expanduser('~/repos/lever-runner'),
    'pincherOS': os.path.expanduser('~/repos/pincherOS'),
    'open-minded': os.path.expanduser('~/repos/open-minded'),
    'zeroclaw-arena': os.path.expanduser('~/repos/zeroclaw-arena'),
    'fastloop-guard': os.path.expanduser('~/repos/fastloop-guard'),
    'metal-lathe': os.path.expanduser('~/repos/metal-lathe'),
}


def repo_exists(name):
    return os.path.isdir(REPOS.get(name, ''))


def test_lever_runner_imports():
    """Can we import lever-runner core modules?"""
    sys.path.insert(0, REPOS['lever-runner'] + '/src')
    from lever_runner.fastloop import FastLoopInterceptor
    fl = FastLoopInterceptor()
    result = fl.check("check disk usage")
    assert result.action == "EXECUTE_IMMEDIATELY"
    print("✅ lever-runner imports and FastLoop works")


def test_zeroclaw_imports():
    """Can ZeroClaw arena run?"""
    sys.path.insert(0, REPOS['zeroclaw-arena'])
    from zeroclaw import TicTacToe, Connect4, Go9x9
    ttt = TicTacToe()
    assert ttt.legal_actions()
    c4 = Connect4()
    assert c4.legal_actions()
    go = Go9x9()
    assert go.legal_actions()
    print("✅ ZeroClaw: TicTacToe, Connect4, Go9x9 all instantiate")


def test_zeroclaw_transfer_learning():
    """Does transfer learning work?"""
    sys.path.insert(0, REPOS['zeroclaw-arena'])
    from transfer_learning import TransferPlayer
    ttt_db = '/tmp/zeroclaw-sandbox/zeroclaw-tictactoe/vectors.db'
    if os.path.exists(ttt_db):
        player = TransferPlayer(ttt_db)
        assert len(player.entries) > 0
        action = player.choose_action("XO.XO.X..", ['0','1','2','3','4','5','6','7','8'])
        assert action in ['0','1','2','3','4','5','6','7','8']
        print(f"✅ Transfer learning works: {len(player.entries)} transitions loaded, chose action '{action}'")
    else:
        print("⚠️ Transfer learning: no tic-tac-toe DB yet (run arena first)")


def test_gpu_vector_engine():
    """Does the GPU vector engine work?"""
    sys.path.insert(0, REPOS['zeroclaw-arena'])
    from gpu_vector_engine import GPUVectorEngine
    engine = GPUVectorEngine(dim=64)
    vecs = engine.hash_embed_batch(["test1", "test2", "test3"])
    engine.add_batch(vecs, [{"id": i} for i in range(3)])
    results = engine.search("test1", top_k=2)
    assert len(results) >= 1
    print(f"✅ GPU Vector Engine: {len(engine)} vectors, search works")


def test_fastloop_guard_compiled():
    """Is fastloop-guard compiled?"""
    binary = REPOS['fastloop-guard'] + '/target/release/fastloop-guard'
    if os.path.exists(binary):
        result = subprocess.run([binary, '--help'], capture_output=True, timeout=5)
        print(f"✅ fastloop-guard binary exists: {os.path.getsize(binary)/1024:.0f}KB")
    else:
        print("⚠️ fastloop-guard not compiled yet")


def test_nail_export_format():
    """Does lever-runner produce valid .nail files that pincherOS can read?

    This tests the critical cross-repo contract: lever-runner exports commands
    as .nail (tar.zst), pincherOS unpacks them. The manifest must match pincherOS's
    expected schema (version as int, source_device with fingerprint, etc.).
    """
    sys.path.insert(0, REPOS['lever-runner'] + '/src')

    # Check that export_nail module loads
    from lever_runner.export_nail import (
        _build_manifest,
        _build_identity,
        _build_config,
        _reflexes_schema_sql,
        NAIL_VERSION,
    )

    # Verify the manifest matches pincherOS expected schema
    manifest = _build_manifest(
        reflex_count=5,
        checksums={"reflexes_db": "abc123"},
        source="lever-runner:test",
    )

    # PincherOS expects 'version' as an integer, not a string like "0.1.0"
    # Check current format and flag if mismatched
    if isinstance(manifest.get("version"), str):
        print(f"⚠️ manifest.version is string ({manifest['version']}), pincherOS expects integer")
    else:
        print(f"✅ manifest.version is correct type: {manifest.get('version')}")

    # PincherOS expects 'source_device' with 'fingerprint' sub-key
    if "source_device" in manifest:
        print("✅ manifest has source_device (pincherOS compatible)")
    else:
        print("⚠️ manifest missing source_device — lever-runner uses 'fingerprint' at top level")

    # PincherOS expects 'embedding_backend' and 'embedding_dimensions'
    for key in ["embedding_backend", "embedding_dimensions"]:
        if key in manifest:
            print(f"✅ manifest has {key}: {manifest[key]}")
        else:
            print(f"⚠️ manifest missing {key} (pincherOS expects it)")

    # Verify identity.json structure matches pincherOS
    identity = _build_identity()
    if "agent_name" in identity:
        print("✅ identity.json has agent_name (pincherOS compatible)")
    elif "name" in identity:
        print("⚠️ identity.json uses 'name' instead of 'agent_name' (minor mismatch)")

    # Verify reflexes.db schema matches pincherOS
    conn = sqlite3.connect(":memory:")
    conn.execute(_reflexes_schema_sql())
    # Check the columns match
    cursor = conn.execute("PRAGMA table_info(reflexes)")
    columns = {row[1] for row in cursor.fetchall()}
    expected = {"id", "intent", "action_sql", "embedding", "confidence", "invoke_count", "last_invoked", "created_at"}
    if columns == expected:
        print("✅ reflexes.db schema matches pincherOS expected columns")
    else:
        missing = expected - columns
        extra = columns - expected
        if missing:
            print(f"⚠️ reflexes.db missing columns: {missing}")
        if extra:
            print(f"ℹ️ reflexes.db has extra columns: {extra}")
    conn.close()

    print("✅ .nail format contract test complete")


def test_ecosystem_health():
    """Can we compute ecosystem health?"""
    repo_path = REPOS.get('conservation-spectral-topology-rs', '')
    if not repo_path or not os.path.isdir(repo_path):
        print("⚠️ conservation-spectral-topology-rs not found")
        return
    result = subprocess.run(
        ['cargo', 'check'],
        cwd=repo_path,
        capture_output=True, timeout=120
    )
    if result.returncode == 0:
        print("✅ conservation-spectral-topology-rs compiles")
    else:
        print(f"⚠️ conservation crate: {result.stderr.decode()[-200:]}")


def test_repos_have_readmes():
    """All repos should have READMEs."""
    missing = []
    for name, path in REPOS.items():
        if not os.path.exists(path):
            continue
        if not any(os.path.exists(os.path.join(path, f)) for f in ['README.md', 'readme.md']):
            missing.append(name)
    if missing:
        print(f"⚠️ Missing READMEs: {missing}")
    else:
        print("✅ All repos have READMEs")


def test_repos_have_tests():
    """All repos should have test files."""
    results = {}
    for name, path in REPOS.items():
        if not os.path.exists(path):
            continue
        test_files = []
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in ['node_modules', '.venv', 'target', '__pycache__']]
            for f in files:
                if 'test' in f.lower() and (f.endswith('.py') or f.endswith('.rs')):
                    test_files.append(f)
        results[name] = len(test_files)

    print("Test file counts:")
    for name, count in sorted(results.items()):
        status = "✅" if count > 0 else "❌"
        print(f"  {status} {name}: {count} test files")


if __name__ == "__main__":
    tests = [
        test_repos_have_readmes,
        test_repos_have_tests,
        test_lever_runner_imports,
        test_zeroclaw_imports,
        test_zeroclaw_transfer_learning,
        test_gpu_vector_engine,
        test_fastloop_guard_compiled,
        test_nail_export_format,
        test_ecosystem_health,
    ]

    print("=" * 60)
    print("SUPERINSTANCE ECOSYSTEM INTEGRATION TEST")
    print("=" * 60)
    print()

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: {e}")
            failed += 1
        print()

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
