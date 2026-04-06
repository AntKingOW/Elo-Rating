"""
OWCS 2024 Global Elo Rating Calculator

Reads OWCS_2024_GLOBAL_MAP_RESULTS.csv (1 row = 1 map result),
processes each map in global_map_order sequence, and outputs:
  - OWCS_2024_GLOBAL_ELO_FINAL.csv     — final rankings
  - OWCS_2024_GLOBAL_ELO_HISTORY.csv   — per-map rating snapshots
  - OWCS_2024_GLOBAL_ELO_RANKINGS.md   — human-readable power ranking

Elo model:
  Base = 1500, K = 24
  Ea = 1 / (1 + 10^((Rb - Ra) / 400))
  Ra' = Ra + K * (Sa - Ea)
  Draw maps (winner == "DRAW"): Elo delta = 0, map is recorded but not updated.
  Forfeit maps (source_note == "forfeit_default"): treated as regular wins.
  New team first appearance: starts at Base (1500).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

ROOT         = Path(__file__).resolve().parent
INPUT_FILE   = ROOT / "OWCS_2024_GLOBAL_MAP_RESULTS.csv"
OUT_CSV      = ROOT / "OWCS_2024_GLOBAL_ELO_FINAL.csv"
OUT_HISTORY  = ROOT / "OWCS_2024_GLOBAL_ELO_HISTORY.csv"
OUT_RANKINGS = ROOT / "OWCS_2024_GLOBAL_ELO_RANKINGS.md"

BASE_ELO = 1500.0
K        = 24.0

# Events classified as non-regional (skip when inferring home region)
INTERNATIONAL_EVENTS = {
    "owcs_2024_asia_s1_wildcard",
    "owcs_2024_asia_s1_main",
    "owcs_2024_asia_s2_wildcard",
    "owcs_2024_asia_s2_main",
    "owcs_2024_dallas_major",
    "ewc_2024",
    "owcs_2024_world_finals",
}

# Human-readable region labels
REGION_LABEL = {
    "korea":         "Korea",
    "japan":         "Japan",
    "pacific":       "Pacific",
    "na":            "NA",
    "emea":          "EMEA",
    "international": "Intl",
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class TeamStats:
    name:         str
    elo:          float = BASE_ELO
    maps_played:  int   = 0
    maps_won:     int   = 0
    maps_lost:    int   = 0
    maps_drawn:   int   = 0
    first_event:  str   = ""
    last_event:   str   = ""
    home_region:  str   = ""
    # region → appearance count (for home-region inference)
    region_counts: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Elo math
# ---------------------------------------------------------------------------

def expected_score(ra: float, rb: float) -> float:
    """Expected score for team with rating ra against rb (0-1 scale)."""
    return 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))


# ---------------------------------------------------------------------------
# Main calculation
# ---------------------------------------------------------------------------

def main() -> None:
    rows = list(csv.DictReader(INPUT_FILE.open(encoding="utf-8")))

    teams:   dict[str, TeamStats] = {}
    history: list[dict]           = []

    def get_team(name: str) -> TeamStats:
        if name not in teams:
            teams[name] = TeamStats(name=name)
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

        # --- Draw map: record but skip Elo update ---
        if winner == "DRAW":
            ta = get_team(team_a)
            tb = get_team(team_b)
            record_appearance(ta, event_id, region)
            record_appearance(tb, event_id, region)
            ta.maps_drawn += 1
            tb.maps_drawn += 1
            ta.maps_played += 1
            tb.maps_played += 1
            history.append({
                "global_map_order": gmo,
                "event_id": event_id,
                "team": team_a,
                "elo_after": f"{ta.elo:.2f}",
                "result": "draw",
            })
            history.append({
                "global_map_order": gmo,
                "event_id": event_id,
                "team": team_b,
                "elo_after": f"{tb.elo:.2f}",
                "result": "draw",
            })
            continue

        # --- Normal map (win/loss) ---
        tw = get_team(winner)
        tl = get_team(loser)

        record_appearance(tw, event_id, region)
        record_appearance(tl, event_id, region)

        ew = expected_score(tw.elo, tl.elo)   # winner's expected score
        el = 1.0 - ew                           # loser's expected score

        tw.elo += K * (1.0 - ew)
        tl.elo += K * (0.0 - el)

        tw.maps_played += 1
        tl.maps_played += 1
        tw.maps_won    += 1
        tl.maps_lost   += 1

        history.append({
            "global_map_order": gmo,
            "event_id": event_id,
            "team": winner,
            "elo_after": f"{tw.elo:.2f}",
            "result": "win",
        })
        history.append({
            "global_map_order": gmo,
            "event_id": event_id,
            "team": loser,
            "elo_after": f"{tl.elo:.2f}",
            "result": "loss",
        })

    # --- Infer home region for each team ---
    for t in teams.values():
        if t.region_counts:
            t.home_region = max(t.region_counts, key=t.region_counts.get)
        else:
            t.home_region = "international"

    # --- Sort by final Elo (descending) ---
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
                "rank":        rank,
                "team":        t.name,
                "elo":         f"{t.elo:.1f}",
                "home_region": REGION_LABEL.get(t.home_region, t.home_region),
                "maps_played": t.maps_played,
                "maps_won":    t.maps_won,
                "maps_lost":   t.maps_lost,
                "maps_drawn":  t.maps_drawn,
                "win_pct":     win_pct,
                "first_event": t.first_event,
                "last_event":  t.last_event,
            })

    # --- Write history CSV ---
    hist_fields = ["global_map_order", "event_id", "team", "elo_after", "result"]
    with OUT_HISTORY.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=hist_fields)
        writer.writeheader()
        writer.writerows(history)

    # --- Write markdown rankings ---
    _write_markdown(ranked)

    # --- Console summary ---
    print(f"\n=== OWCS 2024 Global Elo — Calculation Complete ===")
    print(f"  Maps processed : {len(rows)}")
    print(f"  Teams rated    : {len(teams)}")
    print(f"  History rows   : {len(history)}")
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
        "# OWCS 2024 Global Elo Power Rankings",
        "",
        f"- **Base Elo**: {BASE_ELO}  |  **K**: {K}  |  **Unit**: 1 map = 1 update",
        "- Draw maps: no Elo change  |  Forfeit: 2:0 default applied",
        "- 35 events, 1,940 map rows, all regions in one global pool",
        "",
    ]

    # Group by region
    regions_order = ["Korea", "Japan", "Pacific", "NA", "EMEA", "Intl", "international"]
    by_region: dict[str, list[TeamStats]] = {}
    for t in ranked:
        reg = REGION_LABEL.get(t.home_region, t.home_region)
        by_region.setdefault(reg, []).append(t)

    # Full global table (top 50)
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
    for reg in ["Korea", "Japan", "Pacific", "NA", "EMEA"]:
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
