"""
OWCS 2024 Global Map Results — Merge Script

Loads all 35 draft CSVs from drafts/, applies corrections, normalizes
team names, removes exhibition matches, sorts chronologically, and
outputs OWCS_2024_GLOBAL_MAP_RESULTS.csv.

Usage:
    python build_global_merge.py
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DRAFTS_DIR = ROOT / "drafts"
OUTPUT_FILE = ROOT / "OWCS_2024_GLOBAL_MAP_RESULTS.csv"

# ---------------------------------------------------------------------------
# Team name normalization
# ---------------------------------------------------------------------------

# Roster succession: old name → canonical (current) name
SUCCESSION: dict[str, str] = {
    "WAC":            "Crazy Raccoon",
    "From The Gamer": "ZETA DIVISION",
    "From the Gamer": "ZETA DIVISION",
    "FTG":            "ZETA DIVISION",
}

# Case / display normalization: variant → canonical
CASE_NORM: dict[str, str] = {
    # Korea
    "genesis":              "Genesis",
    "sin prisa gaming":     "Sin Prisa Gaming",
    "YETI (Korean team)":   "YETI",

    # Japan
    "Varrel":                     "VARREL",
    "INSOMNIA (Japanese team)":   "Insomnia (Japanese team)",
    "REVATI x NTMR":              "REVATI X NTMR",

    # NA — Stage 1 groups uses all-lowercase team names
    "timeless":                   "Timeless",
    "toronto defiant":            "Toronto Defiant",
    "tsm":                        "TSM",
    "vice (north american team)": "Vice (North American team)",
    "daybreak":                   "Daybreak",
    "final gambit":               "Final Gambit",
    "shikigami hikari":           "Shikigami",   # Stage 1 Groups name → Shikigami (Main+)
    "students of the game":       "Students of the Game",
    "students of the Game":       "Students of the Game",
    "beluga's platoon":           "Beluga's Platoon",
    "Who Is Goldfish":            "Who is Goldfish",
    "FLUFFY AIMERS":              "Fluffy Aimers",
    "Tanuki Tapire":              "Tanuki Esports",  # Stage 4 rename of Tanuki Esports

    # EMEA
    "ence":           "ENCE",
    "Ence":           "ENCE",
    "virtus.pro":     "Virtus.pro",
    "Virtus.Pro":     "Virtus.pro",
    "twisted minds":  "Twisted Minds",
    "ssg":            "Spacestation Gaming",  # EMEA Stage 3 abbreviation
    "SSG":            "Spacestation Gaming",
    "roc esports":    "ROC Esports",
    "Nu.age":         "nu.age",               # nu.age is the official lowercase form

    # International / disambiguation
    "321 diving":     "321 Diving",
}

TEAM_ALIAS_MAP: dict[str, str] = {**SUCCESSION, **CASE_NORM}

SPECIAL_WINNER_VALUES = {"DRAW", "[MANUAL]"}


def normalize_team(name: str) -> str:
    return TEAM_ALIAS_MAP.get(name, name)


def normalize_winner(val: str) -> str:
    if val in SPECIAL_WINNER_VALUES:
        return val
    return normalize_team(val)


# ---------------------------------------------------------------------------
# Exhibition teams to exclude (all-star / friendship matches)
# ---------------------------------------------------------------------------

EXHIBITION_TEAMS_LOWER = {
    "team hydron",       # Dallas Major all-star
    "team danteh",       # Dallas Major all-star
    "team jake",         # World Finals all-star
    "team reinforce",    # World Finals all-star
    "team japan (owcs)", # Asia S1 Main friendship
    "team pacific",      # Asia S1 Main friendship
}


def is_exhibition(row: dict) -> bool:
    return (row["team_a"].lower() in EXHIBITION_TEAMS_LOWER or
            row["team_b"].lower() in EXHIBITION_TEAMS_LOWER)


# ---------------------------------------------------------------------------
# Manual patches
# ---------------------------------------------------------------------------

# Draw patches: rows where winner/loser should be set to "DRAW"
# Key: (event_id, match_order, game_number)
DRAW_PATCHES: set[tuple[str, str, str]] = {
    ("owcs_2024_asia_s2_main", "6", "4"),  # CR vs ZETA DIVISION — map 4 drew
    ("owcs_2024_dallas_major", "2", "3"),  # Team Falcons vs ENCE — map 3 drew
}

# Forfeit expansions: (event_id, match_order) → (winner, loser)
# Each forfeit placeholder row is replaced with 2 virtual maps (2:0 default)
FORFEIT_MATCHES: dict[tuple[str, str], tuple[str, str]] = {
    ("faceit_2024_s2_emea_master", "1"):  ("ENCE",              "Supershy"),
    ("faceit_2024_s2_emea_master", "8"):  ("Ex Oblivione",      "Supershy"),
    ("faceit_2024_s2_emea_master", "11"): ("Washington Hospice", "A One Man Army"),
}


def apply_patches(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    for row in rows:
        eid = row["event_id"]
        mo  = row["match_order"]
        gn  = row["game_number"]

        # Draw patches
        if (eid, mo, gn) in DRAW_PATCHES:
            row["winner"] = "DRAW"
            row["loser"]  = "DRAW"
            out.append(row)
            continue

        # Forfeit placeholders → expand to 2 virtual maps
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
# Chronological event order (determined from actual match_date values)
# ---------------------------------------------------------------------------

EVENT_ORDER: list[str] = [
    "owcs_2024_asia_s1_pacific",   # 2024-02-29
    "owcs_2024_na_s1_groups",      # 2024-03-08
    "owcs_2024_emea_s1_groups",    # 2024-03-08
    "owcs_2024_na_s1_main",        # 2024-03-21
    "owcs_2024_emea_s1_main",      # 2024-03-21
    "owcs_2024_asia_s1_japan",     # 2024-03-24
    "owcs_2024_asia_s1_korea",     # 2024-03-28
    "owcs_2024_asia_s1_wildcard",  # 2024-04-08
    "owcs_2024_na_s2_groups",      # 2024-04-12
    "owcs_2024_emea_s2_groups",    # 2024-04-12
    "owcs_2024_asia_s1_main",      # 2024-04-25
    "owcs_2024_na_s2_main",        # 2024-04-25
    "owcs_2024_emea_s2_main",      # 2024-04-25
    "owcs_2024_dallas_major",      # 2024-05-31
    "faceit_2024_s1_na_master",    # 2024-06-14
    "faceit_2024_s1_emea_master",  # 2024-06-14
    "ewc_2024",                    # 2024-07-26
    "owcs_2024_asia_s2_pacific",   # 2024-08-08
    "owcs_2024_na_s3_groups",      # 2024-08-16
    "owcs_2024_emea_s3_groups",    # 2024-08-16
    "owcs_2024_na_s3_main",        # 2024-08-29
    "owcs_2024_emea_s3_main",      # 2024-08-29
    "owcs_2024_asia_s2_korea",     # 2024-08-30
    "owcs_2024_asia_s2_japan",     # 2024-09-02
    "faceit_2024_s2_na_master",    # 2024-09-13
    "faceit_2024_s2_emea_master",  # 2024-09-13
    "owcs_2024_asia_s2_wildcard",  # 2024-09-13
    "owcs_2024_na_s4_groups",      # 2024-09-27
    "owcs_2024_emea_s4_groups",    # 2024-09-27
    "owcs_2024_asia_s2_main",      # 2024-09-27
    "owcs_2024_na_s4_main",        # 2024-10-10
    "owcs_2024_emea_s4_main",      # 2024-10-10
    "faceit_2024_s3_na_master",    # ~Oct 2024 (no date in source, placed after Stage 4)
    "faceit_2024_s3_emea_master",  # ~Oct 2024 (no date in source, placed after Stage 4)
    "owcs_2024_world_finals",      # 2024-11-22
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

    # Known legitimate lowercase/special names
    known_lowercase = {"nu.age"}
    # Known legitimate disambiguation names (kept intentionally)
    known_disambig = {"Insomnia (Japanese team)", "Vice (North American team)"}
    # Suspect: fully lowercase AND not in known-lowercase set
    suspect = [
        t for t in all_teams
        if (t == t.lower() and t not in known_lowercase)
        or ("[MANUAL]" in t)
        or ("(korean team)" in t.lower())
    ]
    # Remove known-legitimate disambig forms from suspect list
    suspect = [t for t in suspect if t not in known_disambig]

    print("\n=== Build Global Merge: Summary ===")
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

    # Per-event row counts
    print("\n  Rows per event:")
    for eid in EVENT_ORDER:
        count = sum(1 for r in rows if r["event_id"] == eid)
        print(f"    {eid:<45} {count:>4}")

    print(f"\n  Output: {OUTPUT_FILE}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print("=== Build Global Merge ===")

    print("\n[1] Loading drafts...")
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
