"""
Batch scraper for all remaining OWCS 2025 events.
Runs liquipedia_scraper.py for each event in sequence.
Already-scraped events (Korea S1) are skipped.
"""

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DRAFTS = ROOT / "drafts" / "2025"
DRAFTS.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://liquipedia.net/overwatch/Overwatch_Champions_Series"

EVENTS = [
    # (event_id, liquipedia_path, region, stage_label)
    # Stage 1
    # Korea S1 already done - skip
    ("owcs_2025_asia_s1_japan",     "/2025/Asia/Stage_1/Japan",                        "japan",         "Stage 1"),
    ("owcs_2025_asia_s1_pacific",   "/2025/Asia/Stage_1/Pacific",                      "pacific",       "Stage 1"),
    ("owcs_2025_na_s1",             "/2025/NA/Stage_1",                                "na",            "Stage 1"),
    ("owcs_2025_emea_s1",           "/2025/EMEA/Stage_1",                              "emea",          "Stage 1"),
    ("owcs_2025_china_s1",          "/2025/China/Stage_1",                             "china",         "Stage 1"),
    ("owcs_2025_asia_s1_main",      "/2025/Asia/Stage_1",                              "international", "Stage 1 Main"),
    # Champions Clash
    ("owcs_2025_champions_clash",   "/2025/Champions_Clash",                           "international", "Champions Clash"),
    # Stage 2
    ("owcs_2025_asia_s2_korea",     "/2025/Asia/Stage_2/Korea",                        "korea",         "Stage 2"),
    ("owcs_2025_asia_s2_japan",     "/2025/Asia/Stage_2/Japan",                        "japan",         "Stage 2"),
    ("owcs_2025_asia_s2_pacific",   "/2025/Asia/Stage_2/Pacific",                      "pacific",       "Stage 2"),
    ("owcs_2025_na_s2",             "/2025/NA/Stage_2",                                "na",            "Stage 2"),
    ("owcs_2025_emea_s2",           "/2025/EMEA/Stage_2",                              "emea",          "Stage 2"),
    ("owcs_2025_china_s2",          "/2025/China/Stage_2",                             "china",         "Stage 2"),
    # Midseason Championship
    ("owcs_2025_midseason",         "/2025/Midseason_Championship",                    "international", "Midseason Championship"),
    # Stage 3
    ("owcs_2025_asia_s3_korea",     "/2025/Asia/Stage_3/Korea",                        "korea",         "Stage 3"),
    ("owcs_2025_asia_s3_japan",     "/2025/Asia/Stage_3/Japan",                        "japan",         "Stage 3"),
    ("owcs_2025_asia_s3_pacific",   "/2025/Asia/Stage_3/Pacific",                      "pacific",       "Stage 3"),
    ("owcs_2025_na_s3",             "/2025/NA/Stage_3",                                "na",            "Stage 3"),
    ("owcs_2025_emea_s3",           "/2025/EMEA/Stage_3",                              "emea",          "Stage 3"),
    ("owcs_2025_china_s3",          "/2025/China/Stage_3",                             "china",         "Stage 3"),
    ("owcs_2025_apac_championship", "/2025/Asia/Stage_3/Championship/APAC",            "international", "APAC Championship"),
    ("owcs_2025_korea_road_to_wf",  "/2025/Asia/Stage_3/Championship/Korea",           "international", "Korea Road to WF"),
    # World Finals
    ("owcs_2025_world_finals",      "/2025/World_Finals",                              "international", "World Finals"),
]


def run_event(event_id: str, path: str, region: str, stage: str) -> bool:
    out_file = DRAFTS / f"{event_id}.csv"
    if out_file.exists() and out_file.stat().st_size > 0:
        print(f"[SKIP] {event_id} — already exists ({out_file.stat().st_size} bytes)")
        return True

    url = BASE_URL + path
    cmd = [
        sys.executable,
        str(ROOT / "liquipedia_scraper.py"),
        url,
        "--region", region,
        "--event-id", event_id,
        "--season", "2025",
        "--stage", stage,
        "--output", str(out_file),
    ]
    print(f"\n{'='*60}")
    print(f"[SCRAPE] {event_id}")
    print(f"  URL   : {url}")
    print(f"  Region: {region}")
    print(f"  Output: {out_file}")
    print(f"{'='*60}")

    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        print(f"[ERROR] {event_id} exited with code {result.returncode}")
        return False
    return True


def main():
    total = len(EVENTS)
    ok = 0
    fail = 0
    for i, (event_id, path, region, stage) in enumerate(EVENTS, 1):
        print(f"\n[{i}/{total}] Starting {event_id}")
        success = run_event(event_id, path, region, stage)
        if success:
            ok += 1
        else:
            fail += 1
        # Brief pause between events (scraper already rate-limits internally)
        if i < total:
            print(f"  → Waiting 5s before next event...")
            time.sleep(5)

    print(f"\n{'='*60}")
    print(f"DONE — {ok} succeeded, {fail} failed (of {total})")
    print(f"Output: {DRAFTS}")


if __name__ == "__main__":
    main()
