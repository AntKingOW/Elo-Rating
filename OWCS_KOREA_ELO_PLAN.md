# OWCS Korea Elo Plan

## Goal

Build a Korea-only OWCS team Elo model starting from 2024 and track:

- map-level Elo movement
- weekly Elo change
- stage-level Elo change
- season-level Elo change

## Recommended Rating Unit

Use **one played map/game as one Elo result**.

Why:

- `3:0`, `3:2`, and `4:3` series should not move ratings the same way
- map-level results reflect team strength more precisely than match-only results
- weekly trend charts become more informative

## Recommended Scope

Start with **OWCS Korea only**:

- OWCS 2024 Korea Stage 1
- OWCS 2024 Korea Stage 2
- OWCS 2025 Korea Stage 1
- OWCS 2025 Korea Stage 2
- OWCS 2026 Korea Stage 1

Use Liquipedia as the source for event pages and match/map outcomes.

Known source pages:

- https://liquipedia.net/overwatch/Overwatch_Champions_Series/2024/Asia/Stage_1/Korea
- https://liquipedia.net/overwatch/Overwatch_Champions_Series/2024/Asia/Stage_2/Korea
- https://liquipedia.net/overwatch/Overwatch_Champions_Series/2025/Asia/Stage_1/Korea
- https://liquipedia.net/overwatch/Overwatch_Champions_Series/2025/Asia/Stage_2/Korea
- https://liquipedia.net/overwatch/Overwatch_Champions_Series/2026/Asia/Stage_1/Korea

## Baseline Model

Recommended first-pass settings:

- starting Elo: `1500`
- expected score:
  - `Ea = 1 / (1 + 10 ^ ((Rb - Ra) / 400))`
- update:
  - `Ra' = Ra + K * (Sa - Ea)`
- result value:
  - map win = `1`
  - map loss = `0`
- initial K-factor: `24`

Reason for `K = 24`:

- large enough to show movement on weekly charts
- not so large that one upset breaks the table
- simple enough for the first version

## Season Carry-Over Policy

Recommended policy:

1. Carry ratings forward **within the same calendar season**.
2. Regress ratings toward mean between seasons.

Suggested season reset formula:

- `new_season_rating = 1500 + 0.75 * (old_rating - 1500)`

This is an inference-based recommendation, not a Liquipedia rule.

Why:

- keeps long-term strength signal
- prevents 2024 results from overpowering 2026 charts
- helps make new-season weekly movement easier to read

## New Team Policy

For teams with no verified Korea OWCS history:

- start at `1500`

For rebrands or clear continuity cases:

- do **not** auto-carry by name similarity
- only carry ratings through a manual identity map

Reason:

- OWCS has new teams, qualifier teams, and brand changes
- automatic inheritance will create false continuity

## Weekly Tracking

For each team and each week, store:

- week start Elo
- week end Elo
- weekly delta
- maps played in the week
- wins in the week
- losses in the week

For each stage, also store:

- stage start Elo
- stage end Elo
- total stage delta

For each season, also store:

- season start Elo
- season end Elo
- total season delta

## Suggested Build Order

1. Build event list for 2024-2026 Korea stages.
2. Build team identity map.
3. Build map-level result dataset.
4. Compute chronological Elo updates.
5. Aggregate to weekly, stage, and season summaries.
6. Add charts later.

## Known Limitation

Liquipedia clearly provides Korea event pages, but map-level results may sometimes live inside expandable match blocks. In this environment, those details may need manual review or screenshot-assisted verification instead of fully automatic extraction.

## Recommendation

Proceed with:

- Korea-only Elo
- map-level Elo
- `1500` new-team baseline
- manual identity mapping
- between-season regression to mean

This gives the most stable first version without overfitting uncertain team continuity.
