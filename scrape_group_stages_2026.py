"""
scrape_group_stages_2026.py

Collect OWCS 2026 Stage 1 Regular Season results into drafts/2026/.
This mirrors the existing group-stage scraper flow but keeps 2026 isolated
from the 2024/2025 files.

Scope for now:
  - Japan / Korea / Pacific / China / EMEA / NA
  - Regular Season only
  - Korea & Pacific: collect only currently posted matches
  - China: keep Round Robin stage only, exclude Swiss stage

Usage:
    python scrape_group_stages_2026.py
"""

from __future__ import annotations

import csv
from pathlib import Path

from scrape_group_stages import (
    FIELDNAMES,
    fetch_raw,
    matches_to_rows,
    parse_matches_from_wikitext,
)

ROOT = Path(__file__).resolve().parent
DRAFTS_2026 = ROOT / "drafts" / "2026"
DRAFTS_2026.mkdir(parents=True, exist_ok=True)

EVENTS_2026 = [
    (
        "owcs_2026_asia_s1_japan",
        DRAFTS_2026 / "owcs_2026_asia_s1_japan.csv",
        "Overwatch_Champions_Series/2026/Asia/Stage_1/Japan/Regular_Season",
        "japan",
        "Stage 1",
        2026,
    ),
    (
        "owcs_2026_asia_s1_korea",
        DRAFTS_2026 / "owcs_2026_asia_s1_korea.csv",
        "Overwatch_Champions_Series/2026/Asia/Stage_1/Korea/Regular_Season",
        "korea",
        "Stage 1",
        2026,
    ),
    (
        "owcs_2026_asia_s1_pacific",
        DRAFTS_2026 / "owcs_2026_asia_s1_pacific.csv",
        "Overwatch_Champions_Series/2026/Asia/Stage_1/Pacific/Regular_Season",
        "pacific",
        "Stage 1",
        2026,
    ),
    (
        "owcs_2026_china_s1",
        DRAFTS_2026 / "owcs_2026_china_s1.csv",
        "Overwatch_Champions_Series/2026/China/Stage_1/Regular_Season",
        "china",
        "Stage 1",
        2026,
    ),
    (
        "owcs_2026_emea_s1",
        DRAFTS_2026 / "owcs_2026_emea_s1.csv",
        "Overwatch_Champions_Series/2026/EMEA/Stage_1/Regular_Season",
        "emea",
        "Stage 1",
        2026,
    ),
    (
        "owcs_2026_na_s1",
        DRAFTS_2026 / "owcs_2026_na_s1.csv",
        "Overwatch_Champions_Series/2026/NA/Stage_1/Regular_Season",
        "na",
        "Stage 1",
        2026,
    ),
]

# China Stage 1 includes Swiss first, then Round Robin.
# We only keep rows dated on/after the Round Robin start.
CHINA_ROUND_ROBIN_START = "2026-04-04"


def filter_matches(event_id: str, matches: list[dict]) -> list[dict]:
    if event_id != "owcs_2026_china_s1":
        return matches
    return [m for m in matches if m.get("match_date", "") >= CHINA_ROUND_ROBIN_START]


def write_csv(csv_path: Path, rows: list[dict]) -> None:
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def process_event(event_id, csv_path, wiki_title, region, stage_label, season):
    print(f"\n{'=' * 60}")
    print(f"[2026] {event_id}")
    print("  Fetching... ", end="", flush=True)
    wikitext = fetch_raw(wiki_title)
    if not wikitext:
        print("EMPTY/404 - skipping")
        return

    matches = parse_matches_from_wikitext(wikitext)
    print(f"{len(matches)} matches parsed")
    matches = filter_matches(event_id, matches)
    print(f"  {len(matches)} matches kept after 2026 filters")

    if not matches:
        print("  No matches kept - skipping CSV write")
        return

    rows = matches_to_rows(
        matches,
        event_id,
        region,
        season,
        stage_label,
        f"https://liquipedia.net/overwatch/index.php?title={wiki_title}",
    )
    write_csv(csv_path, rows)
    print(f"  -> {len(rows)} map rows written to {csv_path.name}")


if __name__ == "__main__":
    print("=== 2026 Stage 1 Regular Season Scraper ===")
    print(f"Events: {len(EVENTS_2026)}")
    print(f"Output: {DRAFTS_2026}")
    for args in EVENTS_2026:
        process_event(*args)
    print("\n=== Done ===")
