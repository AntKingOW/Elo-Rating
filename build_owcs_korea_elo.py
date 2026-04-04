from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INPUT_CSV = ROOT / "OWCS_KOREA_ELO_MAP_RESULTS.csv"
SERIES_BACKFILL_CSV = ROOT / "OWCS_KOREA_ELO_SERIES_BACKFILL.csv"
OUTPUT_MD = ROOT / "OWCS_KOREA_ELO_CURRENT.md"
FALCONS_OUTPUT_MD = ROOT / "OWCS_KOREA_ELO_TEAM_FALCONS.md"
TRENDS_OUTPUT_MD = ROOT / "OWCS_KOREA_ELO_YEAR_STAGE_TRENDS.md"

BASE_RATING = 1500.0
K_FACTOR = 24.0
TEAM_CANONICAL_MAP = {
    "From The Gamer": "ZETA DIVISION",
    "WAC": "Crazy Raccoon",
}


@dataclass
class MapResult:
    season_year: int
    stage_label: str
    week_label: str
    day_label: str
    match_date: str
    sort_key: str
    match_order: int
    game_number: int
    team_a: str
    team_b: str
    winner: str
    loser: str
    map_name: str


def expected_score(rating_a: float, rating_b: float) -> float:
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))


def canonical_team_name(team: str) -> str:
    return TEAM_CANONICAL_MAP.get(team, team)


def load_rows() -> list[MapResult]:
    rows: list[MapResult] = []
    with INPUT_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                MapResult(
                    season_year=int(row["season_year"]),
                    stage_label=row["stage_label"],
                    week_label=row["week_label"],
                    day_label=row["day_label"],
                    match_date=row["match_date"],
                    sort_key=row["match_date"],
                    match_order=int(row["match_order"]),
                    game_number=int(row["game_number"]),
                    team_a=canonical_team_name(row["team_a"]),
                    team_b=canonical_team_name(row["team_b"]),
                    winner=canonical_team_name(row["winner"]),
                    loser=canonical_team_name(row["loser"]),
                    map_name=row["map_name"],
                )
            )

    if SERIES_BACKFILL_CSV.exists():
        with SERIES_BACKFILL_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                season_year = int(row["season_year"])
                team_a = canonical_team_name(row["team_a"])
                team_b = canonical_team_name(row["team_b"])
                wins_a = int(row["wins_a"])
                wins_b = int(row["wins_b"])
                match_date = row["match_date"]
                sort_key = row["match_sort_key"]
                match_order = int(row["match_order"])
                total_games = wins_a + wins_b

                for game_number in range(1, total_games + 1):
                    if game_number <= wins_a:
                        winner = team_a
                        loser = team_b
                    else:
                        winner = team_b
                        loser = team_a

                    rows.append(
                        MapResult(
                            season_year=season_year,
                            stage_label=row["stage_label"],
                            week_label=row["week_label"],
                            day_label=row["day_label"],
                            match_date=match_date,
                            sort_key=sort_key,
                            match_order=match_order,
                            game_number=game_number,
                            team_a=team_a,
                            team_b=team_b,
                            winner=winner,
                            loser=loser,
                            map_name=f"SeriesGame{game_number}",
                        )
                    )

    rows.sort(
        key=lambda r: (
            r.season_year,
            r.stage_label,
            r.sort_key,
            r.match_order,
            r.game_number,
        )
    )
    return rows


def calculate_state(rows: list[MapResult]):
    ratings: dict[str, float] = defaultdict(lambda: BASE_RATING)
    weekly: dict[tuple[str, str], dict[str, float | int]] = {}
    stage_team: dict[tuple[str, str], dict[str, float | int]] = {}
    totals: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {"maps_played": 0, "maps_won": 0, "maps_lost": 0}
    )
    timeline: list[dict[str, object]] = []

    for row in rows:
        for team in (row.team_a, row.team_b):
            weekly_key = (f"{row.season_year} {row.stage_label} - {row.week_label}", team)
            if weekly_key not in weekly:
                weekly[weekly_key] = {
                    "elo_start": ratings[team],
                    "elo_end": ratings[team],
                    "maps_played": 0,
                    "maps_won": 0,
                    "maps_lost": 0,
                }
            stage_key = (f"{row.season_year} {row.stage_label}", team)
            if stage_key not in stage_team:
                stage_team[stage_key] = {
                    "elo_start": ratings[team],
                    "elo_end": ratings[team],
                    "maps_played": 0,
                    "maps_won": 0,
                    "maps_lost": 0,
                }

        rating_a = ratings[row.team_a]
        rating_b = ratings[row.team_b]
        expected_a = expected_score(rating_a, rating_b)
        expected_b = expected_score(rating_b, rating_a)

        score_a = 1.0 if row.winner == row.team_a else 0.0
        score_b = 1.0 if row.winner == row.team_b else 0.0

        ratings[row.team_a] = rating_a + K_FACTOR * (score_a - expected_a)
        ratings[row.team_b] = rating_b + K_FACTOR * (score_b - expected_b)

        for team, won in ((row.team_a, score_a == 1.0), (row.team_b, score_b == 1.0)):
            weekly_key = (f"{row.season_year} {row.stage_label} - {row.week_label}", team)
            weekly[weekly_key]["elo_end"] = ratings[team]
            weekly[weekly_key]["maps_played"] += 1
            stage_key = (f"{row.season_year} {row.stage_label}", team)
            stage_team[stage_key]["elo_end"] = ratings[team]
            stage_team[stage_key]["maps_played"] += 1
            totals[team]["maps_played"] += 1
            if won:
                weekly[weekly_key]["maps_won"] += 1
                stage_team[stage_key]["maps_won"] += 1
                totals[team]["maps_won"] += 1
            else:
                weekly[weekly_key]["maps_lost"] += 1
                stage_team[stage_key]["maps_lost"] += 1
                totals[team]["maps_lost"] += 1

        timeline.append(
            {
                "season_year": row.season_year,
                "stage_label": row.stage_label,
                "week_label": row.week_label,
                "match_date": row.match_date,
                "sort_key": row.sort_key,
                "match_order": row.match_order,
                "game_number": row.game_number,
                "team_a": row.team_a,
                "team_b": row.team_b,
                "winner": row.winner,
                "ratings": dict(ratings),
            }
        )

    return ratings, weekly, stage_team, totals, timeline


def build_markdown(rows: list[MapResult]) -> str:
    ratings, weekly, stage_team, totals, _timeline = calculate_state(rows)

    ranking = sorted(ratings.items(), key=lambda item: item[1], reverse=True)
    lines: list[str] = []
    lines.append("# OWCS Korea Elo Current")
    lines.append("")
    lines.append("This is a first-pass Elo table built from the currently verified Korea-only map results in:")
    lines.append("")
    lines.append(f"- [{INPUT_CSV.name}]({INPUT_CSV.as_posix()})")
    lines.append("")
    lines.append(f"Model: starting Elo `{int(BASE_RATING)}`, K-factor `{int(K_FACTOR)}`")
    lines.append("")
    lines.append("## Current Team Ratings")
    lines.append("")
    lines.append("| Rank | Team | Elo | Maps Played | W-L |")
    lines.append("| --- | --- | ---: | ---: | ---: |")
    for idx, (team, rating) in enumerate(ranking, start=1):
        total = totals[team]
        wl = f"{int(total['maps_won'])}-{int(total['maps_lost'])}"
        lines.append(
            f"| {idx} | {team} | {rating:.2f} | {int(total['maps_played'])} | {wl} |"
        )

    grouped_weeks: dict[str, list[tuple[str, dict[str, float | int]]]] = defaultdict(list)
    for (week_label, team), data in weekly.items():
        grouped_weeks[week_label].append((team, data))

    for week_label in sorted(grouped_weeks.keys()):
        lines.append("")
        lines.append(f"## {week_label}")
        lines.append("")
        lines.append("| Team | Elo Start | Elo End | Delta | Maps | W-L |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
        week_rows = sorted(
            grouped_weeks[week_label],
            key=lambda item: float(item[1]["elo_end"]),
            reverse=True,
        )
        for team, data in week_rows:
            delta = float(data["elo_end"]) - float(data["elo_start"])
            wl = f"{int(data['maps_won'])}-{int(data['maps_lost'])}"
            lines.append(
                f"| {team} | {float(data['elo_start']):.2f} | {float(data['elo_end']):.2f} | {delta:+.2f} | {int(data['maps_played'])} | {wl} |"
            )

    grouped_stages: dict[str, list[tuple[str, dict[str, float | int]]]] = defaultdict(list)
    for (stage_label, team), data in stage_team.items():
        grouped_stages[stage_label].append((team, data))

    for stage_label in sorted(grouped_stages.keys()):
        lines.append("")
        lines.append(f"## {stage_label}")
        lines.append("")
        lines.append("| Team | Elo Start | Elo End | Delta | Maps | W-L |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
        stage_rows = sorted(
            grouped_stages[stage_label],
            key=lambda item: float(item[1]["elo_end"]),
            reverse=True,
        )
        for team, data in stage_rows:
            delta = float(data["elo_end"]) - float(data["elo_start"])
            wl = f"{int(data['maps_won'])}-{int(data['maps_lost'])}"
            lines.append(
                f"| {team} | {float(data['elo_start']):.2f} | {float(data['elo_end']):.2f} | {delta:+.2f} | {int(data['maps_played'])} | {wl} |"
            )

    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- This table uses verified 2026 map results plus series-score backfill rows when only Korea domestic series scores are available.")
    lines.append("- Series-score backfill expands a `3:1` style result into four game-level Elo updates without map identity.")
    lines.append("- Within-series map order is not specially weighted; each map is one Elo result.")
    lines.append("")
    return "\n".join(lines)


def build_falcons_report(rows: list[MapResult]) -> str:
    _ratings, weekly, stage_team, totals, timeline = calculate_state(rows)
    team = "Team Falcons"
    lines: list[str] = []
    lines.append("# OWCS Korea Elo - Team Falcons")
    lines.append("")
    lines.append("This report tracks Team Falcons using the current Korea-only Elo dataset.")
    lines.append("")
    lines.append(f"- Total maps counted: {int(totals[team]['maps_played'])}")
    lines.append(f"- Total W-L: {int(totals[team]['maps_won'])}-{int(totals[team]['maps_lost'])}")
    lines.append("")
    lines.append("## Stage Summary")
    lines.append("")
    lines.append("| Stage | Elo Start | Elo End | Delta | Maps | W-L |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    stage_rows = []
    for (stage_label, stage_team_name), data in stage_team.items():
        if stage_team_name == team:
            stage_rows.append((stage_label, data))
    for stage_label, data in sorted(stage_rows):
        delta = float(data["elo_end"]) - float(data["elo_start"])
        wl = f"{int(data['maps_won'])}-{int(data['maps_lost'])}"
        lines.append(
            f"| {stage_label} | {float(data['elo_start']):.2f} | {float(data['elo_end']):.2f} | {delta:+.2f} | {int(data['maps_played'])} | {wl} |"
        )
    lines.append("")
    lines.append("## Weekly Summary")
    lines.append("")
    lines.append("| Week | Elo Start | Elo End | Delta | Maps | W-L |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    week_rows = []
    for (week_label, team_name), data in weekly.items():
        if team_name == team:
            week_rows.append((week_label, data))
    for week_label, data in sorted(week_rows):
        delta = float(data["elo_end"]) - float(data["elo_start"])
        wl = f"{int(data['maps_won'])}-{int(data['maps_lost'])}"
        lines.append(
            f"| {week_label} | {float(data['elo_start']):.2f} | {float(data['elo_end']):.2f} | {delta:+.2f} | {int(data['maps_played'])} | {wl} |"
        )
    lines.append("")
    lines.append("## Match Timeline")
    lines.append("")
    lines.append("| Date | Stage | Week | Game | Winner | Team Falcons Elo |")
    lines.append("| --- | --- | --- | ---: | --- | ---: |")
    for row in timeline:
        if row["team_a"] != team and row["team_b"] != team:
            continue
        lines.append(
            f"| {row['match_date']} | {row['stage_label']} | {row['week_label']} | {row['game_number']} | {row['winner']} | {float(row['ratings'][team]):.2f} |"
        )
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- 2024-2025 historical data currently includes Korea domestic Team Falcons series supplied in text form.")
    lines.append("- When only series scores are known, each map in the series is treated as an unlabeled game-level Elo result.")
    lines.append("- This is already enough to trace weekly and stage movement for Team Falcons, but full-league historical Elo still needs other teams' domestic match histories.")
    lines.append("")
    return "\n".join(lines)


def build_year_stage_trends(rows: list[MapResult]) -> str:
    _ratings, _weekly, stage_team, _totals, _timeline = calculate_state(rows)

    current_teams = [
        "Team Falcons",
        "Crazy Raccoon",
        "ZETA DIVISION",
        "Poker Face",
        "T1",
        "ONSIDE GAMING",
        "New Era",
        "Cheeseburger",
        "ZAN Esports",
    ]

    stage_buckets: dict[str, list[tuple[str, dict[str, float | int]]]] = defaultdict(list)
    team_stage_rows: dict[str, list[tuple[str, dict[str, float | int]]]] = defaultdict(list)

    for (stage_label, team), data in stage_team.items():
        stage_buckets[stage_label].append((team, data))
        team_stage_rows[team].append((stage_label, data))

    lines: list[str] = []
    lines.append("# OWCS Korea Elo Year/Stage Trends")
    lines.append("")
    lines.append("This report is for observing Elo movement by year and stage.")
    lines.append("")
    lines.append("## Stage Delta Summary")
    lines.append("")

    for stage_label in sorted(stage_buckets.keys()):
        lines.append(f"### {stage_label}")
        lines.append("")
        lines.append("| Team | Elo Start | Elo End | Delta | Maps | W-L |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
        rows_for_stage = sorted(
            stage_buckets[stage_label],
            key=lambda item: float(item[1]["elo_end"]) - float(item[1]["elo_start"]),
            reverse=True,
        )
        for team, data in rows_for_stage:
            delta = float(data["elo_end"]) - float(data["elo_start"])
            wl = f"{int(data['maps_won'])}-{int(data['maps_lost'])}"
            lines.append(
                f"| {team} | {float(data['elo_start']):.2f} | {float(data['elo_end']):.2f} | {delta:+.2f} | {int(data['maps_played'])} | {wl} |"
            )
        lines.append("")

    lines.append("## Current-Team Stage Journeys")
    lines.append("")
    lines.append("These tables track the current Korea teams across the stages where they appear in the dataset.")
    lines.append("")

    for team in current_teams:
        lines.append(f"### {team}")
        lines.append("")
        lines.append("| Stage | Elo Start | Elo End | Delta | Maps | W-L |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
        rows_for_team = sorted(team_stage_rows.get(team, []), key=lambda item: item[0])
        if not rows_for_team:
            lines.append("| - | - | - | - | - | - |")
        else:
            for stage_label, data in rows_for_team:
                delta = float(data["elo_end"]) - float(data["elo_start"])
                wl = f"{int(data['maps_won'])}-{int(data['maps_lost'])}"
                lines.append(
                    f"| {stage_label} | {float(data['elo_start']):.2f} | {float(data['elo_end']):.2f} | {delta:+.2f} | {int(data['maps_played'])} | {wl} |"
                )
        lines.append("")

    lines.append("## Notes")
    lines.append("")
    lines.append("- 2026 Stage 1 is based on verified map-level results already stored in the project.")
    lines.append("- 2024-2025 domestic history currently includes the Korea-side Team Falcons backfill provided in text form.")
    lines.append("- Because not every other team's 2024-2025 domestic history is backfilled yet, the strongest use of this report right now is trend observation rather than final league-wide historical ranking.")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    rows = load_rows()
    markdown = build_markdown(rows)
    OUTPUT_MD.write_text(markdown, encoding="utf-8")
    FALCONS_OUTPUT_MD.write_text(build_falcons_report(rows), encoding="utf-8")
    TRENDS_OUTPUT_MD.write_text(build_year_stage_trends(rows), encoding="utf-8")
    print(f"Wrote {OUTPUT_MD}")
    print(f"Wrote {FALCONS_OUTPUT_MD}")
    print(f"Wrote {TRENDS_OUTPUT_MD}")


if __name__ == "__main__":
    main()
