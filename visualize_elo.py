"""
OWCS 2024 Elo Dashboard — Monthly HTML Generator

Builds a self-contained dashboard with:
  - Region tabs: Global / Korea / Japan / Pacific / NA / EMEA
  - Monthly Elo trend lines based on tournament result timing
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
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FINAL_CSV = ROOT / "OWCS_2024_GLOBAL_ELO_FINAL.csv"
HISTORY_CSV = ROOT / "OWCS_2024_GLOBAL_ELO_HISTORY.csv"
OUTPUT_HTML = ROOT / "OWCS_2024_ELO_DASHBOARD.html"

REGIONS = ["Korea", "Japan", "Pacific", "NA", "EMEA"]
REGION_FLAGS = {
    "all": "🌐",
    "Korea": "🇰🇷",
    "Japan": "🇯🇵",
    "Pacific": "🌏",
    "NA": "🇺🇸",
    "EMEA": "🌍",
}
REGION_HUE = {
    "Korea": 0,
    "Japan": 325,
    "Pacific": 195,
    "NA": 132,
    "EMEA": 272,
    "Intl": 36,
}

EVENT_SCHEDULE = [
    ("owcs_2024_asia_s1_pacific", "2024-03-03"),
    ("owcs_2024_na_s1_groups", "2024-03-17"),
    ("owcs_2024_emea_s1_groups", "2024-03-17"),
    ("owcs_2024_na_s1_main", "2024-03-21"),
    ("owcs_2024_emea_s1_main", "2024-03-21"),
    ("owcs_2024_asia_s1_japan", "2024-03-24"),
    ("owcs_2024_asia_s1_korea", "2024-03-28"),
    ("owcs_2024_asia_s1_wildcard", "2024-04-08"),
    ("owcs_2024_na_s2_groups", "2024-04-12"),
    ("owcs_2024_emea_s2_groups", "2024-04-12"),
    ("owcs_2024_asia_s1_main", "2024-04-25"),
    ("owcs_2024_na_s2_main", "2024-04-25"),
    ("owcs_2024_emea_s2_main", "2024-04-25"),
    ("owcs_2024_dallas_major", "2024-05-31"),
    ("faceit_2024_s1_na_master", "2024-06-14"),
    ("faceit_2024_s1_emea_master", "2024-06-14"),
    ("ewc_2024", "2024-07-26"),
    ("owcs_2024_asia_s2_pacific", "2024-08-08"),
    ("owcs_2024_na_s3_groups", "2024-08-16"),
    ("owcs_2024_emea_s3_groups", "2024-08-16"),
    ("owcs_2024_na_s3_main", "2024-08-29"),
    ("owcs_2024_emea_s3_main", "2024-08-29"),
    ("owcs_2024_asia_s2_korea", "2024-08-30"),
    ("owcs_2024_asia_s2_japan", "2024-09-02"),
    ("faceit_2024_s2_na_master", "2024-09-13"),
    ("faceit_2024_s2_emea_master", "2024-09-13"),
    ("owcs_2024_asia_s2_wildcard", "2024-09-13"),
    ("owcs_2024_na_s4_groups", "2024-09-27"),
    ("owcs_2024_emea_s4_groups", "2024-09-27"),
    ("owcs_2024_asia_s2_main", "2024-09-27"),
    ("owcs_2024_na_s4_main", "2024-10-10"),
    ("owcs_2024_emea_s4_main", "2024-10-10"),
    ("faceit_2024_s3_na_master", "2024-10-18"),
    ("faceit_2024_s3_emea_master", "2024-10-18"),
    ("owcs_2024_world_finals", "2024-11-22"),
]


def _hsl_to_hex(h: float, s: float, l: float) -> str:
    r, g, b = colorsys.hls_to_rgb(h / 360, l, s)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def region_color(region: str, idx: int = 0, total: int = 1) -> str:
    hue = REGION_HUE.get(region, 180)
    steps = max(total, 1)
    lightness = 0.44 + 0.28 * (idx / steps)
    saturation = 0.78 - 0.12 * (idx % 2)
    return _hsl_to_hex(hue, saturation, lightness)


def month_label(month_key: str) -> str:
    return datetime.strptime(month_key, "%Y-%m").strftime("%b %Y")


def short_event_label(event_id: str) -> str:
    text = event_id.replace("owcs_2024_", "").replace("faceit_2024_", "faceit_")
    return (
        text.replace("_asia_", " asia ")
        .replace("_world_finals", " world finals")
        .replace("_dallas_major", " dallas major")
        .replace("_", " ")
        .title()
    )


def load_data() -> tuple[list[dict], list[str], dict[str, list[str]]]:
    final_rows = list(csv.DictReader(FINAL_CSV.open(encoding="utf-8")))
    history_rows = list(csv.DictReader(HISTORY_CSV.open(encoding="utf-8")))

    event_dates: dict[str, str] = dict(EVENT_SCHEDULE)
    month_events: dict[str, list[tuple[str, str]]] = defaultdict(list)
    event_months = sorted({date[:7] for date in event_dates.values()})
    for event_id, date_value in sorted(event_dates.items(), key=lambda item: item[1]):
        month_key = date_value[:7]
        month_events[month_key].append((date_value, short_event_label(event_id)))

    team_event_elo: dict[str, dict[str, float]] = defaultdict(dict)
    for row in history_rows:
        team_event_elo[row["team"]][row["event_id"]] = float(row["elo_after"])

    team_event_month_elo: dict[str, dict[str, float]] = defaultdict(dict)
    for team, event_elos in team_event_elo.items():
        last_for_month: dict[str, tuple[str, float]] = {}
        for event_id, elo in event_elos.items():
            date_value = event_dates.get(event_id)
            if not date_value:
                continue
            month_key = date_value[:7]
            previous = last_for_month.get(month_key)
            if previous is None or date_value >= previous[0]:
                last_for_month[month_key] = (date_value, elo)
        team_event_month_elo[team] = {
            month_key: round(value[1], 1) for month_key, value in last_for_month.items()
        }

    teams: list[dict] = []
    region_totals: dict[str, int] = defaultdict(int)
    for row in final_rows:
        region_totals[row["home_region"]] += 1

    region_index: dict[str, int] = defaultdict(int)
    for row in sorted(final_rows, key=lambda item: float(item["elo"]), reverse=True):
        name = row["team"]
        region = row["home_region"]
        idx = region_index[region]
        region_index[region] += 1

        monthly_points: list[float | None] = []
        current: float | None = None
        month_map = team_event_month_elo.get(name, {})
        for month_key in event_months:
            if month_key in month_map:
                current = month_map[month_key]
            monthly_points.append(current)

        last_value = next((v for v in reversed(monthly_points) if v is not None), None)
        prev_value = next(
            (monthly_points[i] for i in range(len(monthly_points) - 2, -1, -1) if monthly_points[i] is not None),
            None,
        )
        delta = round(last_value - prev_value, 1) if last_value is not None and prev_value is not None else None

        teams.append(
            {
                "name": name,
                "region": region,
                "finalElo": float(row["elo"]),
                "rank": int(row["rank"]),
                "mapsPlayed": int(row["maps_played"]),
                "mapsWon": int(row["maps_won"]),
                "mapsLost": int(row["maps_lost"]),
                "mapsDrawn": int(row["maps_drawn"]),
                "winPct": row["win_pct"],
                "firstEvent": row["first_event"],
                "lastEvent": row["last_event"],
                "monthlyElo": monthly_points,
                "lastMonthlyElo": last_value,
                "monthlyDelta": delta,
                "color": region_color(region, idx, region_totals[region]),
            }
        )

    month_event_labels = {
        month: [f"{date_value}  {label}" for date_value, label in items]
        for month, items in month_events.items()
    }

    return teams, event_months, month_event_labels


def build_html(teams: list[dict], months: list[str], month_event_labels: dict[str, list[str]]) -> str:
    month_labels_json = json.dumps([month_label(month) for month in months], ensure_ascii=False)
    month_event_labels_json = json.dumps(month_event_labels, ensure_ascii=False)
    teams_json = json.dumps(sorted(teams, key=lambda item: item["finalElo"], reverse=True), ensure_ascii=False)

    region_tabs_html = "\n".join(
        f'<button class="tab" data-region="{region}">{REGION_FLAGS.get(region, "")} {region}</button>'
        for region in REGIONS
    )

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OWCS 2024 Monthly Elo Dashboard</title>
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
  .delta.up {{ color: #74d680; }}
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
    min-width: 900px;
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
      <div class="eyebrow">OWCS 2024 Elo Dashboard</div>
      <h1>월별 Elo 흐름과 지역별 Top 5를 한 화면에서</h1>
      <p class="subtitle">대회가 끝난 시점을 기준으로 팀 Elo를 월 단위로 스냅샷화했습니다. 대회가 없는 달은 마지막 Elo를 이어받아 추세를 볼 수 있게 처리했습니다.</p>
      <div class="tabs">
        <button class="tab active" data-region="all">{REGION_FLAGS["all"]} Global</button>
        {region_tabs_html}
      </div>
    </header>

    <section class="stats" id="stats"></section>

    <section class="layout">
      <article class="card">
        <div class="card-head">
          <h2 id="chartTitle">Global Monthly Elo</h2>
          <p id="chartSubtitle">최종 Elo 기준 상위 팀들의 월별 라인</p>
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
              <th>Latest Monthly Elo</th>
              <th>Monthly Delta</th>
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
const MONTH_LABELS = {month_labels_json};
const MONTH_EVENTS = {month_event_labels_json};
const ALL_TEAMS = {teams_json};

let currentRegion = 'all';
let eloChart = null;

function visibleTeams(region) {{
  const teams = region === 'all'
    ? ALL_TEAMS
    : ALL_TEAMS.filter(team => team.region === region);
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
  const highest = teams[0];
  const avg = teams.length
    ? (teams.reduce((sum, team) => sum + team.finalElo, 0) / teams.length).toFixed(1)
    : '0.0';
  const active = teams.filter(team => team.lastMonthlyElo !== null).length;
  const label = region === 'all' ? 'Global' : region;
  document.getElementById('stats').innerHTML = `
    <div class="stat"><div class="label">${{label}} Teams</div><div class="value">${{teams.length}}</div></div>
    <div class="stat"><div class="label">Highest Elo</div><div class="value">${{highest ? highest.finalElo.toFixed(1) : '0.0'}}</div></div>
    <div class="stat"><div class="label">Average Elo</div><div class="value">${{avg}}</div></div>
    <div class="stat"><div class="label">Tracked Monthly</div><div class="value">${{active}}</div></div>
  `;
}}

function renderChart(teams, region) {{
  const limit = region === 'all' ? 12 : Math.min(10, teams.length);
  const chartTeams = teams.slice(0, limit);
  const datasets = chartTeams.map(team => ({{
    label: team.name,
    data: team.monthlyElo,
    borderColor: team.color,
    backgroundColor: alpha(team.color, 0.14),
    pointBackgroundColor: team.color,
    pointBorderColor: '#08141f',
    pointBorderWidth: 1.5,
    pointRadius: 3,
    pointHoverRadius: 5,
    borderWidth: 2.4,
    tension: 0.26,
    spanGaps: true,
    fill: false,
  }}));

  document.getElementById('chartTitle').textContent = `${{region === 'all' ? 'Global' : region}} Monthly Elo`;
  document.getElementById('chartSubtitle').textContent =
    `최종 Elo 상위 ${{chartTeams.length}}팀 기준 월별 추세`;

  if (eloChart) eloChart.destroy();
  eloChart = new Chart(document.getElementById('eloChart'), {{
    type: 'line',
    data: {{
      labels: MONTH_LABELS,
      datasets,
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      interaction: {{
        mode: 'nearest',
        intersect: false,
      }},
      plugins: {{
        legend: {{
          position: 'bottom',
          labels: {{
            color: '#c7d8e5',
            usePointStyle: true,
            boxWidth: 8,
            padding: 16,
          }},
        }},
        tooltip: {{
          backgroundColor: 'rgba(8, 20, 31, 0.95)',
          borderColor: 'rgba(143, 187, 216, 0.18)',
          borderWidth: 1,
          titleColor: '#ffffff',
          bodyColor: '#d5e4ee',
          callbacks: {{
            afterTitle(items) {{
              const idx = items[0].dataIndex;
              const monthKey = Object.keys(MONTH_EVENTS)[idx];
              const events = MONTH_EVENTS[monthKey] || [];
              return events.length ? [' ', 'Events:', ...events] : [' ', 'No recorded event'];
            }},
            label(ctx) {{
              if (ctx.raw === null) return ` ${{ctx.dataset.label}}: debut not yet`;
              return ` ${{ctx.dataset.label}}: ${{ctx.raw.toFixed(1)}}`;
            }},
          }},
        }},
      }},
      scales: {{
        x: {{
          grid: {{
            color: 'rgba(255,255,255,0.05)',
          }},
          ticks: {{
            color: '#8eabbf',
          }},
        }},
        y: {{
          grid: {{
            color: 'rgba(255,255,255,0.07)',
          }},
          ticks: {{
            color: '#8eabbf',
          }},
        }},
      }},
    }},
  }});

  const note = Object.entries(MONTH_EVENTS)
    .map(([month, events]) => `<strong>${{MONTH_LABELS[Object.keys(MONTH_EVENTS).indexOf(month)]}}</strong>: ${{events.join(' / ')}}`)
    .join('<br>');
  document.getElementById('eventsNote').innerHTML = note;
}}

function renderTop5(teams, region) {{
  const top5 = teams.slice(0, 5);
  document.getElementById('topTitle').textContent = `${{region === 'all' ? 'Global' : region}} Top 5`;
  document.getElementById('topSubtitle').textContent = '최신 월별 스냅샷과 마지막 월 대비 변동';
  document.getElementById('top5List').innerHTML = top5.map((team, index) => {{
    const delta = formatDelta(team.monthlyDelta);
    return `
      <div class="top5-item">
        <div class="top5-row">
          <div class="top5-rank">${{index + 1}}</div>
          <div class="team-meta">
            <div class="team-name">${{team.name}}</div>
            <div class="team-sub">${{team.region}} · ${{team.mapsWon}}W-${{team.mapsLost}}L-${{team.mapsDrawn}}D · ${{team.winPct}}</div>
          </div>
          <div class="team-elo" style="color:${{team.color}}">${{team.finalElo.toFixed(1)}}</div>
        </div>
        <div class="delta ${{delta.cls}}">Monthly delta: ${{delta.text}}</div>
      </div>
    `;
  }}).join('');
}}

function renderTable(teams, region) {{
  document.getElementById('tableTitle').textContent = `${{region === 'all' ? 'Global' : region}} Rankings Table`;
  document.getElementById('tableBody').innerHTML = teams.map(team => {{
    const delta = formatDelta(team.monthlyDelta);
    const latest = team.lastMonthlyElo === null ? 'n/a' : team.lastMonthlyElo.toFixed(1);
    return `
      <tr>
        <td>${{team.rank}}</td>
        <td style="font-weight:800;color:${{team.color}}">${{team.name}}</td>
        <td><span class="badge">${{team.region}}</span></td>
        <td>${{team.finalElo.toFixed(1)}}</td>
        <td>${{latest}}</td>
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
  const teams = visibleTeams(region);
  renderStats(teams, region);
  renderChart(teams, region);
  renderTop5(teams, region);
  renderTable(teams, region);
}}

document.querySelectorAll('.tab').forEach(button => {{
  button.addEventListener('click', () => {{
    document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
    button.classList.add('active');
    render(button.dataset.region);
  }});
}});

render('all');
</script>
</body>
</html>"""


def main() -> None:
    print("Loading monthly Elo dashboard data...")
    teams, months, month_event_labels = load_data()
    print(f"  Teams loaded : {len(teams)}")
    print(f"  Months found : {len(months)}")

    print("Building HTML...")
    html = build_html(teams, months, month_event_labels)
    OUTPUT_HTML.write_text(html, encoding="utf-8")

    print(f"  Generated    : {OUTPUT_HTML}")
    print("Open the HTML file in a browser to explore the dashboard.")


if __name__ == "__main__":
    main()
