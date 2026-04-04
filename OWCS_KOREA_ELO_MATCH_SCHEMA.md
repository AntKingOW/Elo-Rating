# OWCS Korea Elo Match Schema

## Purpose

This schema defines the minimum dataset needed to compute team Elo from map-level OWCS Korea results.

## One Row = One Map Result

Each row should represent exactly one played map/game.

## Required Fields

| Field | Type | Description |
| --- | --- | --- |
| `event_id` | string | Stable event identifier, for example `owcs_2026_korea_stage_1` |
| `season_year` | integer | Year, for example `2026` |
| `stage_label` | string | Stage name, for example `Stage 1` |
| `week_label` | string | Week label, for example `Week 2` |
| `day_label` | string | Day label, for example `Day 1` |
| `match_date` | string | ISO date, for example `2026-04-03` |
| `match_order` | integer | Match number inside the day |
| `game_number` | integer | Map number inside the series |
| `team_a` | string | Canonical team name |
| `team_b` | string | Canonical team name |
| `winner` | string | Canonical winning team |
| `loser` | string | Canonical losing team |
| `map_name` | string | Map name |
| `map_mode` | string | Control / Hybrid / Flashpoint / Push / Escort |
| `series_format` | string | `bo5` or `bo7` |
| `source_url` | string | Liquipedia event or match URL |
| `source_note` | string | Notes such as screenshot/manual verification |

## Optional Fields

| Field | Type | Description |
| --- | --- | --- |
| `distance_a` | number | Push or escort progress for team A when useful |
| `distance_b` | number | Push or escort progress for team B when useful |
| `score_a` | string | Control or flashpoint style score if needed |
| `score_b` | string | Control or flashpoint style score if needed |
| `mvp_player` | string | Match MVP if available |
| `initial_ban_team` | string | Canonical team name |
| `initial_ban_hero` | string | Hero name |
| `followup_ban_team` | string | Canonical team name |
| `followup_ban_hero` | string | Hero name |

## Ordering Rule

Rows must be sorted in this order before Elo calculation:

1. `match_date`
2. `match_order`
3. `game_number`

If multiple events occur on the same date, also sort by:

4. `season_year`
5. `stage_label`

## Elo Output Fields

These fields should be computed, not manually entered:

| Field | Description |
| --- | --- |
| `elo_team_a_before` | Team A Elo before the map |
| `elo_team_b_before` | Team B Elo before the map |
| `elo_team_a_after` | Team A Elo after the map |
| `elo_team_b_after` | Team B Elo after the map |
| `elo_delta_team_a` | Team A Elo change |
| `elo_delta_team_b` | Team B Elo change |

## Weekly Summary Schema

After map-level calculation, weekly summaries can be derived with:

| Field | Description |
| --- | --- |
| `team_name` | Canonical team name |
| `season_year` | Year |
| `stage_label` | Stage name |
| `week_label` | Week name |
| `elo_start` | Elo before first map of the week |
| `elo_end` | Elo after last map of the week |
| `elo_delta` | `elo_end - elo_start` |
| `maps_played` | Count of maps played |
| `maps_won` | Count of map wins |
| `maps_lost` | Count of map losses |

## Current Recommendation

Keep the first Elo dataset as small and explicit as possible:

- one row per map
- canonical team names only
- manual notes for ambiguous continuity cases
