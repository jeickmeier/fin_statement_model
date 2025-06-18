#!/usr/bin/env python3
"""Detect duplicate metric definitions in YAML files.

This helper is intended for CI/pre-commit.  It walks the metric_defn directory
and flags two kinds of duplication problems:

1. *Duplicate names*: two or more metric YAML entries share the same ``name`` –
   most likely a copy-paste error.
2. *Duplicate formulas*: two metric definitions have the exact same ``formula``
   string but *different* names (near-duplicate).  This often indicates the
   metric should be defined once and referenced elsewhere.

If any duplicates are found the script exits with a non-zero status code and
prints a human-readable report.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path
from typing import List, Tuple

import yaml

METRIC_ROOT = (
    Path(__file__).resolve().parents[1]
    / "fin_statement_model"
    / "core"
    / "metrics"
    / "metric_defn"
)

if not METRIC_ROOT.exists():
    print(f"Metric definition directory not found: {METRIC_ROOT}", file=sys.stderr)
    sys.exit(1)

# Gather all YAML files under metric_defn.
files: List[Path] = sorted(METRIC_ROOT.rglob("*.yaml"))
if not files:
    print("No YAML files found under metric_defn – nothing to check.")
    sys.exit(0)

name_to_locations: defaultdict[str, List[Tuple[Path, int]]] = defaultdict(list)
formula_to_entries: defaultdict[str, List[Tuple[str, Path, int]]] = defaultdict(list)


def process_file(path: Path) -> None:
    with path.open("r", encoding="utf-8") as f:
        try:
            docs = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"YAML parse error in {path}: {e}", file=sys.stderr)
            return

    if not isinstance(docs, list):
        return

    for idx, entry in enumerate(docs, start=1):
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        formula = entry.get("formula")
        if name:
            name_to_locations[name].append((path, idx))
        if formula and name:
            formula_to_entries[formula].append((name, path, idx))


for fp in files:
    process_file(fp)

# --- Report duplicates -------------------------------------------------------
problems = []

for name, locs in name_to_locations.items():
    if len(locs) > 1:
        problems.append(f"Duplicate metric name '{name}' defined in:")
        problems.extend([f"  • {p}:{line}" for p, line in locs])
        problems.append("")

for formula, entries in formula_to_entries.items():
    if len(entries) > 1:
        # Only flag if names differ; identical names already reported above.
        names = {n for n, _, _ in entries}
        if len(names) > 1:
            problems.append("Identical formula defined under multiple names:")
            problems.append(f"  Formula: {formula}")
            problems.extend([f"  • {n} — {p}:{line}" for n, p, line in entries])
            problems.append("")

if problems:
    print("\n".join(problems), file=sys.stderr)
    sys.exit(1)

print("✔ No duplicate metric definitions found.")
