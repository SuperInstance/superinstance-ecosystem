#!/usr/bin/env python3
"""
Demo: Convert existing ad-hoc bottles to the new .bottle protocol format.

Scans captains-log/i2i/ for existing markdown/flat bottles and converts them
to structured YAML .bottle files.

Usage:
    python scripts/demo_bottle_conversion.py [--dry-run]
"""

import os
import sys
import glob
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bottle_protocol import Bottle, observe, hypothesize, API_VERSION


def convert_markdown_bottle(path: str) -> Bottle:
    """Convert an existing markdown bottle file to a structured Bottle.

    Tries to extract metadata from the markdown content and wraps it
    as an observation bottle with the original content in the payload.
    """
    with open(path) as f:
        content = f.read()

    # Try to extract source from filename or content
    basename = os.path.basename(path)
    parts = basename.replace(".md", "").split("-")

    # Heuristic: look for known agent names in filename
    source = "unknown"
    known_agents = ["forgemaster", "oracle2", "metal-lathe", "lever-runner", "zeroclaw"]
    for agent in known_agents:
        if agent in basename.lower():
            source = agent
            break

    # Try to extract kind from content
    kind = "observation"
    content_lower = content.lower()
    if "hypothesis" in content_lower or "hypothesize" in content_lower:
        kind = "hypothesis"
    elif "experiment" in content_lower:
        kind = "experiment"
    elif "result" in content_lower:
        kind = "result"
    elif "config" in content_lower or "proposal" in content_lower:
        kind = "config"

    return Bottle(
        kind=kind,
        source=source,
        payload={
            "original_file": basename,
            "content_preview": content[:500],
            "converted_from": "markdown",
        },
        confidence=0.5,
        tags=["converted", "legacy"],
    )


def convert_text_bottle(path: str) -> Bottle:
    """Convert a generic text file to a Bottle."""
    basename = os.path.basename(path)
    with open(path) as f:
        content = f.read()
    return observe(
        source="unknown",
        what=f"converted from {basename}",
        data={"content_preview": content[:500], "converted_from": "text"},
        tags=["converted", "legacy"],
    )


def main():
    parser = argparse.ArgumentParser(description="Convert legacy bottles to .bottle protocol")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without writing")
    parser.add_argument("--source-dir", default="captains-log/i2i", help="Directory with legacy bottles")
    parser.add_argument("--output-dir", default="captains-log/i2i/v2", help="Output directory for converted bottles")
    args = parser.parse_args()

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    source_dir = os.path.join(repo_root, args.source_dir)
    output_dir = os.path.join(repo_root, args.output_dir)

    if not os.path.exists(source_dir):
        print(f"No source directory found at {source_dir}")
        print("Creating demo bottles instead...")
        # Create demo bottles to showcase the protocol
        demo_dir = output_dir if not args.dry_run else None
        demos = [
            observe(
                "forgemaster",
                "spectral similarity between repos is >0.97",
                {"cosine_sim": 0.97, "repos_compared": 3},
                confidence=0.94,
                tags=["observation", "spectral", "cross-repo"],
            ),
            hypothesize(
                "forgemaster",
                "position-aware embeddings will outperform pure hash for command matching",
                evidence=["44% top-1 vs 0% in initial benchmark"],
                confidence=0.7,
            ),
            observe(
                "metal-lathe",
                "cache hit rate at 44% after one week",
                {"hit_rate": 0.44, "commands_seen": 1000},
                confidence=0.9,
                tags=["observation", "cache", "metrics"],
            ),
        ]
        for b in demos:
            print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Bottle: {b.kind} from {b.source}")
            print(b.to_yaml())
            if demo_dir:
                path = b.save(demo_dir)
                print(f"  → saved to {path}")
        return

    # Process existing files
    patterns = ["*.md", "*.txt", "*.yaml", "*.yml"]
    files = []
    for pattern in patterns:
        files.extend(glob.glob(os.path.join(source_dir, pattern)))

    if not files:
        print(f"No files found in {source_dir}")
        return

    print(f"Found {len(files)} files to convert in {source_dir}")
    converted = 0
    for fpath in files:
        basename = os.path.basename(fpath)
        # Skip already-converted bottles
        if basename.startswith("BOTTLE-"):
            print(f"  SKIP (already converted): {basename}")
            continue

        try:
            if fpath.endswith(".md"):
                bottle = convert_markdown_bottle(fpath)
            elif fpath.endswith((".yaml", ".yml")):
                # Try to load as existing bottle first
                try:
                    bottle = Bottle.from_file(fpath)
                    print(f"  SKIP (valid bottle): {basename}")
                    continue
                except Exception:
                    bottle = convert_text_bottle(fpath)
            else:
                bottle = convert_text_bottle(fpath)

            print(f"\n  CONVERT: {basename} → {bottle.kind} from {bottle.source}")
            if args.dry_run:
                print(bottle.to_yaml()[:200] + "...")
            else:
                path = bottle.save(output_dir)
                print(f"    → saved to {path}")
            converted += 1
        except Exception as e:
            print(f"  ERROR converting {basename}: {e}")

    print(f"\n{'Would convert' if args.dry_run else 'Converted'}: {converted}/{len(files)} files")
    if not args.dry_run and converted > 0:
        print(f"Output directory: {output_dir}")


if __name__ == "__main__":
    main()
