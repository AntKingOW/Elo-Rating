"""
scrape_group_stages.py

Fetches group-stage / regular-season match data from Liquipedia (raw wikitext),
parses {{Match}} templates, and prepends the resulting rows to the existing
draft CSV files so playoffs keep their relative ordering.

Usage:
    python scrape_group_stages.py
"""

from __future__ import annotations
import csv, re, time, sys
from datetime import datetime
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
ROOT        = Path(__file__).resolve().parent
DRAFTS_2024 = ROOT / "drafts"
DRAFTS_2025 = ROOT / "drafts" / "2025"

LIQUIPEDIA_RAW = "https://liquipedia.net/overwatch/index.php"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AntKingOW-EloBot/1.0; +research)",
    "Accept-Encoding": "gzip",
}
DELAY = 12   # seconds between HTTP requests (Liquipedia rate limit)

# ---------------------------------------------------------------------------
# Event catalogue
# ---------------------------------------------------------------------------
# 2024: wikitext section-per-week pages (user-provided links, action=raw)
# Each entry: (event_id, csv_path, wiki_title, [sections], region, stage_label, season)
EVENTS_2024 = [
    ("owcs_2024_asia_s1_japan",
     DRAFTS_2024 / "draft_owcs_2024_asia_s1_japan.csv",
     "Overwatch_Champions_Series/2024/Asia/Stage_1/Japan/Group_Stage",
     [4, 5, 6, 7], "japan", "Stage 1", 2024),

    ("owcs_2024_asia_s1_korea",
     DRAFTS_2024 / "draft_owcs_2024_asia_s1_korea.csv",
     "Overwatch_Champions_Series/2024/Asia/Stage_1/Korea/Group_Stage",
     [4, 5, 6, 7], "korea", "Stage 1", 2024),

    ("owcs_2024_asia_s2_japan",
     DRAFTS_2024 / "draft_owcs_2024_asia_s2_japan.csv",
     "Overwatch_Champions_Series/2024/Asia/Stage_2/Japan/Group_Stage",
     [4, 5, 6], "japan", "Stage 2", 2024),

    ("owcs_2024_asia_s2_korea",
     DRAFTS_2024 / "draft_owcs_2024_asia_s2_korea.csv",
     "Overwatch_Champions_Series/2024/Asia/Stage_2/Korea/Group_Stage",
     [4, 5, 6], "korea", "Stage 2", 2024),
]

# 2025: full subpages (no section param — entire page is the group stage)
# Each entry: (event_id, csv_path, wiki_title, region, stage_label, season)
EVENTS_2025 = [
    # Japan – Regular Season
    ("owcs_2025_asia_s1_japan",
     DRAFTS_2025 / "owcs_2025_asia_s1_japan.csv",
     "Overwatch_Champions_Series/2025/Asia/Stage_1/Japan/Regular_Season",
     "japan", "Stage 1", 2025),
    ("owcs_2025_asia_s2_japan",
     DRAFTS_2025 / "owcs_2025_asia_s2_japan.csv",
     "Overwatch_Champions_Series/2025/Asia/Stage_2/Japan/Regular_Season",
     "japan", "Stage 2", 2025),
    ("owcs_2025_asia_s3_japan",
     DRAFTS_2025 / "owcs_2025_asia_s3_japan.csv",
     "Overwatch_Champions_Series/2025/Asia/Stage_3/Japan/Regular_Season",
     "japan", "Stage 3", 2025),

    # Korea – Regular Season (embedded in main page, section 8)
    ("owcs_2025_asia_s1_korea",
     DRAFTS_2025 / "owcs_2025_asia_s1_korea.csv",
     "Overwatch_Champions_Series/2025/Asia/Stage_1/Korea",
     "korea", "Stage 1", 2025, 8),
    ("owcs_2025_asia_s2_korea",
     DRAFTS_2025 / "owcs_2025_asia_s2_korea.csv",
     "Overwatch_Champions_Series/2025/Asia/Stage_2/Korea",
     "korea", "Stage 2", 2025, 8),
    ("owcs_2025_asia_s3_korea",
     DRAFTS_2025 / "owcs_2025_asia_s3_korea.csv",
     "Overwatch_Champions_Series/2025/Asia/Stage_3/Korea",
     "korea", "Stage 3", 2025, 8),

    # Pacific – Regular Season (embedded in main page, section 7; S1 has no group stage)
    ("owcs_2025_asia_s2_pacific",
     DRAFTS_2025 / "owcs_2025_asia_s2_pacific.csv",
     "Overwatch_Champions_Series/2025/Asia/Stage_2/Pacific",
     "pacific", "Stage 2", 2025, 7),
    ("owcs_2025_asia_s3_pacific",
     DRAFTS_2025 / "owcs_2025_asia_s3_pacific.csv",
     "Overwatch_Champions_Series/2025/Asia/Stage_3/Pacific",
     "pacific", "Stage 3", 2025, 7),

    # China – Regular Season
    ("owcs_2025_china_s1",
     DRAFTS_2025 / "owcs_2025_china_s1.csv",
     "Overwatch_Champions_Series/2025/China/Stage_1/Regular_Season",
     "china", "Stage 1", 2025),
    ("owcs_2025_china_s2",
     DRAFTS_2025 / "owcs_2025_china_s2.csv",
     "Overwatch_Champions_Series/2025/China/Stage_2/Regular_Season",
     "china", "Stage 2", 2025),
    ("owcs_2025_china_s3",
     DRAFTS_2025 / "owcs_2025_china_s3.csv",
     "Overwatch_Champions_Series/2025/China/Stage_3/Regular_Season",
     "china", "Stage 3", 2025),

    # EMEA – Regular Season
    ("owcs_2025_emea_s1",
     DRAFTS_2025 / "owcs_2025_emea_s1.csv",
     "Overwatch_Champions_Series/2025/EMEA/Stage_1/Regular_Season",
     "emea", "Stage 1", 2025),
    ("owcs_2025_emea_s2",
     DRAFTS_2025 / "owcs_2025_emea_s2.csv",
     "Overwatch_Champions_Series/2025/EMEA/Stage_2/Regular_Season",
     "emea", "Stage 2", 2025),
    ("owcs_2025_emea_s3",
     DRAFTS_2025 / "owcs_2025_emea_s3.csv",
     "Overwatch_Champions_Series/2025/EMEA/Stage_3/Regular_Season",
     "emea", "Stage 3", 2025),

    # NA – Regular Season
    ("owcs_2025_na_s1",
     DRAFTS_2025 / "owcs_2025_na_s1.csv",
     "Overwatch_Champions_Series/2025/NA/Stage_1/Regular_Season",
     "na", "Stage 1", 2025),
    ("owcs_2025_na_s2",
     DRAFTS_2025 / "owcs_2025_na_s2.csv",
     "Overwatch_Champions_Series/2025/NA/Stage_2/Regular_Season",
     "na", "Stage 2", 2025),
    ("owcs_2025_na_s3",
     DRAFTS_2025 / "owcs_2025_na_s3.csv",
     "Overwatch_Champions_Series/2025/NA/Stage_3/Regular_Season",
     "na", "Stage 3", 2025),

    # Midseason Championship – Group Stage
    ("owcs_2025_midseason",
     DRAFTS_2025 / "owcs_2025_midseason.csv",
     "Overwatch_Champions_Series/2025/Midseason_Championship/Group_Stage",
     "international", "Midseason Championship", 2025),
]

FIELDNAMES = [
    "event_id", "event_region", "season_year", "stage_label",
    "week_label", "day_label", "match_date",
    "match_order", "game_number",
    "team_a", "team_b", "winner", "loser",
    "map_name", "map_mode", "series_format",
    "source_url", "source_note",
]

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def fetch_raw(title: str, section: int | None = None) -> str:
    params: dict = {"title": title, "action": "raw"}
    if section is not None:
        params["section"] = section
    time.sleep(DELAY)
    for attempt in range(3):
        try:
            r = requests.get(LIQUIPEDIA_RAW, params=params,
                             headers=HEADERS, timeout=30)
            if r.status_code == 404:
                return ""
            r.raise_for_status()
            return r.text
        except requests.RequestException as exc:
            wait = DELAY * (2 ** attempt)
            print(f"    [retry {attempt+1}] {exc} — waiting {wait}s")
            time.sleep(wait)
    return ""

# ---------------------------------------------------------------------------
# Wikitext parsing helpers
# ---------------------------------------------------------------------------

def extract_param(text: str, key: str) -> str:
    """Extract value of |key=... up to next | or end of template."""
    m = re.search(rf'\|{re.escape(key)}=([^|{{}}]*)', text)
    return m.group(1).strip() if m else ""

def parse_team(opponent_block: str) -> str:
    """{{TeamOpponent|NAME|...}} → NAME"""
    m = re.search(r'\{\{TeamOpponent\|([^|}]+)', opponent_block)
    return m.group(1).strip() if m else ""

def parse_date(raw: str) -> str:
    """'February  26, 2024 - 17:00 {{Abbr/KST}}' → '2024-02-26'"""
    cleaned = re.sub(r'\{\{[^}]+\}\}', '', raw).strip()
    cleaned = re.sub(r'\s*[-–]\s*[\d:]+\s*$', '', cleaned).strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)
    for fmt in ("%B %d, %Y", "%B%d, %Y"):
        try:
            return datetime.strptime(cleaned, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return cleaned

def parse_matches_from_wikitext(wikitext: str) -> list[dict]:
    """
    Parse all {{Match ...}} blocks from raw Liquipedia wikitext.
    Returns list of match dicts with keys:
      week_label, day_label, match_date, match_num,
      team_a, team_b, bestof, maps[{map_name, map_mode, winner_side}]
    """
    results = []
    current_week = "Week 1"
    current_day  = ""

    # Normalise line endings
    text = wikitext.replace("\r\n", "\n").replace("\r", "\n")

    # Track week headers: ===Week N=== or |title=Week N
    # We scan line by line for headers, then find Match blocks
    # Build a position → week map
    week_positions: list[tuple[int, str]] = []
    for m in re.finditer(
            r'(?:={2,3}\s*(?:\{\{HiddenSort\|)?(Week\s*\d+)(?:\}\})?\s*={2,3}'
            r'|\|title=(Week\s*\d+))',
            text, re.IGNORECASE):
        label = (m.group(1) or m.group(2)).strip()
        week_positions.append((m.start(), label))

    # Also look for Mheader lines for day info: |M1header=February 26
    day_positions: list[tuple[int, str]] = []
    for m in re.finditer(r'\|M\d+header=([^\n|]+)', text):
        day_positions.append((m.start(), m.group(1).strip()))

    def week_at(pos: int) -> str:
        label = "Week 1"
        for p, lbl in week_positions:
            if p <= pos:
                label = lbl
        return label

    def day_at(pos: int) -> str:
        label = ""
        for p, lbl in day_positions:
            if p <= pos:
                label = lbl
        return label

    # Extract each |MN={{Match ... }} or |RnMn={{Match ... }} block
    # Strategy: find all match-block markers, collect text until next marker or end
    match_starts = list(re.finditer(r'\|(?:R\d+)?M(\d+)=\{\{Match', text))

    match_num_global = 0
    for i, ms in enumerate(match_starts):
        match_num_global += 1
        start = ms.start()
        end   = match_starts[i + 1].start() if i + 1 < len(match_starts) else len(text)
        block = text[start:end]

        wk  = week_at(start)
        day = day_at(start)

        # date
        date_m = re.search(r'\|date=([^\n]+)', block)
        raw_date = date_m.group(1) if date_m else ""
        match_date = parse_date(raw_date)

        # bestof
        bo_m = re.search(r'\|bestof=(\d+)', block)
        bestof = f"bo{bo_m.group(1)}" if bo_m else "bo5"

        # teams
        opp1 = re.search(r'\|opponent1=(\{\{TeamOpponent\|[^}]+\}\})', block)
        opp2 = re.search(r'\|opponent2=(\{\{TeamOpponent\|[^}]+\}\})', block)
        team_a = parse_team(opp1.group(1)) if opp1 else ""
        team_b = parse_team(opp2.group(1)) if opp2 else ""
        if not team_a or not team_b:
            continue

        # maps
        maps = []
        for map_m in re.finditer(
                r'\|map(\d+)=\{\{Map\|map=([^|]*)\|mode=([^|]*)\|score1=[^|]*\|score2=[^|]*\|winner=(\d*)',
                block):
            map_name = map_m.group(2).strip()
            map_mode = map_m.group(3).strip()
            winner_n = map_m.group(4).strip()
            if not map_name or winner_n not in ("1", "2"):
                continue
            maps.append({
                "map_name":    map_name,
                "map_mode":    map_mode,
                "winner_side": winner_n,   # "1"=team_a, "2"=team_b
            })

        if not maps:
            continue

        results.append({
            "week_label":  wk,
            "day_label":   day if day else "[MANUAL]",
            "match_date":  match_date if match_date else "[MANUAL]",
            "match_num":   match_num_global,
            "team_a":      team_a,
            "team_b":      team_b,
            "bestof":      bestof,
            "maps":        maps,
        })

    return results

# ---------------------------------------------------------------------------
# CSV row builder
# ---------------------------------------------------------------------------

def matches_to_rows(
    matches:      list[dict],
    event_id:     str,
    event_region: str,
    season_year:  int,
    stage_label:  str,
    source_url:   str,
    match_order_start: int = 1,
) -> list[dict]:
    rows = []
    for mo, match in enumerate(matches, start=match_order_start):
        team_a = match["team_a"]
        team_b = match["team_b"]
        for gn, mp in enumerate(match["maps"], start=1):
            winner = team_a if mp["winner_side"] == "1" else team_b
            loser  = team_b if mp["winner_side"] == "1" else team_a
            rows.append({
                "event_id":     event_id,
                "event_region": event_region,
                "season_year":  season_year,
                "stage_label":  stage_label,
                "week_label":   match["week_label"],
                "day_label":    match["day_label"],
                "match_date":   match["match_date"],
                "match_order":  mo,
                "game_number":  gn,
                "team_a":       team_a,
                "team_b":       team_b,
                "winner":       winner,
                "loser":        loser,
                "map_name":     mp["map_name"],
                "map_mode":     mp["map_mode"],
                "series_format":match["bestof"],
                "source_url":   source_url,
                "source_note":  "group_stage_scrape",
            })
    return rows

# ---------------------------------------------------------------------------
# Prepend to existing CSV
# ---------------------------------------------------------------------------

def prepend_to_csv(csv_path: Path, new_rows: list[dict]) -> None:
    """Insert new_rows at the top of csv_path, renumbering match_order of
    existing rows so they continue after the new group-stage rows."""
    if not new_rows:
        return

    gs_match_count = max(r["match_order"] for r in new_rows)

    existing: list[dict] = []
    if csv_path.exists():
        with csv_path.open(encoding="utf-8", newline="") as f:
            existing = list(csv.DictReader(f))
        # shift existing match_order up
        for row in existing:
            try:
                row["match_order"] = int(row["match_order"]) + gs_match_count
            except (ValueError, KeyError):
                pass

    all_rows = new_rows + existing
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(all_rows)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def process_event_2024(event_id, csv_path, wiki_title, sections,
                       region, stage_label, season):
    print(f"\n{'='*60}")
    print(f"[2024] {event_id}")
    all_matches: list[dict] = []
    for sec in sections:
        url = (f"https://liquipedia.net/overwatch/index.php"
               f"?title={wiki_title}&action=raw&section={sec}")
        print(f"  Fetching section {sec}… ", end="", flush=True)
        wikitext = fetch_raw(wiki_title, section=sec)
        if not wikitext:
            print("EMPTY/404 — skipping")
            continue
        matches = parse_matches_from_wikitext(wikitext)
        print(f"{len(matches)} matches parsed")
        all_matches.extend(matches)

    if not all_matches:
        print("  No matches found — skipping CSV update")
        return

    rows = matches_to_rows(all_matches, event_id, region, season,
                           stage_label,
                           f"https://liquipedia.net/overwatch/index.php?title={wiki_title}")
    prepend_to_csv(csv_path, rows)
    print(f"  → {len(all_matches)} matches / {len(rows)} map rows prepended to {csv_path.name}")


def process_event_2025(event_id, csv_path, wiki_title, region, stage_label, season, section=None):
    print(f"\n{'='*60}")
    print(f"[2025] {event_id}")
    sec_label = f" (section {section})" if section else ""
    print(f"  Fetching{sec_label}… ", end="", flush=True)
    wikitext = fetch_raw(wiki_title, section=section)
    if not wikitext:
        print("EMPTY/404 — skipping")
        return
    matches = parse_matches_from_wikitext(wikitext)
    print(f"{len(matches)} matches parsed")

    if not matches:
        print("  No matches found — skipping CSV update")
        return

    rows = matches_to_rows(matches, event_id, region, season,
                           stage_label,
                           f"https://liquipedia.net/overwatch/index.php?title={wiki_title}")
    prepend_to_csv(csv_path, rows)
    print(f"  → {len(matches)} matches / {len(rows)} map rows prepended to {csv_path.name}")


if __name__ == "__main__":
    print("=== Group Stage Scraper ===")
    print(f"2024 events: {len(EVENTS_2024)}")
    print(f"2025 events: {len(EVENTS_2025)}")

    for args in EVENTS_2024:
        process_event_2024(*args)

    for args in EVENTS_2025:
        # args may have 6 or 7 elements (7th = section number for embedded pages)
        process_event_2025(*args)

    print("\n\n=== Done ===")
