"""
scrape_2026_all.py

Runs the full 2026 OWCS update pipeline in repository-native order:
  1. Refresh regional regular-season drafts
  2. Refresh Korea playoff draft
  3. Refresh missing regional playoff drafts
  4. Rebuild merged 2026 map results
  5. Recalculate 2026 Elo outputs

This keeps the existing repository structure while making 2026 updates
repeatable from a single entry point.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

STEPS = [
    "scrape_group_stages_2026.py",
    "parse_korea_playoffs_2026.py",
    "scrape_stage1_playoffs_2026.py",
    "build_global_merge_2026.py",
    "build_owcs_2026_global_elo.py",
]


def main() -> None:
    print("=== OWCS 2026 Full Refresh ===")
    print(f"Root: {ROOT}")
    for idx, script in enumerate(STEPS, start=1):
        print(f"\n[{idx}/{len(STEPS)}] {script}")
        result = subprocess.run([sys.executable, str(ROOT / script)])
        if result.returncode != 0:
            raise SystemExit(result.returncode)
    print("\n=== 2026 refresh complete ===")


if __name__ == "__main__":
    main()
