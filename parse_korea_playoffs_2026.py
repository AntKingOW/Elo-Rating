"""
parse_korea_playoffs_2026.py

Parses Korea 2026 Stage 1 playoff match results from Liquipedia main page:
  - Playoffs Seeding Decider Matches
  - Last Chance Qualifier
  - Regional Playoffs (including 3rd place match)

Outputs: drafts/2026/owcs_2026_asia_s1_korea_playoffs.csv
"""

from __future__ import annotations
import csv, re
from pathlib import Path
from scrape_group_stages import fetch_raw, FIELDNAMES

ROOT = Path(__file__).resolve().parent
OUT  = ROOT / "drafts" / "2026" / "owcs_2026_asia_s1_korea_playoffs.csv"

WIKI_TITLE = "Overwatch_Champions_Series/2026/Asia/Stage_1/Korea"
EVENT_ID   = "owcs_2026_asia_s1_korea_playoffs"
SOURCE_URL = "https://liquipedia.net/overwatch/Overwatch_Champions_Series/2026/Asia/Stage_1/Korea"

CASE_NORM = {
    "zeta division":   "ZETA DIVISION",
    "crazy raccoon":   "Crazy Raccoon",
    "team falcons":    "Team Falcons",
    "onside gaming":   "ONSIDE GAMING",
    "t1":              "T1",
    "zan esports":     "ZAN Esports",
    "poker face":      "Poker Face",
    "cheeseburger":    "Cheeseburger",
    "new era":         "New Era",
}

def norm(name: str) -> str:
    return CASE_NORM.get(name.strip().lower(), name.strip())

def parse_date(raw: str) -> str:
    m = re.search(r'(\d{4}-\d{2}-\d{2})', raw)
    return m.group(1) if m else ""

def stage_label_for(pos: int, stage_positions: list[tuple[int,str]]) -> str:
    label = ""
    for p, lbl in stage_positions:
        if p <= pos:
            label = lbl
    return label

def week_label_for(stage: str) -> str:
    return {
        "Playoffs Seeding Decider Matches": "Seeding Decider",
        "Last Chance Qualifier":            "Last Chance Qualifier",
        "Regional Playoffs":                "Regional Playoffs",
    }.get(stage, stage)

def main():
    print("Fetching wikitext...")
    wikitext = fetch_raw(WIKI_TITLE)
    if not wikitext:
        print("FAILED — empty wikitext")
        return

    # Find stage section positions
    stage_positions: list[tuple[int,str]] = []
    for m in re.finditer(r'\{\{Stage\|([^}]+)\}\}', wikitext):
        stage_positions.append((m.start(), m.group(1).strip()))

    # Find ALL match blocks (including RxMTP)
    match_starts = list(re.finditer(
        r'\|(?:Rx\w+|R\d+M\w+|M\d+)=\{\{Match', wikitext
    ))
    print(f"Found {len(match_starts)} match blocks")

    rows: list[dict] = []
    global_map_order = 1

    for i, ms in enumerate(match_starts):
        start = ms.start()
        end   = match_starts[i+1].start() if i+1 < len(match_starts) else len(wikitext)
        block = wikitext[start:end]

        stage = stage_label_for(start, stage_positions)
        week  = week_label_for(stage)

        date_m = re.search(r'\|date=([^\n]+)', block)
        match_date = parse_date(date_m.group(1)) if date_m else ""

        # Day label: extract "May 2" style from date
        day_m = re.search(r'\d{4}-(\d{2}-\d{2})', match_date)
        day_label = match_date  # use full date as day label

        bo_m = re.search(r'\|bestof=(\d+)', block)
        series_format = f"bo{bo_m.group(1)}" if bo_m else "bo5"

        opp1 = re.search(r'\|opponent1=\{\{TeamOpponent\|([^|}]+)', block)
        opp2 = re.search(r'\|opponent2=\{\{TeamOpponent\|([^|}]+)', block)
        if not opp1 or not opp2:
            continue
        team_a = norm(opp1.group(1))
        team_b = norm(opp2.group(1))

        # Parse maps
        maps = list(re.finditer(
            r'\|map(\d+)=\{\{Map\|map=([^|]*)\|mode=([^|]*)\|score1=[^|]*\|score2=[^|]*\|winner=(\d*)',
            block
        ))

        match_order = i + 1
        for gn, mm in enumerate(maps, 1):
            map_name = mm.group(2).strip()
            map_mode = mm.group(3).strip().title()
            winner_side = mm.group(4).strip()
            if winner_side == "1":
                winner, loser = team_a, team_b
            elif winner_side == "2":
                winner, loser = team_b, team_a
            else:
                winner, loser = "DRAW", "DRAW"

            rows.append({
                "event_id":         EVENT_ID,
                "event_region":     "korea",
                "season_year":      2026,
                "stage_label":      "Stage 1",
                "week_label":       week,
                "day_label":        match_date,
                "match_date":       match_date,
                "match_order":      match_order,
                "game_number":      gn,
                "team_a":           team_a,
                "team_b":           team_b,
                "winner":           winner,
                "loser":            loser,
                "map_name":         map_name,
                "map_mode":         map_mode,
                "series_format":    series_format,
                "source_url":       SOURCE_URL,
                "source_note":      "liquipedia_playoff_parse",
            })
            global_map_order += 1

        print(f"  [{stage}] {match_date} | {team_a} vs {team_b} | {len(maps)} maps")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSaved {len(rows)} map rows → {OUT}")

if __name__ == "__main__":
    main()
