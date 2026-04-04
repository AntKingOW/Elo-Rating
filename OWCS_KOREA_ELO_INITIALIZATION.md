# OWCS Korea Elo Initialization

## Recommended First Version

Use this policy:

1. Start every team's **first recorded OWCS Korea map under its exact current team name** at `1500`.
2. Compute Elo chronologically from the oldest Korea OWCS map result forward.
3. Between seasons, regress toward `1500`.
4. Do not inherit Elo from predecessor teams in the first model.

## Why Not Hand-Assign Strong Teams Higher Ratings?

Because that introduces subjective bias.

If `Crazy Raccoon`, `ZETA DIVISION`, or `Team Falcons` start above `1500` by manual choice, the rating curve becomes much harder to defend later. It is cleaner to let:

- 2024 OWCS Korea results
- 2025 OWCS Korea results

create their 2026 starting position naturally.

## Recommended Season Reset

Between seasons:

`new_rating = 1500 + 0.75 * (old_rating - 1500)`

This keeps long-term strength but prevents old results from overpowering newer weekly movement.

## Current Practical Starting Point

Before 2024 and 2025 are fully backfilled:

- use the verified 2026 dataset to test the Elo engine
- do **not** treat 2026-only outputs as final historical Elo

This gives us a working calculator now, and a clear path to improve it later.

## Team Continuity Rule

Use [OWCS_KOREA_ELO_TEAM_IDENTITY_MAP.md](/C:/Users/user/Documents/Playground/OWCStats/OWCS_KOREA_ELO_TEAM_IDENTITY_MAP.md) to decide continuity.

Conservative rule:

- exact current team name first appearance: `1500`
- predecessor teams: ignored for v1

This is safer than over-linking teams by name similarity or roster continuity.
