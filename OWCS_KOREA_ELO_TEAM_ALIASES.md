# OWCS Korea Elo Team Alias Map

## Purpose

This file stores the currently approved **Korea team name and abbreviation map**
for OWCS Korea Elo ingestion.

Use this map when converting:

- Liquipedia played-match pages
- copied match-history text
- screenshot labels
- broadcast abbreviations

into canonical Korea team names.

## Rule

- This file is for **name normalization only**.
- It does **not** imply Elo inheritance or team-successor carry-over.
- Elo inheritance remains governed by
  [OWCS_KOREA_ELO_TEAM_IDENTITY_MAP.md](/C:/Users/user/Documents/Playground/OWCStats/OWCS_KOREA_ELO_TEAM_IDENTITY_MAP.md).

## Approved Korea Team Alias Map

| Canonical Team | Known Aliases / Abbreviations | Notes |
| --- | --- | --- |
| Team Falcons | Falcons, FLC | Current canonical domestic name |
| Crazy Raccoon | CR | Current canonical domestic name |
| ZETA DIVISION | ZETA | Current canonical domestic name |
| Poker Face | PF | Current canonical domestic name |
| T1 | T1 | Current canonical domestic name |
| ONSIDE GAMING | OSG, RODE ONSIDE GAMING, RONG | Use `ONSIDE GAMING` as canonical name |
| New Era | NE | Current canonical domestic name |
| Cheeseburger | CB | Current canonical domestic name |
| ZAN Esports | ZAN | Current canonical domestic name |
| From The Gamer | FTG | Historical Korea team |
| WAC | WAC | Historical Korea team |
| YETI | YETI | Historical Korea team |
| RunAway | RA | Historical Korea team |
| Sin Prisa Gaming | SPG | Historical Korea team |
| Vesta Crew | VEC | Historical Korea team; use exact historical name when parsing older results |
| Genesis | GNS | Historical Korea team |
| HaeJeokDan | HJD | Historical Korea team |
| Old Ocean | OCN | Historical Korea team |
| WAY | WAY | Historical Korea team |
| All Gamers Global | AGG | Historical Korea team |
| Fnatic | FNC | Historical Korea participant |
| WAE | WAE | Korea alias pending long-form confirmation |
| MIR | MIR | Korea alias pending long-form confirmation |

## Current Assumption

The following abbreviations are currently treated as **confirmed Korea-context
team aliases** for OWCS Korea parsing:

- CR
- PF
- ZETA
- T1
- OSG
- NE
- CB
- ZAN
- FTG
- WAC
- HJD
- VEC
- WAY
- OCN
- GNS
- SPG
- RA
- YETI
- AGG
- FNC
- WAE
- MIR

## Notes

- If a future played-match export contains an unknown short code, add it here
  before using it in Elo ingestion.
- International-only abbreviations should be tracked separately and should not
  be mixed into this Korea-only alias file unless needed for filtering.
