"""Append Champions Clash 2026 map results to OWCS_2026_GLOBAL_MAP_RESULTS.csv"""
from pathlib import Path

CSV_PATH = Path(__file__).parent / "OWCS_2026_GLOBAL_MAP_RESULTS.csv"
SOURCE_URL = "https://liquipedia.net/overwatch/Overwatch_Champions_Series/2026/Champions_Clash"
SOURCE_NOTE = "liquipedia_manual"

# (match_order, game_number, team_a, team_b, winner, loser, map_name, map_mode, series_format, match_date, day_label)
clash_maps = [
    # Match 18: TM vs AG (UB QF, bo3, May 22)
    (18,1,"Twisted Minds","All Gamers","Twisted Minds","All Gamers","Oasis","Control","bo3","2026-05-22","May 22nd"),
    (18,2,"Twisted Minds","All Gamers","Twisted Minds","All Gamers","New Junk City","Flashpoint","bo3","2026-05-22","May 22nd"),
    # Match 19: CR vs DAL (UB QF, bo3, May 22)
    (19,1,"Crazy Raccoon","Dallas Fuel","Crazy Raccoon","Dallas Fuel","Oasis","Control","bo3","2026-05-22","May 22nd"),
    (19,2,"Crazy Raccoon","Dallas Fuel","Crazy Raccoon","Dallas Fuel","Circuit Royal","Escort","bo3","2026-05-22","May 22nd"),
    # Match 20: VP vs WBG (UB QF, bo3, May 22) — VP wins 2-1, WBG wins map 2
    (20,1,"Virtus.pro","Weibo Gaming","Virtus.pro","Weibo Gaming","Oasis","Control","bo3","2026-05-22","May 22nd"),
    (20,2,"Virtus.pro","Weibo Gaming","Weibo Gaming","Virtus.pro","Numbani","Hybrid","bo3","2026-05-22","May 22nd"),
    (20,3,"Virtus.pro","Weibo Gaming","Virtus.pro","Weibo Gaming","New Junk City","Flashpoint","bo3","2026-05-22","May 22nd"),
    # Match 21: ZETA vs SSG (UB QF, bo3, May 22)
    (21,1,"ZETA DIVISION","Spacestation Gaming","ZETA DIVISION","Spacestation Gaming","Ilios","Control","bo3","2026-05-22","May 22nd"),
    (21,2,"ZETA DIVISION","Spacestation Gaming","ZETA DIVISION","Spacestation Gaming","New Junk City","Flashpoint","bo3","2026-05-22","May 22nd"),
    # Match 22: DAL vs AG (LB R1, bo3, May 22)
    (22,1,"Dallas Fuel","All Gamers","Dallas Fuel","All Gamers","Antarctic Peninsula","Control","bo3","2026-05-22","May 22nd"),
    (22,2,"Dallas Fuel","All Gamers","Dallas Fuel","All Gamers","Runasapi","Push","bo3","2026-05-22","May 22nd"),
    # Match 23: WBG vs SSG (LB R1, bo3, May 22)
    (23,1,"Weibo Gaming","Spacestation Gaming","Weibo Gaming","Spacestation Gaming","Oasis","Control","bo3","2026-05-22","May 22nd"),
    (23,2,"Weibo Gaming","Spacestation Gaming","Weibo Gaming","Spacestation Gaming","King's Row","Hybrid","bo3","2026-05-22","May 22nd"),
    # Match 24: CR vs TM (UB SF, bo5, May 23) — CR wins 3-0
    (24,1,"Crazy Raccoon","Twisted Minds","Crazy Raccoon","Twisted Minds","Ilios","Control","bo5","2026-05-23","May 23rd"),
    (24,2,"Crazy Raccoon","Twisted Minds","Crazy Raccoon","Twisted Minds","Rialto","Escort","bo5","2026-05-23","May 23rd"),
    (24,3,"Crazy Raccoon","Twisted Minds","Crazy Raccoon","Twisted Minds","King's Row","Hybrid","bo5","2026-05-23","May 23rd"),
    # Match 25: ZETA vs VP (UB SF, bo5, May 23) — ZETA wins 3-1, VP wins map 4
    (25,1,"ZETA DIVISION","Virtus.pro","ZETA DIVISION","Virtus.pro","Ilios","Control","bo5","2026-05-23","May 23rd"),
    (25,2,"ZETA DIVISION","Virtus.pro","ZETA DIVISION","Virtus.pro","New Junk City","Flashpoint","bo5","2026-05-23","May 23rd"),
    (25,3,"ZETA DIVISION","Virtus.pro","ZETA DIVISION","Virtus.pro","Rialto","Escort","bo5","2026-05-23","May 23rd"),
    (25,4,"ZETA DIVISION","Virtus.pro","Virtus.pro","ZETA DIVISION","King's Row","Hybrid","bo5","2026-05-23","May 23rd"),
    # Match 26: VP vs DAL (LB QF, bo5, May 23) — VP wins 3-1, DAL wins map 1
    (26,1,"Virtus.pro","Dallas Fuel","Dallas Fuel","Virtus.pro","Oasis","Control","bo5","2026-05-23","May 23rd"),
    (26,2,"Virtus.pro","Dallas Fuel","Virtus.pro","Dallas Fuel","Dorado","Escort","bo5","2026-05-23","May 23rd"),
    (26,3,"Virtus.pro","Dallas Fuel","Virtus.pro","Dallas Fuel","New Junk City","Flashpoint","bo5","2026-05-23","May 23rd"),
    (26,4,"Virtus.pro","Dallas Fuel","Virtus.pro","Dallas Fuel","Numbani","Hybrid","bo5","2026-05-23","May 23rd"),
    # Match 27: TM vs WBG (LB QF, bo5, May 23) — TM wins 3-2, WBG wins maps 3,5
    (27,1,"Twisted Minds","Weibo Gaming","Twisted Minds","Weibo Gaming","Oasis","Control","bo5","2026-05-23","May 23rd"),
    (27,2,"Twisted Minds","Weibo Gaming","Twisted Minds","Weibo Gaming","King's Row","Hybrid","bo5","2026-05-23","May 23rd"),
    (27,3,"Twisted Minds","Weibo Gaming","Weibo Gaming","Twisted Minds","Runasapi","Push","bo5","2026-05-23","May 23rd"),
    (27,4,"Twisted Minds","Weibo Gaming","Twisted Minds","Weibo Gaming","Circuit Royal","Escort","bo5","2026-05-23","May 23rd"),
    (27,5,"Twisted Minds","Weibo Gaming","Weibo Gaming","Twisted Minds","New Junk City","Flashpoint","bo5","2026-05-23","May 23rd"),
    # Match 28: CR vs ZETA (UB Final, bo5, May 24) — CR wins 3-1, ZETA wins map 3
    (28,1,"Crazy Raccoon","ZETA DIVISION","Crazy Raccoon","ZETA DIVISION","Ilios","Control","bo5","2026-05-24","May 24th"),
    (28,2,"Crazy Raccoon","ZETA DIVISION","Crazy Raccoon","ZETA DIVISION","Circuit Royal","Escort","bo5","2026-05-24","May 24th"),
    (28,3,"Crazy Raccoon","ZETA DIVISION","ZETA DIVISION","Crazy Raccoon","Suravasa","Flashpoint","bo5","2026-05-24","May 24th"),
    (28,4,"Crazy Raccoon","ZETA DIVISION","Crazy Raccoon","ZETA DIVISION","King's Row","Hybrid","bo5","2026-05-24","May 24th"),
    # Match 29: TM vs VP (LB SF, bo5, May 24) — TM wins 3-1, VP wins map 1
    (29,1,"Twisted Minds","Virtus.pro","Virtus.pro","Twisted Minds","Oasis","Control","bo5","2026-05-24","May 24th"),
    (29,2,"Twisted Minds","Virtus.pro","Twisted Minds","Virtus.pro","New Junk City","Flashpoint","bo5","2026-05-24","May 24th"),
    (29,3,"Twisted Minds","Virtus.pro","Twisted Minds","Virtus.pro","Rialto","Escort","bo5","2026-05-24","May 24th"),
    (29,4,"Twisted Minds","Virtus.pro","Twisted Minds","Virtus.pro","Runasapi","Push","bo5","2026-05-24","May 24th"),
    # Match 30: TM vs ZETA (LB Final, bo5, May 24) — TM wins 3-1, ZETA wins map 3
    (30,1,"Twisted Minds","ZETA DIVISION","Twisted Minds","ZETA DIVISION","Ilios","Control","bo5","2026-05-24","May 24th"),
    (30,2,"Twisted Minds","ZETA DIVISION","Twisted Minds","ZETA DIVISION","Suravasa","Flashpoint","bo5","2026-05-24","May 24th"),
    (30,3,"Twisted Minds","ZETA DIVISION","ZETA DIVISION","Twisted Minds","Circuit Royal","Escort","bo5","2026-05-24","May 24th"),
    (30,4,"Twisted Minds","ZETA DIVISION","Twisted Minds","ZETA DIVISION","King's Row","Hybrid","bo5","2026-05-24","May 24th"),
    # Match 31: CR vs TM (Grand Final, bo7, May 24) — CR wins 4-3, TM wins maps 4,5,6
    (31,1,"Crazy Raccoon","Twisted Minds","Crazy Raccoon","Twisted Minds","Ilios","Control","bo7","2026-05-24","May 24th"),
    (31,2,"Crazy Raccoon","Twisted Minds","Crazy Raccoon","Twisted Minds","Circuit Royal","Escort","bo7","2026-05-24","May 24th"),
    (31,3,"Crazy Raccoon","Twisted Minds","Crazy Raccoon","Twisted Minds","King's Row","Hybrid","bo7","2026-05-24","May 24th"),
    (31,4,"Crazy Raccoon","Twisted Minds","Twisted Minds","Crazy Raccoon","New Junk City","Flashpoint","bo7","2026-05-24","May 24th"),
    (31,5,"Crazy Raccoon","Twisted Minds","Twisted Minds","Crazy Raccoon","Runasapi","Push","bo7","2026-05-24","May 24th"),
    (31,6,"Crazy Raccoon","Twisted Minds","Twisted Minds","Crazy Raccoon","Oasis","Control","bo7","2026-05-24","May 24th"),
    (31,7,"Crazy Raccoon","Twisted Minds","Crazy Raccoon","Twisted Minds","Suravasa","Flashpoint","bo7","2026-05-24","May 24th"),
]

last_order = 655
new_rows = []
gmo = last_order + 1

for (match_order, game_number, team_a, team_b, winner, loser, map_name, map_mode, series_format, match_date, day_label) in clash_maps:
    row = f"{gmo},owcs_2026_champions_clash,international,2026,Champions Clash,Playoffs,{day_label},{match_date},{match_order},{game_number},{team_a},{team_b},{winner},{loser},{map_name},{map_mode},{series_format},{SOURCE_URL},{SOURCE_NOTE}\n"
    new_rows.append(row)
    gmo += 1

print(f"Total new rows: {len(new_rows)}")
print(f"New global_map_order range: 656 to {gmo-1}")
print(f"\nFirst row: {new_rows[0]}")
print(f"Last row:  {new_rows[-1]}")

with open(CSV_PATH, "a", encoding="utf-8", newline="") as f:
    for row in new_rows:
        f.write(row)

print(f"\nDone. Appended {len(new_rows)} rows.")
