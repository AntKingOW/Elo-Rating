"""
scrape_stage1_playoffs_2026.py

Fetches OWCS 2026 Stage 1 regional playoff results from Liquipedia main pages
and writes them as separate draft CSVs under drafts/2026/.

This keeps the existing regular-season files intact while extending the 2026
pipeline with missing playoff stages.
"""

from __future__ import annotations

import csv
from pathlib import Path

from liquipedia_scraper import OUTPUT_COLUMNS, scrape_page, url_to_page_name
from scrape_group_stages import fetch_raw, matches_to_rows, parse_matches_from_wikitext

ROOT = Path(__file__).resolve().parent
DRAFTS_2026 = ROOT / "drafts" / "2026"
DRAFTS_2026.mkdir(parents=True, exist_ok=True)

EVENTS_2026_PLAYOFFS = [
    {
        "event_id": "owcs_2026_asia_s1_japan_playoffs",
        "output": DRAFTS_2026 / "owcs_2026_asia_s1_japan_playoffs.csv",
        "url": "https://liquipedia.net/overwatch/Overwatch_Champions_Series/2026/Asia/Stage_1/Japan",
        "region": "japan",
        "stage_label": "Stage 1",
        "week_label": "Regional Playoffs",
        "playoff_start": "2026-04-13",
    },
    {
        "event_id": "owcs_2026_asia_s1_pacific_playoffs",
        "output": DRAFTS_2026 / "owcs_2026_asia_s1_pacific_playoffs.csv",
        "url": "https://liquipedia.net/overwatch/Overwatch_Champions_Series/2026/Asia/Stage_1/Pacific",
        "region": "pacific",
        "stage_label": "Stage 1",
        "week_label": "Regional Playoffs",
        "playoff_start": "2026-04-30",
    },
    {
        "event_id": "owcs_2026_china_s1_playoffs",
        "output": DRAFTS_2026 / "owcs_2026_china_s1_playoffs.csv",
        "url": "https://liquipedia.net/overwatch/Overwatch_Champions_Series/2026/China/Stage_1",
        "region": "china",
        "stage_label": "Stage 1",
        "week_label": "Regional Playoffs",
        "playoff_start": "2026-04-25",
    },
    {
        "event_id": "owcs_2026_emea_s1_playoffs",
        "output": DRAFTS_2026 / "owcs_2026_emea_s1_playoffs.csv",
        "url": "https://liquipedia.net/overwatch/Overwatch_Champions_Series/2026/EMEA/Stage_1",
        "region": "emea",
        "stage_label": "Stage 1",
        "week_label": "Regional Playoffs",
        "playoff_start": "2026-04-10",
    },
    {
        "event_id": "owcs_2026_na_s1_playoffs",
        "output": DRAFTS_2026 / "owcs_2026_na_s1_playoffs.csv",
        "url": "https://liquipedia.net/overwatch/Overwatch_Champions_Series/2026/NA/Stage_1",
        "region": "na",
        "stage_label": "Stage 1",
        "week_label": "Regional Playoffs",
        "playoff_start": "2026-04-10",
    },
]


def write_csv(csv_path: Path, rows: list[dict]) -> None:
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def fallback_scrape_event(config: dict) -> list[dict]:
    wiki_title = url_to_page_name(config["url"])
    wikitext = fetch_raw(wiki_title)
    if not wikitext:
        raise RuntimeError(f"raw fallback returned empty wikitext for {wiki_title}")

    matches = parse_matches_from_wikitext(wikitext)
    rows = matches_to_rows(
        matches,
        config["event_id"],
        config["region"],
        2026,
        config["stage_label"],
        config["url"],
    )
    for row in rows:
        row["week_label"] = config["week_label"]
        row["source_note"] = "playoff_raw_fallback"
    return rows


def scrape_event(config: dict) -> None:
    print(f"\n{'=' * 60}")
    print(f"[2026 Playoffs] {config['event_id']}")
    print(f"  URL   : {config['url']}")
    print(f"  Start : {config['playoff_start']}")

    try:
        rows = scrape_page(
            url=config["url"],
            region=config["region"],
            event_id=config["event_id"],
            season_year=2026,
            stage_label=config["stage_label"],
            week_label=config["week_label"],
        )
        if rows and all(row["match_date"] in {"", "[MANUAL]"} for row in rows):
            print("  API scrape returned no usable dates, switching to raw fallback")
            rows = fallback_scrape_event(config)
    except Exception as exc:
        print(f"  API scrape failed, trying raw fallback: {exc}")
        rows = fallback_scrape_event(config)
    rows = [row for row in rows if row["match_date"] >= config["playoff_start"]]
    print(f"  Rows kept after playoff-date filter: {len(rows)}")

    if not rows:
        print("  No playoff rows found - skipping write")
        return

    write_csv(config["output"], rows)
    print(f"  -> written to {config['output'].name}")


def main() -> None:
    print("=== 2026 Stage 1 Regional Playoff Scraper ===")
    print(f"Events: {len(EVENTS_2026_PLAYOFFS)}")
    print(f"Output: {DRAFTS_2026}")
    for config in EVENTS_2026_PLAYOFFS:
        scrape_event(config)
    print("\n=== Done ===")


if __name__ == "__main__":
    main()
