"""
OWCS 2025 Global Map Results — Merge Script

Loads all 24 draft CSVs from drafts/2025/, applies corrections, normalizes
team names, removes exhibition matches, sorts chronologically, and
outputs OWCS_2025_GLOBAL_MAP_RESULTS.csv.

Usage:
    python build_global_merge_2025.py
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DRAFTS_DIR = ROOT / "drafts" / "2025"
OUTPUT_FILE = ROOT / "OWCS_2025_GLOBAL_MAP_RESULTS.csv"

# ---------------------------------------------------------------------------
# Team name normalization
# ---------------------------------------------------------------------------

# Roster/brand succession within 2025 season: old name → canonical (later) name
SUCCESSION: dict[str, str] = {
    # WAY roster journey: WAY (Stage 1) → All Gamers Global (Stage 2) → WAE (Stage 3)
    "WAY":                      "WAE",
    "All Gamers Global":        "WAE",

    # Korea: From the Gamer rebranded to ONSIDE GAMING (S1 → S2)
    "From the Gamer":           "ONSIDE GAMING",

    # Pacific: 99DIVINE rebranded to Nosebleed Esports (S2 → S3)
    "99DIVINE":                 "Nosebleed Esports",

    # Pacific: Mud Dog rebranded to Stronghold (S2 → S3)
    "Mud Dog":                  "Stronghold",

    # Japan: Inferno rebranded to VEC (S2 → S3)
    "Inferno (Japanese team)":  "VEC",

    # NOTE: Avidity (NA 2025 S1) is a separate team from EXN Zenith → Extinction chain.
    # Avidity's carry-over from Rad x Avidity (2024) is handled in build_owcs_2025_global_elo.py.
    # Extinction's carry-over from EXN Zenith (2024) is handled in build_owcs_2025_global_elo.py.
}

# Case / display normalization: variant → canonical
CASE_NORM: dict[str, str] = {
    # Korea
    "Onside Gaming":              "ONSIDE GAMING",
    "wae":                        "WAE",

    # Japan
    "Varrel":                     "VARREL",
    "vec":                        "VEC",
    "reject":                     "REJECT",
    "Reject":                     "REJECT",
    "aplomb tiger":               "Aplomb Tiger",
    "please not hero ban":        "Please Not Hero Ban",
    "Revati":                     "REVATI",
    "INSOMNIA (Japanese team)":   "Insomnia (Japanese team)",

    # Pacific
    "FURY (Australian team)":     "FURY",

    # EMEA
    "gen.g":                      "Gen.G",
    "al qadsiah":                 "Al Qadsiah",
    "twisted minds":              "Twisted Minds",
    "Virtus.Pro":                 "Virtus.pro",
    "virtus.pro":                 "Virtus.pro",   # ensure lowercase variant handled too
    "team peps":                  "Team Peps",
    "team falcons":               "Team Falcons",

    # China
    "weibo gaming":               "Weibo Gaming",
    "roc esports":                "ROC Esports",
    "milk tea":                   "Milk Tea",
    "ynb esports":                "YNB Esports",
    "zones":                      "ZONES",

    # International / disambiguation
    "99divine":                   "99DIVINE",
    "ALL Gamers Global":          "All Gamers Global",   # handled before SUCCESSION
    "Zeta Division":              "ZETA DIVISION",
    "ZETA Division":              "ZETA DIVISION",
    "FullHouse":                  "Full House",
    "Team CC (Chinese orgless team)": "Team CC",
    "TEAM CC (Chinese orgless team)": "Team CC",
    "TEAM XX":                    "Team XX",

    # Korea — group stage variants
    "From The Gamer":             "From the Gamer",   # → SUCCESSION maps to ONSIDE GAMING
    "ONSIDE Gaming":              "ONSIDE GAMING",
    "Onside Gaming":              "ONSIDE GAMING",    # lowercase-n variant found in S2 data

    # Japan — group stage variants
    "jkot":                       "JKOT",

    # Pacific — group stage variants
    "mud dog":                    "Mud Dog",
    "Mud Dog":                    "Mud Dog",

    # NA — group stage variants (all-lowercase from wikitext)
    "avidity":                    "Avidity",   # SUCCESSION then maps → Extinction
    "extinction":                 "Extinction",
    "ntmr":                       "NTMR",
    "spacestation gaming":        "Spacestation Gaming",
    "team liquid":                "Team Liquid",
    "timeless":                   "Timeless",
    "amplify":                    "Amplify",
    "dhillducks":                 "DhillDucks",
    "geekay esports":             "Geekay Esports",
    "Geekay esports":             "Geekay Esports",
    "shikigami":                  "Shikigami",
    "rad esports":                "Rad Esports",
    "quick esports":              "Quick Esports",
    "sakura esports":             "Sakura Esports",
    "the ultimates":              "The Ultimates",
    "Team peps":                  "Team Peps",

    # EMEA — group stage variants
    "gen.g esports":              "Gen.G",
    "Gen.G Esports":              "Gen.G",
    "team vision":                "Team Vision",   # EMEA Team Vision (separate from Korean Team Vision)
    "vision esports":             "Team Vision",   # same EMEA team under old name
    "Roc Esports":                "ROC Esports",

    # China — group stage variants
    "boom":                       "BOOM",
}

SPECIAL_WINNER_VALUES = {"DRAW", "[MANUAL]"}


def normalize_team(name: str) -> str:
    """Two-step normalization: CASE_NORM first, then SUCCESSION (chained)."""
    canonical = CASE_NORM.get(name, name)
    return SUCCESSION.get(canonical, canonical)


def normalize_winner(val: str) -> str:
    if val in SPECIAL_WINNER_VALUES:
        return val
    return normalize_team(val)


# ---------------------------------------------------------------------------
# Exhibition teams to exclude (all-star / friendship matches)
# ---------------------------------------------------------------------------

EXHIBITION_TEAMS_LOWER = {
    # Korea S1 exhibition
    "team black",
    "team white",
    # Champions Clash showmatch
    "team grill",
    "team eggplant (showmatch team)",
    # Midseason showmatch
    "bronze baddies",
    "diamond dawgs",
    # World Finals showmatch
    "remus",
    "romulus",
}


def is_exhibition(row: dict) -> bool:
    return (row["team_a"].lower() in EXHIBITION_TEAMS_LOWER or
            row["team_b"].lower() in EXHIBITION_TEAMS_LOWER)


# ---------------------------------------------------------------------------
# Manual patches
# ---------------------------------------------------------------------------

# Draw patches: (event_id, match_order, game_number)
DRAW_PATCHES: set[tuple[str, str, str]] = {
    # Add any confirmed draws here after review
}

# Forfeit expansions: (event_id, match_order) → (winner, loser)
FORFEIT_MATCHES: dict[tuple[str, str], tuple[str, str]] = {
    # Add any forfeits here after review
}


def apply_patches(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    for row in rows:
        eid = row["event_id"]
        mo  = row["match_order"]
        gn  = row["game_number"]

        if (eid, mo, gn) in DRAW_PATCHES:
            row["winner"] = "DRAW"
            row["loser"]  = "DRAW"
            out.append(row)
            continue

        fkey = (eid, mo)
        if fkey in FORFEIT_MATCHES and "NO_MAP_DATA" in row.get("source_note", ""):
            winner, loser = FORFEIT_MATCHES[fkey]
            base = dict(row)
            base["winner"]        = winner
            base["loser"]         = loser
            base["map_name"]      = "forfeit"
            base["map_mode"]      = "forfeit"
            base["series_format"] = "bo3"
            base["source_note"]   = "forfeit_default"
            out.append({**base, "game_number": "1"})
            out.append({**base, "game_number": "2"})
            continue

        out.append(row)
    return out


# ---------------------------------------------------------------------------
# Chronological event order (confirmed via Liquipedia)
# ---------------------------------------------------------------------------

EVENT_ORDER: list[str] = [
    # Stage 1 domestic leagues
    "owcs_2025_asia_s1_japan",      # 2025-01-27
    "owcs_2025_asia_s1_pacific",    # 2025-01-30
    "owcs_2025_asia_s1_korea",      # 2025-02-21
    "owcs_2025_na_s1",              # 2025-03-01
    "owcs_2025_emea_s1",            # 2025-03-01
    "owcs_2025_asia_s1_main",       # 2025-03-14  (Asia regional finals)
    "owcs_2025_china_s1",           # 2025-04-04
    # Phase 2: Champions Clash
    "owcs_2025_champions_clash",    # 2025-04-20
    # Stage 2 domestic leagues
    "owcs_2025_asia_s2_korea",      # 2025-05-09
    "owcs_2025_na_s2",              # 2025-05-10
    "owcs_2025_emea_s2",            # 2025-05-10
    "owcs_2025_asia_s2_japan",      # 2025-05-12
    "owcs_2025_asia_s2_pacific",    # 2025-05-15
    "owcs_2025_china_s2",           # 2025-06-27
    # Phase 3: Midseason Championship
    "owcs_2025_midseason",          # 2025-07-31
    # Stage 3 domestic leagues
    "owcs_2025_asia_s3_japan",      # 2025-08-25
    "owcs_2025_asia_s3_pacific",    # 2025-08-28
    "owcs_2025_asia_s3_korea",      # 2025-08-29
    "owcs_2025_na_s3",              # 2025-09-06
    "owcs_2025_emea_s3",            # 2025-09-06
    "owcs_2025_china_s3",           # 2025-09-06
    # Phase 4: End-of-season championships
    "owcs_2025_apac_championship",  # 2025-10-24
    "owcs_2025_korea_road_to_wf",   # 2025-10-24
    # Phase 5: World Finals
    "owcs_2025_world_finals",       # 2025-11-30
]

EVENT_ORDER_IDX: dict[str, int] = {eid: i for i, eid in enumerate(EVENT_ORDER)}

# ---------------------------------------------------------------------------
# Output columns
# ---------------------------------------------------------------------------

OUTPUT_COLUMNS: list[str] = [
    "global_map_order",
    "event_id", "event_region", "season_year", "stage_label",
    "week_label", "day_label", "match_date", "match_order", "game_number",
    "team_a", "team_b", "winner", "loser",
    "map_name", "map_mode", "series_format",
    "source_url", "source_note",
]

# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def load_all_drafts() -> list[dict]:
    rows: list[dict] = []
    for f in sorted(DRAFTS_DIR.glob("*.csv")):
        file_rows = list(csv.DictReader(f.open(encoding="utf-8")))
        rows.extend(file_rows)
    return rows


def normalize_all(rows: list[dict]) -> list[dict]:
    for row in rows:
        row["team_a"] = normalize_team(row["team_a"])
        row["team_b"] = normalize_team(row["team_b"])
        row["winner"] = normalize_winner(row["winner"])
        row["loser"]  = normalize_winner(row["loser"])
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
        return (event_idx, mo, gn)

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


# ---------------------------------------------------------------------------
# Summary / verification
# ---------------------------------------------------------------------------

def print_summary(rows: list[dict]) -> None:
    total    = len(rows)
    manual   = sum(1 for r in rows if "[MANUAL]" in str(list(r.values())))
    draws    = sum(1 for r in rows if r.get("winner") == "DRAW")
    forfeits = sum(1 for r in rows if r.get("source_note") == "forfeit_default")

    events_seen = {r["event_id"] for r in rows}
    missing_events = [e for e in EVENT_ORDER if e not in events_seen]
    unknown_events = sorted(events_seen - set(EVENT_ORDER))

    all_teams = sorted({r["team_a"] for r in rows} | {r["team_b"] for r in rows})

    # Suspect names: fully lowercase AND not a known special case
    known_lowercase: set[str] = {"jkot"}  # intentional all-lowercase team names
    suspect = [
        t for t in all_teams
        if (t == t.lower() and t not in known_lowercase)
        or ("[MANUAL]" in t)
    ]

    print("\n=== Build Global Merge 2025: Summary ===")
    print(f"  Total rows       : {total}")
    print(f"  [MANUAL] rows    : {manual}  {'← needs attention' if manual else '✓'}")
    print(f"  Draw maps        : {draws}")
    print(f"  Forfeit maps     : {forfeits}")
    print(f"  Events found     : {len(events_seen)} / {len(EVENT_ORDER)}")
    if missing_events:
        print(f"  MISSING events   : {missing_events}")
    if unknown_events:
        print(f"  Unknown events   : {unknown_events}")
    print(f"  Unique teams     : {len(all_teams)}")
    if suspect:
        print(f"  Suspect names    : {suspect}")
    else:
        print(f"  Suspect names    : none ✓")

    print("\n  Rows per event:")
    for eid in EVENT_ORDER:
        count = sum(1 for r in rows if r["event_id"] == eid)
        print(f"    {eid:<48} {count:>4}")

    print(f"\n  Output: {OUTPUT_FILE}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print("=== Build Global Merge 2025 ===")

    print("\n[1] Loading drafts from drafts/2025/ ...")
    rows = load_all_drafts()
    n_files = len(list(DRAFTS_DIR.glob("*.csv")))
    print(f"    {len(rows)} rows from {n_files} files")

    print("\n[2] Applying patches (draws + forfeits)...")
    rows = apply_patches(rows)
    print(f"    {len(rows)} rows after patches")

    print("\n[3] Filtering exhibition matches...")
    before = len(rows)
    rows = [r for r in rows if not is_exhibition(r)]
    print(f"    Removed {before - len(rows)} exhibition rows → {len(rows)} rows")

    print("\n[4] Normalizing team names...")
    rows = normalize_all(rows)
    print(f"    Done")

    print("\n[5] Sorting chronologically...")
    rows = sort_rows(rows)
    rows = assign_order(rows)
    print(f"    Done")

    print("\n[6] Writing output...")
    write_output(rows)
    print(f"    Written to {OUTPUT_FILE}")

    print_summary(rows)


if __name__ == "__main__":
    main()
