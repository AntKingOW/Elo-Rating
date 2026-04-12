"""
OWCS 2025 Global Elo Rating Calculator

Reads OWCS_2025_GLOBAL_MAP_RESULTS.csv, initializes team ratings from
OWCS_2024_GLOBAL_ELO_FINAL.csv (carry-over), processes all 2025 maps, and outputs:
  - OWCS_2025_GLOBAL_ELO_FINAL.csv     — final rankings
  - OWCS_2025_GLOBAL_ELO_HISTORY.csv   — per-map rating snapshots
  - OWCS_2025_GLOBAL_ELO_RANKINGS.md   — human-readable power ranking

Elo model:
  BASE_ELO = 1400, K = 24 (flat — same for regional and international events)
  Ea = 1 / (1 + 10^((Rb - Ra) / 400))
  Ra' = Ra + K * (Sa - Ea)
  New team first appearance: starts at BASE_ELO (1400).
  Teams carried over from 2024: start from their 2024 final Elo.
  Draw maps: Elo delta = 0, map is recorded but not updated.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

ROOT          = Path(__file__).resolve().parent
INPUT_FILE    = ROOT / "OWCS_2025_GLOBAL_MAP_RESULTS.csv"
PRIOR_ELO     = ROOT / "OWCS_2024_GLOBAL_ELO_FINAL.csv"   # 2024 final Elo as starting point
OUT_CSV       = ROOT / "OWCS_2025_GLOBAL_ELO_FINAL.csv"
OUT_HISTORY   = ROOT / "OWCS_2025_GLOBAL_ELO_HISTORY.csv"
OUT_RANKINGS  = ROOT / "OWCS_2025_GLOBAL_ELO_RANKINGS.md"

BASE_ELO        = 1400.0
K_BASE          = 24.0
K_INTERNATIONAL = 24.0   # same as K_BASE (FIDE flat-K principle)

# ---------------------------------------------------------------------------
# 2024→2025 name mapping
# "Team name in 2025" → "Team name in 2024 final Elo"
# Used when a team rebranded between seasons.
# ---------------------------------------------------------------------------
CARRY_OVER_2024_MAP: dict[str, str] = {
    "Avidity":           "Rad x Avidity",   # same roster as Rad x Avidity 2024, back under Avidity brand
    "Team Vision":       "Vision Esports",  # Vision Esports renamed to Team Vision (Jan 2025)
    "Full House":        "Full House",      # same Pacific team across 2024 -> 2025 after canonical spacing cleanup
    "Extinction":        "EXN Zenith",      # EXN Zenith (2024 NA S4) rebranded to Extinction for 2025
    "Nosebleed Esports": "99DIVINE",        # 99DIVINE (Pacific) rebranded to Nosebleed Esports (2025 S3)
}

# ---------------------------------------------------------------------------
# Teams that share a 2024 name but are DIFFERENT teams in 2025
# → force to BASE_ELO regardless of 2024 Elo match
# ---------------------------------------------------------------------------
FORCE_RESET_2025: set[str] = {
    "Team Z",      # 2024 Team Z roster disbanded (joined O3 Splash Nov 2024); 2025 Team Z = new roster
    "ROC Esports", # 2024 ROC Esports = EMEA team; 2025 ROC Esports = different China team, same name
}

# ---------------------------------------------------------------------------
# Event classification
# ---------------------------------------------------------------------------

# Events classified as non-regional (skip when inferring home region)
INTERNATIONAL_EVENTS: set[str] = {
    "owcs_2025_asia_s1_main",
    "owcs_2025_champions_clash",
    "owcs_2025_midseason",
    "owcs_2025_apac_championship",
    "owcs_2025_korea_road_to_wf",
    "owcs_2025_world_finals",
}

REGION_LABEL: dict[str, str] = {
    "korea":         "Korea",
    "japan":         "Japan",
    "pacific":       "Pacific",
    "na":            "NA",
    "emea":          "EMEA",
    "china":         "China",
    "international": "Intl",
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class TeamStats:
    name:          str
    elo:           float = BASE_ELO
    maps_played:   int   = 0
    maps_won:      int   = 0
    maps_lost:     int   = 0
    maps_drawn:    int   = 0
    first_event:   str   = ""
    last_event:    str   = ""
    home_region:   str   = ""
    region_counts: dict  = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Elo math
# ---------------------------------------------------------------------------

def expected_score(ra: float, rb: float) -> float:
    return 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))


# ---------------------------------------------------------------------------
# Load 2024 final Elo
# ---------------------------------------------------------------------------

def load_prior_elo() -> dict[str, float]:
    """Returns {team_name: final_elo} from 2024 final CSV."""
    prior: dict[str, float] = {}
    if not PRIOR_ELO.exists():
        print(f"  [WARN] {PRIOR_ELO} not found — all teams start at BASE_ELO")
        return prior
    for row in csv.DictReader(PRIOR_ELO.open(encoding="utf-8")):
        prior[row["team"]] = float(row["elo"])
    print(f"  Loaded {len(prior)} teams from 2024 final Elo")
    return prior


# ---------------------------------------------------------------------------
# Main calculation
# ---------------------------------------------------------------------------

def main() -> None:
    print("=== OWCS 2025 Global Elo Calculator ===\n")

    # Load prior Elo
    print("[0] Loading 2024 carry-over Elo...")
    prior_elo = load_prior_elo()

    rows = list(csv.DictReader(INPUT_FILE.open(encoding="utf-8")))
    print(f"[1] Loaded {len(rows)} map rows from {INPUT_FILE.name}\n")

    teams:   dict[str, TeamStats] = {}
    history: list[dict]           = []

    def get_team(name: str) -> TeamStats:
        if name not in teams:
            ts = TeamStats(name=name)
            # Determine starting Elo
            if name in FORCE_RESET_2025:
                ts.elo = BASE_ELO
                print(f"  [RESET] {name} → {BASE_ELO} (different team from 2024)")
            else:
                # Check direct carry-over first, then name alias
                lookup = CARRY_OVER_2024_MAP.get(name, name)
                if lookup in prior_elo:
                    ts.elo = prior_elo[lookup]
                    if lookup != name:
                        print(f"  [CARRY] {name} ← {lookup} (2024 Elo: {ts.elo:.1f})")
                elif name in prior_elo:
                    ts.elo = prior_elo[name]
                else:
                    ts.elo = BASE_ELO  # new team
            teams[name] = ts
        return teams[name]

    def record_appearance(t: TeamStats, event_id: str, region: str) -> None:
        if not t.first_event:
            t.first_event = event_id
        t.last_event = event_id
        if event_id not in INTERNATIONAL_EVENTS:
            t.region_counts[region] = t.region_counts.get(region, 0) + 1

    for row in rows:
        winner   = row["winner"]
        loser    = row["loser"]
        team_a   = row["team_a"]
        team_b   = row["team_b"]
        event_id = row["event_id"]
        region   = row["event_region"]
        gmo      = int(row["global_map_order"])

        # --- Draw map ---
        if winner == "DRAW":
            ta = get_team(team_a)
            tb = get_team(team_b)
            record_appearance(ta, event_id, region)
            record_appearance(tb, event_id, region)
            ta.maps_drawn += 1
            tb.maps_drawn += 1
            ta.maps_played += 1
            tb.maps_played += 1
            history.append({"global_map_order": gmo, "event_id": event_id, "team": team_a, "elo_after": f"{ta.elo:.2f}", "result": "draw"})
            history.append({"global_map_order": gmo, "event_id": event_id, "team": team_b, "elo_after": f"{tb.elo:.2f}", "result": "draw"})
            continue

        # --- Skip rows with unresolved [MANUAL] winner ---
        if winner == "[MANUAL]" or loser == "[MANUAL]":
            continue

        # --- Normal map (win/loss) ---
        tw = get_team(winner)
        tl = get_team(loser)

        record_appearance(tw, event_id, region)
        record_appearance(tl, event_id, region)

        ew = expected_score(tw.elo, tl.elo)
        el = 1.0 - ew

        tw.elo += K_BASE * (1.0 - ew)
        tl.elo += K_BASE * (0.0 - el)

        tw.maps_played += 1
        tl.maps_played += 1
        tw.maps_won    += 1
        tl.maps_lost   += 1

        history.append({"global_map_order": gmo, "event_id": event_id, "team": winner, "elo_after": f"{tw.elo:.2f}", "result": "win"})
        history.append({"global_map_order": gmo, "event_id": event_id, "team": loser,  "elo_after": f"{tl.elo:.2f}", "result": "loss"})

    # --- Infer home region ---
    for t in teams.values():
        if t.region_counts:
            t.home_region = max(t.region_counts, key=t.region_counts.get)
        else:
            t.home_region = "international"

    # --- Sort by final Elo ---
    ranked = sorted(teams.values(), key=lambda t: -t.elo)

    # --- Write final CSV ---
    final_fields = [
        "rank", "team", "elo", "home_region",
        "maps_played", "maps_won", "maps_lost", "maps_drawn", "win_pct",
        "first_event", "last_event",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=final_fields)
        writer.writeheader()
        for rank, t in enumerate(ranked, 1):
            decisive = t.maps_won + t.maps_lost
            win_pct  = f"{t.maps_won / decisive * 100:.1f}%" if decisive > 0 else "N/A"
            writer.writerow({
                "rank": rank, "team": t.name,
                "elo": f"{t.elo:.1f}",
                "home_region": REGION_LABEL.get(t.home_region, t.home_region),
                "maps_played": t.maps_played, "maps_won": t.maps_won,
                "maps_lost": t.maps_lost, "maps_drawn": t.maps_drawn,
                "win_pct": win_pct,
                "first_event": t.first_event, "last_event": t.last_event,
            })

    # --- Write history CSV ---
    hist_fields = ["global_map_order", "event_id", "team", "elo_after", "result"]
    with OUT_HISTORY.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=hist_fields)
        writer.writeheader()
        writer.writerows(history)

    # --- Write markdown ---
    _write_markdown(ranked)

    # --- Console summary ---
    print(f"\n=== OWCS 2025 Global Elo — Complete ===")
    print(f"  Maps processed : {len(rows)}")
    print(f"  Maps with Elo  : {len(history) // 2}  (skipped [MANUAL] winners)")
    print(f"  Teams rated    : {len(teams)}")
    print()
    print(f"  {'Rank':<5} {'Team':<40} {'Elo':>7}  {'W':>4} {'L':>4} {'D':>3}  {'Win%':>6}  Region")
    print(f"  {'-'*5} {'-'*40} {'-'*7}  {'-'*4} {'-'*4} {'-'*3}  {'-'*6}  ------")
    for rank, t in enumerate(ranked[:30], 1):
        decisive = t.maps_won + t.maps_lost
        win_pct  = f"{t.maps_won / decisive * 100:.1f}%" if decisive > 0 else "N/A"
        reg = REGION_LABEL.get(t.home_region, t.home_region)
        print(f"  {rank:<5} {t.name:<40} {t.elo:>7.1f}  {t.maps_won:>4} {t.maps_lost:>4} {t.maps_drawn:>3}  {win_pct:>6}  {reg}")

    print(f"\n  Outputs:")
    print(f"    {OUT_CSV}")
    print(f"    {OUT_HISTORY}")
    print(f"    {OUT_RANKINGS}")


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------

def _write_markdown(ranked: list[TeamStats]) -> None:
    lines = [
        "# OWCS 2025 Global Elo Power Rankings",
        "",
        f"- **Base Elo**: {BASE_ELO} (new teams) | carry-over: 2024 final Elo",
        f"- **K**: {K_BASE} (flat — regional and international events equal)",
        "- **Unit**: 1 map = 1 Elo update  |  Draw maps: no Elo change",
        "- 24 events, 5 phases, all regions (incl. China new in 2025)",
        "",
    ]

    regions_order = ["Korea", "Japan", "Pacific", "NA", "EMEA", "China"]
    by_region: dict[str, list[TeamStats]] = {}
    for t in ranked:
        reg = REGION_LABEL.get(t.home_region, t.home_region)
        by_region.setdefault(reg, []).append(t)

    # Global table (top 50)
    lines += [
        "## Global Top 50",
        "",
        "| Rank | Team | Elo | Region | Maps | W | L | D | Win% |",
        "|------|------|-----|--------|------|---|---|---|------|",
    ]
    for rank, t in enumerate(ranked[:50], 1):
        decisive = t.maps_won + t.maps_lost
        win_pct  = f"{t.maps_won / decisive * 100:.1f}%" if decisive > 0 else "N/A"
        reg = REGION_LABEL.get(t.home_region, t.home_region)
        lines.append(
            f"| {rank} | {t.name} | {t.elo:.1f} | {reg} | "
            f"{t.maps_played} | {t.maps_won} | {t.maps_lost} | {t.maps_drawn} | {win_pct} |"
        )
    lines += [""]

    # Per-region tables
    for reg in regions_order:
        teams_in_region = by_region.get(reg, [])
        if not teams_in_region:
            continue
        lines += [
            f"## {reg} Rankings",
            "",
            "| Rank | Team | Elo | Maps | W | L | Win% |",
            "|------|------|-----|------|---|---|------|",
        ]
        for rank, t in enumerate(teams_in_region, 1):
            decisive = t.maps_won + t.maps_lost
            win_pct  = f"{t.maps_won / decisive * 100:.1f}%" if decisive > 0 else "N/A"
            lines.append(
                f"| {rank} | {t.name} | {t.elo:.1f} | "
                f"{t.maps_played} | {t.maps_won} | {t.maps_lost} | {win_pct} |"
            )
        lines += [""]

    OUT_RANKINGS.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
