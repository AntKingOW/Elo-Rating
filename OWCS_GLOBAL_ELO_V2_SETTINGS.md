# OWCS Global Elo V2 Settings

## Purpose

This document defines the second-pass Elo model used for broader 2026 team comparison.

## Scope

- Base dataset starts from Korea historical results already stored in this project.
- Target display ranking should prioritize `teams active in the 2026 season`.
- International matches can be included when they are available from trusted match-history inputs.

## Team display filter

Primary leaderboard:
- Show only teams active in the `2026 season`.

Supporting tables:
- Full hidden pool can still include historical or international opponents because Elo needs opponent strength.

## Elo base model

- Start rating: `1500`
- Core unit: `one map / one game result`
- Series scores such as `3:1`, `4:2`, `3:0` are expanded into game-count results
- Order of wins/losses inside the same series is ignored in v2, same as v1

## Tier multipliers

These multipliers apply to Elo movement after expected-score calculation.

### S / A / Qualifier

- Win multiplier: `1.0`
- Loss multiplier: `1.0`

### B-Tier

- Win multiplier: `0.8`
- Loss multiplier: `1.2`

### C-Tier

- Win multiplier: `0.6`
- Loss multiplier: `1.4`

## Exclusions

- `FF` / forfeit results
- Scrims
- Matches without a trustworthy opponent / score record

## Interpretation

- Strong international wins should help top Korean teams more than domestic-only v1.
- Lower-tier wins should count less.
- Lower-tier losses should hurt more.
- The visible leaderboard should focus on `2026 active teams`, even if historical inactive teams remain in the hidden Elo pool.
