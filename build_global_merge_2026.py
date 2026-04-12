"""
OWCS 2026 Stage 1 Global Map Results — Merge Script

Loads 2026 Stage 1 draft CSVs from drafts/2026/, applies basic normalization,
filters China Swiss-stage rows, sorts chronologically, and outputs
OWCS_2026_GLOBAL_MAP_RESULTS.csv.

This intentionally creates new 2026 artifacts and does not overwrite
the 2024/2025 outputs.
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DRAFTS_DIR = ROOT / "drafts" / "2026"
OUTPUT_FILE = ROOT / "OWCS_2026_GLOBAL_MAP_RESULTS.csv"

SUCCESSION: dict[str, str] = {
    # Fill in confirmed 2025 -> 2026 rebrands here as they are verified.
}

CASE_NORM: dict[str, str] = {
    # Japan
    "Varrel": "VARREL",
    "please not hero ban": "Please Not Hero Ban",
    # Cross-year carry-over case / spacing fixes
    "FullHouse": "Full House",
    "team liquid": "Team Liquid",
    "team peps": "Team Peps",
    "fury": "FURY",
    "lunex gaming": "LuneX Gaming",
    "mmy": "MMY",
    "quasar esports": "Quasar Esports",
    "rankers": "Rankers",
    # Korea
    "ZETA Division": "ZETA DIVISION",
    "ONSIDE Gaming": "ONSIDE GAMING",
    "ONSIDE Gaming.": "ONSIDE GAMING",
    # NA
    "dallas fuel": "Dallas Fuel",
    "spacestation gaming": "Spacestation Gaming",
    # EMEA
    "geekay esports": "Geekay Esports",
    "al qadsiah": "Al Qadsiah",
    # Common style fixes
    "Team peps": "Team Peps",
    "twisted minds": "Twisted Minds",
    "virtus.pro": "Virtus.pro",
}

SPECIAL_WINNER_VALUES = {"DRAW", "[MANUAL]"}
CHINA_ROUND_ROBIN_START = "2026-04-04"


def normalize_team(name: str) -> str:
    canonical = CASE_NORM.get(name, name)
    return SUCCESSION.get(canonical, canonical)


def normalize_winner(val: str) -> str:
    if val in SPECIAL_WINNER_VALUES:
        return val
    return normalize_team(val)


def is_china_swiss(row: dict) -> bool:
    return row["event_id"] == "owcs_2026_china_s1" and row["match_date"] < CHINA_ROUND_ROBIN_START


EVENT_ORDER: list[str] = [
    "owcs_2026_asia_s1_japan",
    "owcs_2026_asia_s1_korea",
    "owcs_2026_asia_s1_pacific",
    "owcs_2026_china_s1",
    "owcs_2026_emea_s1",
    "owcs_2026_na_s1",
]

EVENT_ORDER_IDX: dict[str, int] = {eid: i for i, eid in enumerate(EVENT_ORDER)}

OUTPUT_COLUMNS: list[str] = [
    "global_map_order",
    "event_id",
    "event_region",
    "season_year",
    "stage_label",
    "week_label",
    "day_label",
    "match_date",
    "match_order",
    "game_number",
    "team_a",
    "team_b",
    "winner",
    "loser",
    "map_name",
    "map_mode",
    "series_format",
    "source_url",
    "source_note",
]


def load_all_drafts() -> list[dict]:
    rows: list[dict] = []
    for f in sorted(DRAFTS_DIR.glob("*.csv")):
        rows.extend(list(csv.DictReader(f.open(encoding="utf-8"))))
    return rows


def normalize_all(rows: list[dict]) -> list[dict]:
    for row in rows:
        row["team_a"] = normalize_team(row["team_a"])
        row["team_b"] = normalize_team(row["team_b"])
        row["winner"] = normalize_winner(row["winner"])
        row["loser"] = normalize_winner(row["loser"])
    return rows


def sort_rows(rows: list[dict]) -> list[dict]:
    def key(r: dict) -> tuple:
        event_idx = EVENT_ORDER_IDX.get(r["event_id"], 999)
        try:
            mo = int(r["match_order"])
        except (ValueError, TypeError):
            mo = 9999
        try:
            gn = int(r["game_number"])
        except (ValueError, TypeError):
            gn = 9999
        return (event_idx, r.get("match_date", ""), mo, gn)

    return sorted(rows, key=key)


def assign_order(rows: list[dict]) -> list[dict]:
    for i, row in enumerate(rows, start=1):
        row["global_map_order"] = str(i)
    return rows


def write_output(rows: list[dict]) -> None:
    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def print_summary(rows: list[dict]) -> None:
    events_seen = {r["event_id"] for r in rows}
    print("\n=== Build Global Merge 2026: Summary ===")
    print(f"  Total rows   : {len(rows)}")
    print(f"  Events found : {len(events_seen)} / {len(EVENT_ORDER)}")
    print(f"  Unique teams : {len(sorted({r['team_a'] for r in rows} | {r['team_b'] for r in rows}))}")
    print("\n  Rows per event:")
    for eid in EVENT_ORDER:
        count = sum(1 for r in rows if r["event_id"] == eid)
        print(f"    {eid:<32} {count:>4}")
    print(f"\n  Output: {OUTPUT_FILE}")


def main() -> None:
    print("=== Build Global Merge 2026 ===")

    print("\n[1] Loading drafts from drafts/2026/ ...")
    rows = load_all_drafts()
    print(f"    {len(rows)} rows from {len(list(DRAFTS_DIR.glob('*.csv')))} files")

    print("\n[2] Filtering China Swiss-stage rows ...")
    before = len(rows)
    rows = [r for r in rows if not is_china_swiss(r)]
    print(f"    Removed {before - len(rows)} rows")

    print("\n[3] Normalizing team names ...")
    rows = normalize_all(rows)
    print("    Done")

    print("\n[4] Sorting chronologically ...")
    rows = sort_rows(rows)
    rows = assign_order(rows)
    print("    Done")

    print("\n[5] Writing output ...")
    write_output(rows)
    print(f"    Written to {OUTPUT_FILE}")

    print_summary(rows)


if __name__ == "__main__":
    main()
