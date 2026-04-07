"""
OWCS 2025 Elo Dashboard — Phase-Based HTML Generator

Builds a self-contained dashboard with:
  - Region tabs: Global / Korea / Japan / Pacific / NA / EMEA / China
  - 5-phase Elo trend lines (Stage 1 / Champions Clash / Stage 2 + Midseason / Stage 3 / Finals)
  - Top 5 panel for the selected region
  - Full rankings table

Usage:
    python visualize_elo.py
"""

from __future__ import annotations

import colorsys
import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT        = Path(__file__).resolve().parent
FINAL_CSV   = ROOT / "OWCS_2025_GLOBAL_ELO_FINAL.csv"
HISTORY_CSV = ROOT / "OWCS_2025_GLOBAL_ELO_HISTORY.csv"
OUTPUT_HTML = ROOT / "OWCS_2025_ELO_DASHBOARD.html"

REGIONS = ["Korea", "Japan", "Pacific", "NA", "EMEA", "China"]
REGION_FLAGS = {
    "all":     "🌐",
    "Korea":   "🇰🇷",
    "Japan":   "🇯🇵",
    "Pacific": "🌏",
    "NA":      "🇺🇸",
    "EMEA":    "🌍",
    "China":   "🇨🇳",
}
REGION_HUE = {
    "Korea":   0,
    "Japan":   325,
    "Pacific": 195,
    "NA":      132,
    "EMEA":    272,
    "China":   18,
    "Intl":    36,
}

# ---------------------------------------------------------------------------
# Phase definitions — 5 tournament phases in chronological order
# Each entry: (display_label, [event_ids_in_phase_in_order])
# ---------------------------------------------------------------------------
PHASE_DEFS: list[tuple[str, list[str]]] = [
    ("Stage 1", [
        "owcs_2025_asia_s1_japan",
        "owcs_2025_asia_s1_pacific",
        "owcs_2025_asia_s1_korea",
        "owcs_2025_na_s1",
        "owcs_2025_emea_s1",
        "owcs_2025_asia_s1_main",
        "owcs_2025_china_s1",
    ]),
    ("Champions Clash", [
        "owcs_2025_champions_clash",
    ]),
    ("Stage 2", [
        "owcs_2025_asia_s2_korea",
        "owcs_2025_na_s2",
        "owcs_2025_emea_s2",
        "owcs_2025_asia_s2_japan",
        "owcs_2025_asia_s2_pacific",
        "owcs_2025_china_s2",
    ]),
    ("Midseason Championship", [
        "owcs_2025_midseason",
    ]),
    ("Stage 3", [
        "owcs_2025_asia_s3_japan",
        "owcs_2025_asia_s3_pacific",
        "owcs_2025_asia_s3_korea",
        "owcs_2025_na_s3",
        "owcs_2025_emea_s3",
        "owcs_2025_china_s3",
        "owcs_2025_apac_championship",
        "owcs_2025_korea_road_to_wf",
    ]),
    ("World Finals", [
        "owcs_2025_world_finals",
    ]),
]

# Human-readable event names for tooltips and notes
EVENT_NICE_LABEL: dict[str, str] = {
    "owcs_2025_asia_s1_japan":     "Asia S1 Japan",
    "owcs_2025_asia_s1_pacific":   "Asia S1 Pacific",
    "owcs_2025_asia_s1_korea":     "Asia S1 Korea",
    "owcs_2025_na_s1":             "NA Stage 1",
    "owcs_2025_emea_s1":           "EMEA Stage 1",
    "owcs_2025_asia_s1_main":      "Asia S1 Main",
    "owcs_2025_china_s1":          "China Stage 1",
    "owcs_2025_champions_clash":   "Champions Clash",
    "owcs_2025_asia_s2_korea":     "Asia S2 Korea",
    "owcs_2025_na_s2":             "NA Stage 2",
    "owcs_2025_emea_s2":           "EMEA Stage 2",
    "owcs_2025_asia_s2_japan":     "Asia S2 Japan",
    "owcs_2025_asia_s2_pacific":   "Asia S2 Pacific",
    "owcs_2025_china_s2":          "China Stage 2",
    "owcs_2025_midseason":         "Midseason Championship",
    "owcs_2025_asia_s3_japan":     "Asia S3 Japan",
    "owcs_2025_asia_s3_pacific":   "Asia S3 Pacific",
    "owcs_2025_asia_s3_korea":     "Asia S3 Korea",
    "owcs_2025_na_s3":             "NA Stage 3",
    "owcs_2025_emea_s3":           "EMEA Stage 3",
    "owcs_2025_china_s3":          "China Stage 3",
    "owcs_2025_apac_championship": "APAC Championship",
    "owcs_2025_korea_road_to_wf":  "Korea Road to WF",
    "owcs_2025_world_finals":      "World Finals",
}


# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------

def _hsl_to_hex(h: float, s: float, l: float) -> str:
    r, g, b = colorsys.hls_to_rgb(h / 360, l, s)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def region_color(region: str, idx: int = 0, total: int = 1) -> str:
    hue        = REGION_HUE.get(region, 180)
    steps      = max(total, 1)
    lightness  = 0.44 + 0.28 * (idx / steps)
    saturation = 0.78 - 0.12 * (idx % 2)
    return _hsl_to_hex(hue, saturation, lightness)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data() -> tuple[list[dict], list[str], list[list[str]]]:
    final_rows   = list(csv.DictReader(FINAL_CSV.open(encoding="utf-8")))
    history_rows = list(csv.DictReader(HISTORY_CSV.open(encoding="utf-8")))

    # Build lookup: event_id → phase index and ordering within phase
    event_to_phase:        dict[str, int] = {}
    event_order_in_phase:  dict[str, int] = {}
    for phase_idx, (_, event_ids) in enumerate(PHASE_DEFS):
        for pos, eid in enumerate(event_ids):
            event_to_phase[eid]       = phase_idx
            event_order_in_phase[eid] = pos

    num_phases = len(PHASE_DEFS)

    # Accumulate per-team phase data (history rows are in global_map_order → last write wins)
    team_phase_elo:    dict[str, dict[int, float]] = defaultdict(dict)
    team_phase_events: dict[str, dict[int, set]]   = defaultdict(lambda: defaultdict(set))

    for row in history_rows:
        team     = row["team"]
        eid      = row["event_id"]
        elo      = float(row["elo_after"])
        phase_idx = event_to_phase.get(eid)
        if phase_idx is None:
            continue
        team_phase_elo[team][phase_idx]    = elo   # last row per (team, phase) = final elo
        team_phase_events[team][phase_idx].add(eid)

    # Build sorted teams list
    region_totals: dict[str, int] = defaultdict(int)
    for row in final_rows:
        region_totals[row["home_region"]] += 1

    region_index: dict[str, int] = defaultdict(int)
    teams: list[dict] = []

    for row in sorted(final_rows, key=lambda r: float(r["elo"]), reverse=True):
        name   = row["team"]
        region = row["home_region"]
        idx    = region_index[region]
        region_index[region] += 1

        # Phase Elo array with carry-forward for non-active phases
        elo_map = team_phase_elo.get(name, {})
        phase_elos: list[float | None] = []
        current: float | None = None
        for i in range(num_phases):
            if i in elo_map:
                current = round(elo_map[i], 1)
            phase_elos.append(current)

        # Phase events arrays sorted by position within each phase
        events_map = team_phase_events.get(name, {})
        phase_events_list: list[list[str]] = []
        for i in range(num_phases):
            _, phase_eids = PHASE_DEFS[i]
            participated  = events_map.get(i, set())
            sorted_eids   = sorted(participated, key=lambda e: event_order_in_phase.get(e, 999))
            phase_events_list.append([EVENT_NICE_LABEL.get(e, e) for e in sorted_eids])

        # Delta: last actual participation phase vs second-to-last actual participation phase
        actual = sorted(elo_map.keys())
        last_val = round(elo_map[actual[-1]], 1) if actual else None
        prev_val = round(elo_map[actual[-2]], 1) if len(actual) >= 2 else None
        delta    = round(last_val - prev_val, 1) if last_val is not None and prev_val is not None else None

        teams.append({
            "name":        name,
            "region":      region,
            "finalElo":    float(row["elo"]),
            "rank":        int(row["rank"]),
            "mapsPlayed":  int(row["maps_played"]),
            "mapsWon":     int(row["maps_won"]),
            "mapsLost":    int(row["maps_lost"]),
            "mapsDrawn":   int(row["maps_drawn"]),
            "winPct":      row["win_pct"],
            "firstEvent":  row["first_event"],
            "lastEvent":   row["last_event"],
            "phaseElo":    phase_elos,
            "phaseEvents": phase_events_list,
            "lastPhaseElo": last_val,
            "phaseDelta":  delta,
            "color":       region_color(region, idx, region_totals[region]),
        })

    phase_labels = [label for label, _ in PHASE_DEFS]
    phase_event_labels = [
        [EVENT_NICE_LABEL.get(e, e) for e in eids]
        for _, eids in PHASE_DEFS
    ]

    return teams, phase_labels, phase_event_labels


# ---------------------------------------------------------------------------
# HTML builder
# ---------------------------------------------------------------------------

def build_html(teams: list[dict], phase_labels: list[str], phase_event_labels: list[list[str]]) -> str:
    phase_labels_json       = json.dumps(phase_labels, ensure_ascii=False)
    phase_event_labels_json = json.dumps(phase_event_labels, ensure_ascii=False)
    teams_json              = json.dumps(
        sorted(teams, key=lambda t: t["finalElo"], reverse=True), ensure_ascii=False
    )

    region_tabs_html = "\n".join(
        f'<button class="tab" data-region="{region}">{REGION_FLAGS.get(region, "")} {region}</button>'
        for region in REGIONS
    )

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OWCS 2025 Phase Elo Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  *, *::before, *::after {{ box-sizing: border-box; }}
  :root {{
    --bg: #08141f;
    --surface: rgba(9, 27, 40, 0.86);
    --surface-2: rgba(12, 35, 52, 0.92);
    --border: rgba(143, 187, 216, 0.16);
    --text: #edf4f7;
    --muted: #8eabbf;
    --accent: #f5a524;
    --accent-soft: rgba(245, 165, 36, 0.16);
    --shadow: 0 18px 50px rgba(0, 0, 0, 0.22);
  }}
  body {{
    margin: 0;
    color: var(--text);
    font-family: "Segoe UI", "Noto Sans KR", sans-serif;
    background:
      radial-gradient(circle at top left, rgba(245, 165, 36, 0.14), transparent 30%),
      radial-gradient(circle at top right, rgba(72, 163, 255, 0.18), transparent 34%),
      linear-gradient(180deg, #07111a 0%, #0b1d2c 100%);
  }}
  .shell {{
    max-width: 1460px;
    margin: 0 auto;
    padding: 28px;
  }}
  header {{
    padding: 28px;
    border: 1px solid var(--border);
    border-radius: 24px;
    background: linear-gradient(135deg, rgba(13, 36, 53, 0.94), rgba(8, 22, 34, 0.9));
    box-shadow: var(--shadow);
  }}
  .eyebrow {{
    color: #f6c15b;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    margin-bottom: 10px;
  }}
  h1 {{
    margin: 0 0 10px;
    font-size: clamp(30px, 5vw, 52px);
    line-height: 1.03;
  }}
  .subtitle {{
    margin: 0;
    color: var(--muted);
    max-width: 900px;
    font-size: 15px;
  }}
  .tabs {{
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 22px;
  }}
  .tab {{
    border: 1px solid var(--border);
    background: rgba(255, 255, 255, 0.03);
    color: var(--muted);
    border-radius: 999px;
    padding: 10px 16px;
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    transition: 0.18s ease;
  }}
  .tab:hover {{
    color: var(--text);
    border-color: rgba(245, 165, 36, 0.36);
    transform: translateY(-1px);
  }}
  .tab.active {{
    color: #08141f;
    background: linear-gradient(135deg, #f5a524, #f2d46e);
    border-color: transparent;
  }}
  .stats {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 14px;
    margin-top: 18px;
  }}
  .stat {{
    padding: 18px 20px;
    border: 1px solid var(--border);
    border-radius: 20px;
    background: var(--surface);
    box-shadow: var(--shadow);
  }}
  .stat .label {{
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: var(--muted);
    margin-bottom: 8px;
  }}
  .stat .value {{
    font-size: 28px;
    font-weight: 800;
  }}
  .layout {{
    display: grid;
    grid-template-columns: minmax(0, 2.1fr) minmax(300px, 0.9fr);
    gap: 18px;
    margin-top: 18px;
  }}
  @media (max-width: 1080px) {{
    .layout {{
      grid-template-columns: 1fr;
    }}
  }}
  .card {{
    border: 1px solid var(--border);
    border-radius: 24px;
    background: var(--surface);
    box-shadow: var(--shadow);
    overflow: hidden;
  }}
  .card-head {{
    padding: 20px 22px 0;
  }}
  .card h2 {{
    margin: 0;
    font-size: 18px;
  }}
  .card p {{
    margin: 6px 0 0;
    color: var(--muted);
    font-size: 13px;
  }}
  .chart-wrap {{
    height: 560px;
    padding: 12px 18px 20px;
  }}
  .events-note {{
    padding: 0 22px 22px;
    color: var(--muted);
    font-size: 12px;
    line-height: 1.6;
  }}
  .top5-list {{
    display: grid;
    gap: 12px;
    padding: 18px;
  }}
  .top5-item {{
    padding: 16px;
    border-radius: 18px;
    background: linear-gradient(135deg, rgba(255,255,255,0.035), rgba(255,255,255,0.02));
    border: 1px solid var(--border);
  }}
  .top5-row {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }}
  .top5-rank {{
    width: 28px;
    height: 28px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 800;
    color: #08141f;
    background: linear-gradient(135deg, #f5a524, #f2d46e);
  }}
  .team-meta {{
    flex: 1;
    min-width: 0;
  }}
  .team-name {{
    font-size: 15px;
    font-weight: 800;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  .team-sub {{
    margin-top: 3px;
    color: var(--muted);
    font-size: 12px;
  }}
  .team-elo {{
    font-size: 24px;
    font-weight: 800;
    text-align: right;
  }}
  .delta {{
    margin-top: 6px;
    font-size: 12px;
    font-weight: 700;
  }}
  .delta.up   {{ color: #74d680; }}
  .delta.down {{ color: #ff8f7a; }}
  .delta.flat {{ color: var(--muted); }}
  .table-card {{
    margin-top: 18px;
  }}
  .table-wrap {{
    overflow: auto;
    padding: 0 18px 18px;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    min-width: 760px;
  }}
  th, td {{
    padding: 14px 12px;
    border-bottom: 1px solid rgba(143, 187, 216, 0.12);
    text-align: left;
    font-size: 13px;
  }}
  th {{
    color: var(--muted);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    position: sticky;
    top: 0;
    background: rgba(8, 20, 31, 0.96);
  }}
  tr:hover td {{
    background: rgba(255, 255, 255, 0.02);
  }}
  .badge {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 9px;
    border-radius: 999px;
    background: rgba(255,255,255,0.05);
    color: var(--text);
    font-size: 12px;
    font-weight: 700;
  }}
</style>
</head>
<body>
  <div class="shell">
    <header>
      <div class="eyebrow">OWCS 2025 Elo Dashboard</div>
      <h1>페이즈별 Elo 흐름과 지역별 Top 5를 한 화면에서</h1>
      <p class="subtitle">6개 토너먼트 페이즈(Stage 1 / Champions Clash / Stage 2 / Midseason Championship / Stage 3 / World Finals) 기준으로 Elo 흐름을 시각화했습니다. 미참가 페이즈는 이전 Elo를 이어받습니다.</p>
      <div class="tabs">
        <button class="tab active" data-region="all">{REGION_FLAGS["all"]} Global</button>
        {region_tabs_html}
      </div>
    </header>

    <section class="stats" id="stats"></section>

    <section class="layout">
      <article class="card">
        <div class="card-head">
          <h2 id="chartTitle">Global Phase Elo</h2>
          <p id="chartSubtitle">최종 Elo 기준 상위 팀들의 페이즈별 라인</p>
        </div>
        <div class="chart-wrap">
          <canvas id="eloChart"></canvas>
        </div>
        <div class="events-note" id="eventsNote"></div>
      </article>

      <article class="card">
        <div class="card-head">
          <h2 id="topTitle">Top 5</h2>
          <p id="topSubtitle">선택한 지역의 최신 Elo 기준</p>
        </div>
        <div class="top5-list" id="top5List"></div>
      </article>
    </section>

    <article class="card table-card">
      <div class="card-head">
        <h2 id="tableTitle">Regional Rankings Table</h2>
        <p>필터된 지역 전체 팀 목록입니다.</p>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Rank</th>
              <th>Team</th>
              <th>Region</th>
              <th>Final Elo</th>
              <th>Phase Δ</th>
              <th>Maps</th>
              <th>Record</th>
              <th>Win%</th>
            </tr>
          </thead>
          <tbody id="tableBody"></tbody>
        </table>
      </div>
    </article>
  </div>

<script>
const PHASE_LABELS       = {phase_labels_json};
const PHASE_EVENT_LABELS = {phase_event_labels_json};
const ALL_TEAMS          = {teams_json};

let currentRegion = 'all';
let eloChart      = null;

function visibleTeams(region) {{
  const teams = region === 'all'
    ? ALL_TEAMS
    : ALL_TEAMS.filter(t => t.region === region);
  return [...teams].sort((a, b) => b.finalElo - a.finalElo);
}}

function alpha(hex, opacity) {{
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${{r}}, ${{g}}, ${{b}}, ${{opacity}})`;
}}

function formatDelta(value) {{
  if (value === null || value === undefined) return {{ text: 'new', cls: 'flat' }};
  if (value > 0) return {{ text: `+${{value.toFixed(1)}}`, cls: 'up' }};
  if (value < 0) return {{ text: `${{value.toFixed(1)}}`, cls: 'down' }};
  return {{ text: '0.0', cls: 'flat' }};
}}

function renderStats(teams, region) {{
  const highest  = teams[0];
  const avg      = teams.length
    ? (teams.reduce((s, t) => s + t.finalElo, 0) / teams.length).toFixed(1)
    : '0.0';
  const inFinals = teams.filter(t => t.phaseEvents[4] && t.phaseEvents[4].length > 0).length;
  const label    = region === 'all' ? 'Global' : region;
  document.getElementById('stats').innerHTML = `
    <div class="stat"><div class="label">${{label}} Teams</div><div class="value">${{teams.length}}</div></div>
    <div class="stat"><div class="label">Highest Elo</div><div class="value">${{highest ? highest.finalElo.toFixed(1) : '0.0'}}</div></div>
    <div class="stat"><div class="label">Average Elo</div><div class="value">${{avg}}</div></div>
    <div class="stat"><div class="label">Reached Finals</div><div class="value">${{inFinals}}</div></div>
  `;
}}

function renderChart(teams, region) {{
  const limit      = region === 'all' ? 12 : Math.min(10, teams.length);
  const chartTeams = teams.slice(0, limit);

  const datasets = chartTeams.map(team => ({{
    label:              team.name,
    data:               team.phaseElo,
    borderColor:        team.color,
    backgroundColor:    alpha(team.color, 0.14),
    pointBackgroundColor: team.color,
    pointBorderColor:   '#08141f',
    pointBorderWidth:   1.5,
    pointRadius:        5,
    pointHoverRadius:   8,
    borderWidth:        2.4,
    tension:            0,
    spanGaps:           true,
    fill:               false,
  }}));

  document.getElementById('chartTitle').textContent =
    `${{region === 'all' ? 'Global' : region}} Phase Elo`;
  document.getElementById('chartSubtitle').textContent =
    `최종 Elo 상위 ${{chartTeams.length}}팀 기준 5개 페이즈 추세`;

  if (eloChart) eloChart.destroy();
  eloChart = new Chart(document.getElementById('eloChart'), {{
    type: 'line',
    data: {{ labels: PHASE_LABELS, datasets }},
    options: {{
      responsive:          true,
      maintainAspectRatio: false,
      interaction: {{
        mode:      'nearest',
        intersect: false,
        axis:      'xy',
      }},
      plugins: {{
        legend: {{
          position: 'bottom',
          labels: {{
            color:          '#c7d8e5',
            usePointStyle:  true,
            boxWidth:       8,
            padding:        16,
          }},
        }},
        tooltip: {{
          mode:            'nearest',
          intersect:       false,
          backgroundColor: 'rgba(8, 20, 31, 0.95)',
          borderColor:     'rgba(143, 187, 216, 0.18)',
          borderWidth:     1,
          titleColor:      '#ffffff',
          bodyColor:       '#d5e4ee',
          padding:         12,
          callbacks: {{
            title(items) {{
              if (!items.length) return '';
              const phaseName = PHASE_LABELS[items[0].dataIndex];
              return [items[0].dataset.label, phaseName];
            }},
            label(ctx) {{
              if (ctx.raw === null || ctx.raw === undefined) return null;
              return ` Elo: ${{ctx.raw.toFixed(1)}}`;
            }},
            afterLabel(ctx) {{
              if (ctx.raw === null || ctx.raw === undefined) return null;
              const team   = ALL_TEAMS.find(t => t.name === ctx.dataset.label);
              if (!team) return null;
              const events = team.phaseEvents[ctx.dataIndex];
              if (!events || events.length === 0) return ' Not active this phase';
              return [' Events:', ...events.map(e => ` · ${{e}}`)];
            }},
          }},
        }},
      }},
      scales: {{
        x: {{
          grid:  {{ color: 'rgba(255,255,255,0.05)' }},
          ticks: {{ color: '#8eabbf', font: {{ weight: '600' }} }},
        }},
        y: {{
          grid:  {{ color: 'rgba(255,255,255,0.07)' }},
          ticks: {{ color: '#8eabbf' }},
        }},
      }},
    }},
  }});

  // Events note below chart
  const note = PHASE_LABELS.map((label, i) => {{
    const evs = PHASE_EVENT_LABELS[i];
    return `<strong>${{label}}</strong>: ${{evs.join(' / ')}}`;
  }}).join('<br>');
  document.getElementById('eventsNote').innerHTML = note;
}}

function renderTop5(teams, region) {{
  const top5 = teams.slice(0, 5);
  document.getElementById('topTitle').textContent    = `${{region === 'all' ? 'Global' : region}} Top 5`;
  document.getElementById('topSubtitle').textContent = '최신 페이즈 스냅샷과 이전 페이즈 대비 변동';
  document.getElementById('top5List').innerHTML = top5.map((team, i) => {{
    const delta = formatDelta(team.phaseDelta);
    return `
      <div class="top5-item">
        <div class="top5-row">
          <div class="top5-rank">${{i + 1}}</div>
          <div class="team-meta">
            <div class="team-name">${{team.name}}</div>
            <div class="team-sub">${{team.region}} · ${{team.mapsWon}}W-${{team.mapsLost}}L-${{team.mapsDrawn}}D · ${{team.winPct}}</div>
          </div>
          <div class="team-elo" style="color:${{team.color}}">${{team.finalElo.toFixed(1)}}</div>
        </div>
        <div class="delta ${{delta.cls}}">Phase delta: ${{delta.text}}</div>
      </div>
    `;
  }}).join('');
}}

function renderTable(teams, region) {{
  document.getElementById('tableTitle').textContent = `${{region === 'all' ? 'Global' : region}} Rankings Table`;
  document.getElementById('tableBody').innerHTML = teams.map(team => {{
    const delta = formatDelta(team.phaseDelta);
    return `
      <tr>
        <td>${{team.rank}}</td>
        <td style="font-weight:800;color:${{team.color}}">${{team.name}}</td>
        <td><span class="badge">${{team.region}}</span></td>
        <td>${{team.finalElo.toFixed(1)}}</td>
        <td class="${{delta.cls}}">${{delta.text}}</td>
        <td>${{team.mapsPlayed}}</td>
        <td>${{team.mapsWon}}-${{team.mapsLost}}-${{team.mapsDrawn}}</td>
        <td>${{team.winPct}}</td>
      </tr>
    `;
  }}).join('');
}}

function render(region) {{
  currentRegion = region;
  const teams   = visibleTeams(region);
  renderStats(teams, region);
  renderChart(teams, region);
  renderTop5(teams, region);
  renderTable(teams, region);
}}

document.querySelectorAll('.tab').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    render(btn.dataset.region);
  }});
}});

render('all');
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print("Loading phase Elo dashboard data...")
    teams, phase_labels, phase_event_labels = load_data()
    print(f"  Teams loaded  : {len(teams)}")
    print(f"  Phases defined: {len(phase_labels)}")
    for i, label in enumerate(phase_labels):
        cnt = sum(1 for t in teams if any(t["phaseEvents"][i]))
        print(f"    [{i+1}] {label:<24} — {cnt} teams active")

    print("Building HTML...")
    html = build_html(teams, phase_labels, phase_event_labels)
    OUTPUT_HTML.write_text(html, encoding="utf-8")

    print(f"  Generated     : {OUTPUT_HTML}")
    print("Open the HTML file in a browser to explore the dashboard.")


if __name__ == "__main__":
    main()
