# OWCS Korea / Global Elo V2 Notes

## Why Team Falcons looked low in v1

- The current published Elo is still `Korea domestic only`.
- International results such as `World Finals`, `Champions Clash`, `Midseason Championship`, and `EWC` are not yet backfilled into the active model.
- Match tier weighting is also not yet applied in the active model; every counted map currently uses the same `K-factor`.

## Proposed V2 weighting

- `S/A/Qualifier (A-Tier)` matches: win/loss multiplier `1.0 / 1.0`
- `B-Tier` matches: win/loss multiplier `0.8 / 1.2`
- `C-Tier` matches: win/loss multiplier `0.6 / 1.4`
- `FF` matches: excluded

## Current blocker

- The Elo backfill CSV does not yet store a reliable `tier` field for every imported series.
- The active CSV is also domestic-focused, so international rows must be added before a true global v2 model can be published.

## Recommendation

1. Keep the current domestic Elo as `v1`.
2. Backfill international results for 2024-2026 current teams.
3. Add `tier` to every imported series row.
4. Publish a separate `v2` ranking rather than silently overwriting `v1`.