"""
Liquipedia OWCS match data scraper.

Fetches a Liquipedia tournament page via the MediaWiki API, parses the wikitext
to extract match and map results, and outputs a CSV draft for review.

Usage:
    python liquipedia_scraper.py <URL> --region <region> --event-id <id> --season <year> --stage <label>

Example:
    python liquipedia_scraper.py \\
        "https://liquipedia.net/overwatch/Overwatch_Champions_Series/2024/Asia/Stage_1/Korea" \\
        --region korea \\
        --event-id owcs_2024_korea_stage_1 \\
        --season 2024 \\
        --stage "Stage 1"

Valid regions: korea, na, emea, japan, pacific, international
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urlencode

ROOT = Path(__file__).resolve().parent

try:
    import requests as _requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

# Liquipedia rate limit: respect their guidelines (min 2s, use 10s to be safe)
REQUEST_DELAY = 10.0
USER_AGENT = "OWCSEloRatingTool/1.0 (personal research project)"

VALID_REGIONS = {"korea", "na", "emea", "japan", "pacific", "international"}

MAP_MODE_MAP = {
    "control": "Control",
    "push": "Push",
    "escort": "Escort",
    "payload": "Escort",
    "hybrid": "Hybrid",
    "flashpoint": "Flashpoint",
    "clash": "Clash",
}

OUTPUT_COLUMNS = [
    "event_id", "event_region", "season_year", "stage_label", "week_label",
    "day_label", "match_date", "match_order", "game_number",
    "team_a", "team_b", "winner", "loser",
    "map_name", "map_mode", "series_format",
    "source_url", "source_note",
]


# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------

def fetch_wikitext(page_name: str) -> str:
    """Fetch wikitext for a Liquipedia page via the MediaWiki API."""
    api_base = "https://liquipedia.net/overwatch/api.php"
    api_params = {
        "action": "parse",
        "page": page_name,
        "prop": "wikitext",
        "format": "json",
    }
    print(f"  Fetching: {api_base}?page={page_name}")
    time.sleep(REQUEST_DELAY)

    if _HAS_REQUESTS:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        last_err = None
        for attempt in range(1, 5):
            try:
                r = _requests.get(
                    api_base,
                    params=api_params,
                    headers={"User-Agent": USER_AGENT},
                    timeout=30,
                    verify=False,
                )
                # Handle rate limiting (HTTP 429)
                if r.status_code == 429:
                    retry_after = int(r.headers.get("Retry-After", 60))
                    retry_after = max(retry_after, 60)  # at least 60s
                    print(f"  [429 rate limited] waiting {retry_after}s before retry {attempt}/4...")
                    time.sleep(retry_after)
                    last_err = RuntimeError(f"HTTP 429 rate limited")
                    continue
                data = r.json()
                break
            except Exception as e:
                last_err = e
                wait = REQUEST_DELAY * attempt
                print(f"  [retry {attempt}/4] connection error, waiting {wait:.0f}s...")
                time.sleep(wait)
        else:
            raise last_err
    else:
        import urllib.request
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        query = urlencode(api_params)
        api_url = f"{api_base}?{query}"
        req = urllib.request.Request(api_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))

    if "error" in data:
        raise RuntimeError(f"Liquipedia API error: {data['error']}")
    return data["parse"]["wikitext"]["*"]


def url_to_page_name(url: str) -> str:
    """Convert a Liquipedia URL to a MediaWiki page name."""
    parsed = urlparse(url)
    path = parsed.path
    if path.startswith("/overwatch/"):
        path = path[len("/overwatch/"):]
    return path.strip("/")


# ---------------------------------------------------------------------------
# Wikitext parsing utilities
# ---------------------------------------------------------------------------

def extract_template_blocks(text: str, open_pattern: str) -> list[str]:
    """
    Extract all {{open_pattern...}} blocks, respecting nested {{ }}.
    open_pattern should be the text immediately after '{{', e.g. 'Match'.
    """
    search = "{{" + open_pattern
    blocks: list[str] = []
    start = 0
    while True:
        idx = text.find(search, start)
        if idx == -1:
            break
        depth = 0
        i = idx
        while i < len(text):
            if text[i:i+2] == "{{":
                depth += 1
                i += 2
            elif text[i:i+2] == "}}":
                depth -= 1
                i += 2
                if depth == 0:
                    blocks.append(text[idx:i])
                    break
            else:
                i += 1
        start = idx + 1
    return blocks


def get_param(block: str, key: str) -> str:
    """
    Extract |key=value from a template block (handles values with nested templates).
    Returns the raw value string (possibly multiline), stripped.
    """
    pattern = re.compile(r"\|" + re.escape(key) + r"\s*=\s*((?:[^|{}]|\{\{[^{}]*\}\})*)", re.DOTALL)
    m = pattern.search(block)
    if not m:
        return ""
    return m.group(1).strip()


def extract_team_opponent(block: str) -> str:
    """Extract team name from {{TeamOpponent|Name}} template."""
    m = re.search(r"\{\{TeamOpponent\|([^|}\n]+)", block, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return ""


def clean_wiki_text(raw: str) -> str:
    """Remove wiki links and template markup, returning plain text."""
    # [[Page|Display]] → Display
    raw = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", raw)
    # [[Page]] → Page
    raw = re.sub(r"\[\[([^\]]*)\]\]", r"\1", raw)
    # {{...}} → ""
    raw = re.sub(r"\{\{[^{}]*\}\}", "", raw)
    return raw.strip()


def normalize_map_mode(raw: str) -> str:
    key = raw.strip().lower()
    return MAP_MODE_MAP.get(key, raw.strip() if raw.strip() else "[MANUAL]")


def parse_date(raw: str) -> str:
    """Parse a date string like 'March 29, 2024 - 18:30 {{Abbr/KST}}' to YYYY-MM-DD."""
    raw = re.sub(r"\{\{[^{}]*\}\}", "", raw).strip()
    raw = raw.split("-")[0].strip()
    raw = re.sub(r"\s+", " ", raw)
    # Try YYYY-MM-DD first
    m = re.search(r"\d{4}-\d{2}-\d{2}", raw)
    if m:
        return m.group(0)
    # Try "Month DD, YYYY"
    for fmt in ("%B %d, %Y", "%B %d %Y", "%d %B %Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    # Try "Month DD" with year from context (won't have year → [MANUAL])
    return "[MANUAL]" if raw else "[MANUAL]"


# ---------------------------------------------------------------------------
# Match parsing
# ---------------------------------------------------------------------------

def parse_match_block(match_block: str) -> dict:
    """
    Parse a {{Match...}} block.
    Returns a dict with: team_a, team_b, match_date, series_format, maps.
    maps is a list of dicts: {game_number, map_name, map_mode, winner_idx (1 or 2)}.
    """
    # Team names via {{TeamOpponent|...}}
    opp1_block = get_param(match_block, "opponent1")
    opp2_block = get_param(match_block, "opponent2")
    team_a = extract_team_opponent(opp1_block) or clean_wiki_text(opp1_block) or "[MANUAL]"
    team_b = extract_team_opponent(opp2_block) or clean_wiki_text(opp2_block) or "[MANUAL]"

    date_raw = get_param(match_block, "date")
    match_date = parse_date(date_raw)

    bestof_raw = get_param(match_block, "bestof").strip()
    # series_format resolved after we count maps (see below)
    explicit_format = f"bo{bestof_raw}" if bestof_raw.isdigit() else None

    # Find all {{Map...}} blocks
    map_blocks = extract_template_blocks(match_block, "Map|")

    maps: list[dict] = []
    for game_number, map_block in enumerate(map_blocks, start=1):
        map_name = clean_wiki_text(get_param(map_block, "map")) or "[MANUAL]"
        map_mode_raw = get_param(map_block, "mode")
        map_mode = normalize_map_mode(map_mode_raw)
        winner_param = get_param(map_block, "winner").strip()

        if winner_param.lower() in ("skip", ""):
            continue

        if winner_param in ("1", "2"):
            winner_idx = int(winner_param)
        else:
            # Try to infer from scores
            s1_raw = get_param(map_block, "score1").strip()
            s2_raw = get_param(map_block, "score2").strip()
            try:
                s1 = float(s1_raw)
                s2 = float(s2_raw)
                winner_idx = 1 if s1 > s2 else (2 if s2 > s1 else 0)
            except ValueError:
                winner_idx = 0

        maps.append({
            "game_number": game_number,
            "map_name": map_name,
            "map_mode": map_mode,
            "winner_idx": winner_idx,
        })

    # Infer series_format from map count if not explicit
    if explicit_format:
        series_format = explicit_format
    elif maps:
        map_count = len(maps)
        if map_count <= 5:
            series_format = "bo5"
        elif map_count <= 7:
            series_format = "bo7"
        else:
            series_format = "[MANUAL]"
    else:
        series_format = "[MANUAL]"

    return {
        "team_a": team_a,
        "team_b": team_b,
        "match_date": match_date,
        "series_format": series_format,
        "maps": maps,
    }


def match_to_rows(
    parsed: dict,
    match_order: int,
    event_id: str,
    event_region: str,
    season_year: int,
    stage_label: str,
    week_label: str,
    source_url: str,
    day_label: str = "[MANUAL]",
) -> list[dict]:
    """Convert a parsed match dict to a list of CSV row dicts (one per map)."""
    rows = []
    team_a = parsed["team_a"]
    team_b = parsed["team_b"]

    for m in parsed["maps"]:
        wi = m["winner_idx"]
        if wi == 1:
            winner, loser = team_a, team_b
        elif wi == 2:
            winner, loser = team_b, team_a
        else:
            winner = loser = "[MANUAL]"

        rows.append({
            "event_id": event_id,
            "event_region": event_region,
            "season_year": season_year,
            "stage_label": stage_label,
            "week_label": week_label,
            "day_label": day_label,
            "match_date": parsed["match_date"],
            "match_order": match_order,
            "game_number": m["game_number"],
            "team_a": team_a,
            "team_b": team_b,
            "winner": winner,
            "loser": loser,
            "map_name": m["map_name"],
            "map_mode": m["map_mode"],
            "series_format": parsed["series_format"],
            "source_url": source_url,
            "source_note": "liquipedia_scraper_draft",
        })

    # If no maps extracted, add series-level placeholder row
    if not rows:
        rows.append({
            "event_id": event_id,
            "event_region": event_region,
            "season_year": season_year,
            "stage_label": stage_label,
            "week_label": week_label,
            "day_label": day_label,
            "match_date": parsed["match_date"],
            "match_order": match_order,
            "game_number": 1,
            "team_a": team_a,
            "team_b": team_b,
            "winner": "[MANUAL]",
            "loser": "[MANUAL]",
            "map_name": "[MANUAL]",
            "map_mode": "[MANUAL]",
            "series_format": parsed["series_format"],
            "source_url": source_url,
            "source_note": "liquipedia_scraper_draft_NO_MAP_DATA",
        })

    return rows


# ---------------------------------------------------------------------------
# Main scrape logic
# ---------------------------------------------------------------------------

def build_day_week_labels(
    match_blocks: list[str],
) -> dict[int, tuple[str, str]]:
    """
    Build a mapping from 1-based match_order → (day_label, week_label).

    Uses the match_date from each block to group matches into days and weeks.
    - day_label: "Day 1", "Day 2", ... based on unique dates in order
    - week_label: "Week 1", "Week 2", ... new week when gap > 5 days between dates
    """
    from datetime import date as _date

    # Get match date for each block
    match_dates: list[str] = []
    for block in match_blocks:
        d = parse_date(get_param(block, "date"))
        match_dates.append(d)

    # Collect unique dates in order of first appearance, then sort chronologically
    seen: set[str] = set()
    unique_dates: list[str] = []
    for d in match_dates:
        if d != "[MANUAL]" and d not in seen:
            unique_dates.append(d)
            seen.add(d)
    unique_dates.sort()  # sort YYYY-MM-DD strings chronologically

    # Assign Day N labels
    date_to_day: dict[str, str] = {
        d: f"Day {i}" for i, d in enumerate(unique_dates, start=1)
    }

    # Assign Week N labels: new week when gap > 5 days
    week_num = 1
    date_to_week: dict[str, str] = {}
    prev_date_obj: _date | None = None
    for d in unique_dates:
        try:
            cur = _date.fromisoformat(d)
        except ValueError:
            date_to_week[d] = "[MANUAL]"
            continue
        if prev_date_obj is not None and (cur - prev_date_obj).days >= 4:
            week_num += 1
        date_to_week[d] = f"Week {week_num}"
        prev_date_obj = cur

    result: dict[int, tuple[str, str]] = {}
    for idx, d in enumerate(match_dates, start=1):
        result[idx] = (
            date_to_day.get(d, "[MANUAL]"),
            date_to_week.get(d, "[MANUAL]"),
        )
    return result


def scrape_page(
    url: str,
    region: str,
    event_id: str,
    season_year: int,
    stage_label: str,
    week_label: str,
) -> list[dict]:
    """Fetch a Liquipedia page and return all map-level result rows."""
    page_name = url_to_page_name(url)
    print(f"  Page: {page_name}")
    wikitext = fetch_wikitext(page_name)

    # Find all {{Match blocks
    match_blocks = extract_template_blocks(wikitext, "Match\n") + \
                   extract_template_blocks(wikitext, "Match\r\n") + \
                   extract_template_blocks(wikitext, "Match ")

    seen: set[int] = set()
    unique_blocks: list[str] = []
    for b in match_blocks:
        h = hash(b)
        if h not in seen:
            seen.add(h)
            unique_blocks.append(b)
    match_blocks = unique_blocks

    print(f"  Found {len(match_blocks)} match block(s)")

    # Build day/week label mapping from match dates
    day_week_map = build_day_week_labels(match_blocks)

    all_rows: list[dict] = []

    for match_order, match_block in enumerate(match_blocks, start=1):
        parsed = parse_match_block(match_block)
        auto_day, auto_week = day_week_map.get(match_order, ("[MANUAL]", "[MANUAL]"))
        # --week flag overrides auto-detected week if explicitly provided
        resolved_week = week_label if week_label != "[MANUAL]" else auto_week

        rows = match_to_rows(
            parsed=parsed,
            match_order=match_order,
            event_id=event_id,
            event_region=region,
            season_year=season_year,
            stage_label=stage_label,
            week_label=resolved_week,
            source_url=url,
            day_label=auto_day,
        )
        all_rows.extend(rows)

        team_a = parsed["team_a"]
        team_b = parsed["team_b"]
        map_count = len([r for r in rows if r["map_name"] != "[MANUAL]"])
        print(f"    [{match_order:02d}] {team_a} vs {team_b} — {map_count} maps | {auto_day} / {resolved_week}")

    return all_rows


def write_draft_csv(rows: list[dict], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape OWCS match data from Liquipedia and output a CSV draft for review.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("url", help="Liquipedia tournament page URL")
    parser.add_argument(
        "--region", required=True, choices=sorted(VALID_REGIONS),
        help="Region (korea/na/emea/japan/pacific/international)",
    )
    parser.add_argument("--event-id", required=True, help="Event ID, e.g. owcs_2024_korea_stage_1")
    parser.add_argument("--season", required=True, type=int, help="Season year, e.g. 2024")
    parser.add_argument("--stage", required=True, help="Stage label, e.g. 'Stage 1'")
    parser.add_argument("--week", default="[MANUAL]", help="Week label (optional)")
    parser.add_argument("--output", default=None, help="Output CSV path (default: auto-named)")
    args = parser.parse_args()

    if not _HAS_REQUESTS:
        print("[WARN] 'requests' not installed. Falling back to urllib (may fail on SSL).")
        print("       Install with: pip install requests")

    output_path = (
        Path(args.output)
        if args.output
        else ROOT / f"draft_{args.event_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )

    print(f"\n=== OWCS Liquipedia Scraper ===")
    print(f"URL:      {args.url}")
    print(f"Region:   {args.region}")
    print(f"Event ID: {args.event_id}")
    print(f"Season:   {args.season}")
    print(f"Stage:    {args.stage}")
    print(f"Output:   {output_path}\n")

    try:
        rows = scrape_page(
            url=args.url,
            region=args.region,
            event_id=args.event_id,
            season_year=args.season,
            stage_label=args.stage,
            week_label=args.week,
        )
    except Exception as e:
        print(f"\n[ERROR] Failed to scrape: {e}")
        sys.exit(1)

    if not rows:
        print("\n[ERROR] No match data found. The page may use an unsupported template format.")
        page_name = url_to_page_name(args.url)
        print(f"  Check wikitext at: https://liquipedia.net/overwatch/index.php?title={page_name}&action=edit")
        sys.exit(1)

    write_draft_csv(rows, output_path)

    manual_count = sum(1 for r in rows if any(str(v) == "[MANUAL]" for v in r.values()))
    no_map_data = sum(1 for r in rows if "NO_MAP_DATA" in str(r.get("source_note", "")))

    print(f"\n=== Summary ===")
    print(f"  Total map rows:          {len(rows)}")
    print(f"  Rows with [MANUAL] tags: {manual_count}")
    if no_map_data:
        print(f"  Matches without map data:{no_map_data}  ← these need manual map-by-map entry")
    print(f"  Output: {output_path}")
    print(f"\nReview the draft CSV and fill in [MANUAL] fields before merging into the main dataset.")


if __name__ == "__main__":
    main()
