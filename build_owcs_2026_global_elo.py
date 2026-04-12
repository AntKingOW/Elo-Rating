"""
OWCS 2026 Stage 1 Global Elo Rating Calculator

Reads OWCS_2026_GLOBAL_MAP_RESULTS.csv, initializes team ratings from
OWCS_2025_GLOBAL_ELO_FINAL.csv (carry-over), processes all 2026 Stage 1 maps,
and outputs:
  - OWCS_2026_GLOBAL_ELO_FINAL.csv
  - OWCS_2026_GLOBAL_ELO_HISTORY.csv
  - OWCS_2026_GLOBAL_ELO_RANKINGS.md

This file is intentionally separate from the 2025 calculator.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUT_FILE = ROOT / "OWCS_2026_GLOBAL_MAP_RESULTS.csv"
PRIOR_ELO = ROOT / "OWCS_2025_GLOBAL_ELO_FINAL.csv"
OUT_CSV = ROOT / "OWCS_2026_GLOBAL_ELO_FINAL.csv"
OUT_HISTORY = ROOT / "OWCS_2026_GLOBAL_ELO_HISTORY.csv"
OUT_RANKINGS = ROOT / "OWCS_2026_GLOBAL_ELO_RANKINGS.md"

BASE_ELO = 1400.0
K_BASE = 24.0

# Add confirmed 2025 -> 2026 rebrand carry-overs here.
CARRY_OVER_2025_MAP: dict[str, str] = {}

# Add same-name-but-different-team resets here when confirmed.
FORCE_RESET_2026: set[str] = set()

INTERNATIONAL_EVENTS: set[str] = set()

REGION_LABEL: dict[str, str] = {
    "korea": "Korea",
    "japan": "Japan",
    "pacific": "Pacific",
    "na": "NA",
    "emea": "EMEA",
    "china": "China",
    "international": "Intl",
}


@dataclass
class TeamStats:
    name: str
    elo: float = BASE_ELO
    maps_played: int = 0
    maps_won: int = 0
    maps_lost: int = 0
    maps_drawn: int = 0
    first_event: str = ""
    last_event: str = ""
    home_region: str = ""
    region_counts: dict = field(default_factory=dict)


def expected_score(ra: float, rb: float) -> float:
    return 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))


def load_prior_elo() -> dict[str, float]:
    prior: dict[str, float] = {}
    if not PRIOR_ELO.exists():
        print(f"  [WARN] {PRIOR_ELO} not found - all teams start at BASE_ELO")
        return prior
    for row in csv.DictReader(PRIOR_ELO.open(encoding="utf-8")):
        prior[row["team"]] = float(row["elo"])
    print(f"  Loaded {len(prior)} teams from 2025 final Elo")
    return prior


def main() -> None:
    print("=== OWCS 2026 Stage 1 Global Elo Calculator ===\n")

    print("[0] Loading 2025 carry-over Elo...")
    prior_elo = load_prior_elo()

    rows = list(csv.DictReader(INPUT_FILE.open(encoding="utf-8")))
    print(f"[1] Loaded {len(rows)} map rows from {INPUT_FILE.name}\n")

    teams: dict[str, TeamStats] = {}
    history: list[dict] = []

    def get_team(name: str) -> TeamStats:
        if name not in teams:
            ts = TeamStats(name=name)
            if name in FORCE_RESET_2026:
                ts.elo = BASE_ELO
            else:
                lookup = CARRY_OVER_2025_MAP.get(name, name)
                ts.elo = prior_elo.get(lookup, BASE_ELO)
            teams[name] = ts
        return teams[name]

    def record_appearance(t: TeamStats, event_id: str, region: str) -> None:
        if not t.first_event:
            t.first_event = event_id
        t.last_event = event_id
        if event_id not in INTERNATIONAL_EVENTS:
            t.region_counts[region] = t.region_counts.get(region, 0) + 1

    for row in rows:
        winner = row["winner"]
        loser = row["loser"]
        team_a = row["team_a"]
        team_b = row["team_b"]
        event_id = row["event_id"]
        region = row["event_region"]
        gmo = int(row["global_map_order"])

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

        if winner == "[MANUAL]" or loser == "[MANUAL]":
            continue

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
        tw.maps_won += 1
        tl.maps_lost += 1

        history.append({"global_map_order": gmo, "event_id": event_id, "team": winner, "elo_after": f"{tw.elo:.2f}", "result": "win"})
        history.append({"global_map_order": gmo, "event_id": event_id, "team": loser, "elo_after": f"{tl.elo:.2f}", "result": "loss"})

    for t in teams.values():
        if t.region_counts:
            t.home_region = max(t.region_counts, key=t.region_counts.get)
        else:
            t.home_region = "international"

    ranked = sorted(teams.values(), key=lambda t: -t.elo)

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
            win_pct = f"{t.maps_won / decisive * 100:.1f}%" if decisive > 0 else "N/A"
            writer.writerow({
                "rank": rank,
                "team": t.name,
                "elo": f"{t.elo:.1f}",
                "home_region": REGION_LABEL.get(t.home_region, t.home_region),
                "maps_played": t.maps_played,
                "maps_won": t.maps_won,
                "maps_lost": t.maps_lost,
                "maps_drawn": t.maps_drawn,
                "win_pct": win_pct,
                "first_event": t.first_event,
                "last_event": t.last_event,
            })

    hist_fields = ["global_map_order", "event_id", "team", "elo_after", "result"]
    with OUT_HISTORY.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=hist_fields)
        writer.writeheader()
        writer.writerows(history)

    _write_markdown(ranked)

    print(f"\n=== OWCS 2026 Stage 1 Global Elo - Complete ===")
    print(f"  Maps processed : {len(rows)}")
    print(f"  Teams rated    : {len(teams)}")
    print(f"  Outputs:")
    print(f"    {OUT_CSV}")
    print(f"    {OUT_HISTORY}")
    print(f"    {OUT_RANKINGS}")


def _write_markdown(ranked: list[TeamStats]) -> None:
    lines = [
        "# OWCS 2026 Stage 1 Global Elo Power Rankings",
        "",
        f"- **Base Elo**: {BASE_ELO} (new teams) | carry-over: 2025 final Elo",
        f"- **K**: {K_BASE}",
        "- **Scope**: 2026 Stage 1 regular-season results collected so far",
        "",
        "| Rank | Team | Elo | Region | Maps | W | L | D | Win% |",
        "|------|------|-----|--------|------|---|---|---|------|",
    ]
    for rank, t in enumerate(ranked, 1):
        decisive = t.maps_won + t.maps_lost
        win_pct = f"{t.maps_won / decisive * 100:.1f}%" if decisive > 0 else "N/A"
        reg = REGION_LABEL.get(t.home_region, t.home_region)
        lines.append(
            f"| {rank} | {t.name} | {t.elo:.1f} | {reg} | {t.maps_played} | {t.maps_won} | {t.maps_lost} | {t.maps_drawn} | {win_pct} |"
        )
    OUT_RANKINGS.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
