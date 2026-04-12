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

    # Clean roster transfers confirmed by web research
    "Students of the Game": "NRG Shock",        # NRG acquired SotG roster (Dallas Major, 2024-05-31)
    "Ataraxia":             "Virtus.pro",        # Virtus.pro signed Ataraxia roster (2024-06-11)
    "DAF":                  "Bleed Esports",     # Bleed Esports acquired DAF roster (2024-06-13)
    "Toronto Ultra":        "Toronto Defiant",   # Same org (OverActive Media), EWC-only rebrand
    "Honeypot":             "99DIVINE",          # 99DIVINE acquired Honeypot seed + roster (Pacific S2)
    "Avidity":              "Rad x Avidity",     # Rad x Avidity acquired Avidity roster (Sep 2024)
    "Green Fortnite":       "Timeless Ethereal", # Timeless Ethereal acquired Green Fortnite roster (Aug 2024)
    "YETI":                 "Fnatic",            # Fnatic signed YETI core players (Jun 2024, EWC + Korea S2)

    # Korea 2024
    "Vesta Crew":           "VEC",               # Vesta Crew rebranded to VEC (Korea S2 2024)

    # EMEA 2024
    "ROC Esports":          "Rocstars",          # ROC Esports rebranded to Rocstars (EMEA S2 2024)
    "Gaimin Gladiators":    "Team Peps",         # Team Peps used Gaimin Gladiators brand in EMEA S3 + EWC, then reverted
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
    "Team PEPS":      "Team Peps",            # All-caps variant in EMEA S2 groups wikitext
    "Nu.age":         "nu.age",               # nu.age is the official lowercase form

    # International / disambiguation
    "321 diving":     "321 Diving",
    "FullHouse":      "Full House",

    # Normalization bug fixes (same team, different capitalization in different draft files)
    "WASP X OHHHH NO":          "Wasp X Ohhhh No",   # Liquipedia canonical: mixed case
    "Vendetta (European Team)": "Vendetta (European team)",  # lowercase 't'
    "Team PEPS":                "Team Peps",          # Same French team, Liquipedia: "Team Peps"
}

SPECIAL_WINNER_VALUES = {"DRAW", "[MANUAL]"}

# Events where "Timeless" = original roster that became TSM (pre-signing split)
# After OWCS 2024 Stage 2 ended, TSM signed the Timeless roster (May 2024).
# FACEIT S1 NA onwards: "Timeless" = new/different roster (keeps the Timeless brand).
TIMELESS_TO_TSM_EVENTS: set[str] = {
    "owcs_2024_na_s1_groups",
    "owcs_2024_na_s1_main",
    "owcs_2024_na_s2_groups",
    "owcs_2024_na_s2_main",
}


def normalize_team(name: str, event_id: str = "") -> str:
    """Two-step normalization: CASE_NORM first, then SUCCESSION (chained)."""
    # Step 1: fix case/variant spelling → canonical display name
    canonical = CASE_NORM.get(name, name)
    # Step 2: conditional Timeless split (before SUCCESSION to avoid override)
    if canonical == "Timeless" and event_id in TIMELESS_TO_TSM_EVENTS:
        return "TSM"
    # Step 3: roster succession (old org name → new org name)
    return SUCCESSION.get(canonical, canonical)


def normalize_winner(val: str, event_id: str = "") -> str:
    if val in SPECIAL_WINNER_VALUES:
        return val
    return normalize_team(val, event_id)


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
    "ewc_2024",                    # 2024-07-26
    "owcs_2024_asia_s2_pacific",   # 2024-08-08
    "owcs_2024_na_s3_groups",      # 2024-08-16
    "owcs_2024_emea_s3_groups",    # 2024-08-16
    "owcs_2024_na_s3_main",        # 2024-08-29
    "owcs_2024_emea_s3_main",      # 2024-08-29
    "owcs_2024_asia_s2_korea",     # 2024-08-30
    "owcs_2024_asia_s2_japan",     # 2024-09-02
    "owcs_2024_asia_s2_wildcard",  # 2024-09-13
    "owcs_2024_na_s4_groups",      # 2024-09-27
    "owcs_2024_emea_s4_groups",    # 2024-09-27
    "owcs_2024_asia_s2_main",      # 2024-09-27
    "owcs_2024_na_s4_main",        # 2024-10-10
    "owcs_2024_emea_s4_main",      # 2024-10-10
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

EXCLUDE_EVENT_IDS: set[str] = {
    # FACEIT Masters Showdown — 2nd-division circuit, not OWCS proper
    "faceit_2024_s1_na_master",
    "faceit_2024_s1_emea_master",
    "faceit_2024_s2_na_master",
    "faceit_2024_s2_emea_master",
    "faceit_2024_s3_na_master",
    "faceit_2024_s3_emea_master",
}

def load_all_drafts() -> list[dict]:
    rows: list[dict] = []
    for f in sorted(DRAFTS_DIR.glob("*.csv")):
        file_rows = list(csv.DictReader(f.open(encoding="utf-8")))
        file_rows = [r for r in file_rows if r.get("event_id") not in EXCLUDE_EVENT_IDS]
        rows.extend(file_rows)
    return rows


def normalize_all(rows: list[dict]) -> list[dict]:
    for row in rows:
        eid = row.get("event_id", "")
        row["team_a"] = normalize_team(row["team_a"], eid)
        row["team_b"] = normalize_team(row["team_b"], eid)
        row["winner"] = normalize_winner(row["winner"], eid)
        row["loser"]  = normalize_winner(row["loser"],  eid)
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
