# OWCS Korea Elo Event List

## Scope

This Elo model is intentionally limited to **OWCS Korea domestic play** for the first version.

Included event groups:

- OWCS 2024 Korea Stage 1
- OWCS 2024 Korea Stage 2
- OWCS 2025 Korea Stage 1
- OWCS 2025 Korea Stage 2
- OWCS 2026 Korea Stage 1

Excluded for now:

- Champions Clash
- World Finals
- international cross-region events
- non-OWCS tournaments

## Source Pages

- [OWCS 2024 Korea Stage 1](https://liquipedia.net/overwatch/Overwatch_Champions_Series/2024/Asia/Stage_1/Korea)
- [OWCS 2024 Korea Stage 2](https://liquipedia.net/overwatch/Overwatch_Champions_Series/2024/Asia/Stage_2/Korea)
- [OWCS 2025 Korea Stage 1](https://liquipedia.net/overwatch/Overwatch_Champions_Series/2025/Asia/Stage_1/Korea)
- [OWCS 2025 Korea Stage 2](https://liquipedia.net/overwatch/Overwatch_Champions_Series/2025/Asia/Stage_2/Korea)
- [OWCS 2026 Korea Stage 1](https://liquipedia.net/overwatch/Overwatch_Champions_Series/2026/Asia/Stage_1/Korea)

## Build Order

1. Seed the Elo dataset with already verified 2026 map results.
2. Backfill 2025 Korea map results.
3. Backfill 2024 Korea map results.
4. Recompute from oldest to newest.

## Why This Order

- The 2026 data is already manually verified inside this project.
- Once 2025 and 2024 are added, 2026 opening ratings for non-new teams become naturally earned instead of manually guessed.
- New teams can still start at `1500` without distorting the older team baselines.
