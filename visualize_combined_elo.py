"""
OWCS 2024+2025 Combined Elo — Focused Team Chart

Generates a single-chart HTML showing Elo Rating trajectories for
14 selected teams across the combined 2024 and 2025 OWCS seasons.

Usage:
    python visualize_combined_elo.py
"""

from __future__ import annotations

import colorsys
import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT          = Path(__file__).resolve().parent
HISTORY_2024  = ROOT / "OWCS_2024_GLOBAL_ELO_HISTORY.csv"
HISTORY_2025  = ROOT / "OWCS_2025_GLOBAL_ELO_HISTORY.csv"
OUTPUT_HTML   = ROOT / "OWCS_COMBINED_ELO.html"

# ---------------------------------------------------------------------------
# Target teams (user-specified 14 teams, canonical names in data)
# ---------------------------------------------------------------------------

TARGET_TEAMS: dict[str, str] = {
    # canonical_data_name → display_name
    "Crazy Raccoon":       "Crazy Raccoon",
    "Team Falcons":        "Team Falcons",
    "ZETA DIVISION":       "ZETA DIVISION",
    "T1":                  "T1",
    "VARREL":              "VARREL",
    "Please Not Hero Ban": "Please Not Hero Ban",
    "Weibo Gaming":        "Weibo Gaming",
    "Team CC":             "Team CC (→JDG 2026)",
    "Twisted Minds":       "Twisted Minds",
    "Team Peps":           "Team Peps",
    "Virtus.pro":          "Virtus.pro",
    "Al Qadsiah":          "Al Qadsiah",
    "Team Liquid":         "Team Liquid",
    "Spacestation Gaming": "Spacestation Gaming",
}

# ---------------------------------------------------------------------------
# Combined phase definitions (2024 + 2025, 11 phases total)
# ---------------------------------------------------------------------------

PHASE_DEFS: list[tuple[str, list[str]]] = [
    ("2024 S1+S2", [
        "owcs_2024_asia_s1_pacific",
        "owcs_2024_na_s1_groups",
        "owcs_2024_emea_s1_groups",
        "owcs_2024_na_s1_main",
        "owcs_2024_emea_s1_main",
        "owcs_2024_asia_s1_japan",
        "owcs_2024_asia_s1_korea",
        "owcs_2024_asia_s1_wildcard",
        "owcs_2024_asia_s1_main",
        "owcs_2024_na_s2_groups",
        "owcs_2024_emea_s2_groups",
        "owcs_2024_na_s2_main",
        "owcs_2024_emea_s2_main",
    ]),
    ("Dallas\nMajor", [
        "owcs_2024_dallas_major",
    ]),
    ("EWC 2024", [
        "ewc_2024",
    ]),
    ("2024 S3–S4", [
        "owcs_2024_asia_s2_pacific",
        "owcs_2024_na_s3_groups",
        "owcs_2024_emea_s3_groups",
        "owcs_2024_na_s3_main",
        "owcs_2024_emea_s3_main",
        "owcs_2024_asia_s2_korea",
        "owcs_2024_asia_s2_japan",
        "owcs_2024_asia_s2_wildcard",
        "owcs_2024_na_s4_groups",
        "owcs_2024_emea_s4_groups",
        "owcs_2024_asia_s2_main",
        "owcs_2024_na_s4_main",
        "owcs_2024_emea_s4_main",
    ]),
    ("2024\nWorld Finals", [
        "owcs_2024_world_finals",
    ]),
    # ── 2025 ──
    ("2025 Stage 1", [
        "owcs_2025_asia_s1_japan",
        "owcs_2025_asia_s1_pacific",
        "owcs_2025_asia_s1_korea",
        "owcs_2025_na_s1",
        "owcs_2025_emea_s1",
        "owcs_2025_asia_s1_main",
        "owcs_2025_china_s1",
    ]),
    ("Champions\nClash", [
        "owcs_2025_champions_clash",
    ]),
    ("2025 Stage 2", [
        "owcs_2025_asia_s2_korea",
        "owcs_2025_na_s2",
        "owcs_2025_emea_s2",
        "owcs_2025_asia_s2_japan",
        "owcs_2025_asia_s2_pacific",
        "owcs_2025_china_s2",
    ]),
    ("Midseason\nChampionship", [
        "owcs_2025_midseason",
    ]),
    ("2025 Stage 3", [
        "owcs_2025_asia_s3_japan",
        "owcs_2025_asia_s3_pacific",
        "owcs_2025_asia_s3_korea",
        "owcs_2025_na_s3",
        "owcs_2025_emea_s3",
        "owcs_2025_china_s3",
        "owcs_2025_apac_championship",
        "owcs_2025_korea_road_to_wf",
    ]),
    ("2025\nWorld Finals", [
        "owcs_2025_world_finals",
    ]),
]

# Index of last 2024 phase (0-based) — used to draw the year boundary line
BOUNDARY_AFTER_PHASE = 4   # after "2024 World Finals"

# ---------------------------------------------------------------------------
# Team colors — fixed per team for visual consistency
# ---------------------------------------------------------------------------

TEAM_COLORS: dict[str, str] = {
    "Crazy Raccoon":       "#E30613",
    "Team Falcons":        "#00A651",
    "ZETA DIVISION":       "#000000",
    "T1":                  "#E2012D",
    "VARREL":              "#00B1EB",
    "Please Not Hero Ban": "#A8E6CF",
    "Weibo Gaming":        "#FF4500",
    "Team CC":             "#C8102E",
    "Twisted Minds":       "#FA4B68",
    "Team Peps":           "#FEF100",
    "Virtus.pro":          "#F65101",
    "Al Qadsiah":          "#FDE100",
    "Team Liquid":         "#00274D",
    "Spacestation Gaming": "#FDB827",
}


def _hsl_to_hex(h: float, s: float, l: float) -> str:
    r, g, b = colorsys.hls_to_rgb(h / 360, l, s)
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data() -> list[dict]:
    """
    Load both 2024 and 2025 history CSVs, combine, filter to TARGET_TEAMS,
    and compute per-phase Elo with carry-forward.
    Returns list of team dicts ready for JSON serialization.
    """
    # Build event → phase index mapping
    event_to_phase: dict[str, int] = {}
    for phase_idx, (_, eids) in enumerate(PHASE_DEFS):
        for eid in eids:
            event_to_phase[eid] = phase_idx

    num_phases = len(PHASE_DEFS)

    # Track last Elo per (team, phase_idx)
    team_phase_elo: dict[str, dict[int, float]] = defaultdict(dict)

    def process_csv(path: Path) -> None:
        if not path.exists():
            print(f"  [WARN] {path.name} not found — skipping")
            return
        for row in csv.DictReader(path.open(encoding="utf-8")):
            team = row["team"]
            if team not in TARGET_TEAMS:
                continue
            eid   = row["event_id"]
            phase = event_to_phase.get(eid)
            if phase is None:
                continue
            team_phase_elo[team][phase] = float(row["elo_after"])

    process_csv(HISTORY_2024)
    process_csv(HISTORY_2025)

    # Build team dataset list
    results: list[dict] = []
    for canonical, display in TARGET_TEAMS.items():
        elo_map  = team_phase_elo.get(canonical, {})

        # Phase Elo with carry-forward (None = team not yet active)
        phase_elos: list[float | None] = []
        current: float | None = None
        first_seen = False
        for i in range(num_phases):
            if i in elo_map:
                current    = round(elo_map[i], 1)
                first_seen = True
            elif not first_seen:
                current = None   # team hasn't appeared yet → no line
            phase_elos.append(current)

        # Final Elo = last non-None value
        final_elo = next(
            (v for v in reversed(phase_elos) if v is not None), None
        )

        results.append({
            "name":      display,
            "canonical": canonical,
            "color":     TEAM_COLORS.get(canonical, "#aaaaaa"),
            "phaseElo":  phase_elos,
            "finalElo":  final_elo,
        })

    # Sort by final Elo descending for legend ordering
    results.sort(key=lambda t: (t["finalElo"] or 0), reverse=True)
    return results


# ---------------------------------------------------------------------------
# HTML builder
# ---------------------------------------------------------------------------

def build_html(teams: list[dict]) -> str:
    phase_labels = [label for label, _ in PHASE_DEFS]

    teams_json        = json.dumps(teams, ensure_ascii=False)
    phase_labels_json = json.dumps(phase_labels, ensure_ascii=False)
    boundary_idx      = BOUNDARY_AFTER_PHASE   # vertical line after this x-index

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OWCS 2024+2025 Combined Elo</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  *, *::before, *::after {{ box-sizing: border-box; }}
  :root {{
    --bg: #ffffff;
    --surface: #ffffff;
    --border: rgba(0, 0, 0, 0.12);
    --text: #1a1a1a;
    --muted: #555555;
    --accent: #2563eb;
    --shadow: 0 4px 20px rgba(0,0,0,0.08);
  }}
  body {{
    margin: 0;
    background: #f5f7fa;
    color: var(--text);
    font-family: "Segoe UI", "Noto Sans KR", sans-serif;
    min-height: 100vh;
  }}
  .shell {{
    max-width: 1400px;
    margin: 0 auto;
    padding: 32px 24px;
  }}
  header {{
    padding: 28px 32px;
    border: 1px solid var(--border);
    border-radius: 20px;
    background: #ffffff;
    box-shadow: var(--shadow);
    margin-bottom: 20px;
  }}
  .eyebrow {{
    color: #2563eb;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    margin-bottom: 8px;
  }}
  h1 {{
    margin: 0 0 8px;
    font-size: clamp(22px, 4vw, 40px);
    line-height: 1.1;
    color: #111111;
  }}
  .subtitle {{
    margin: 0;
    color: var(--muted);
    font-size: 14px;
  }}
  .card {{
    border: 1px solid var(--border);
    border-radius: 20px;
    background: #ffffff;
    box-shadow: var(--shadow);
    padding: 24px;
    margin-bottom: 20px;
  }}
  .card h2 {{
    margin: 0 0 4px;
    font-size: 16px;
    font-weight: 700;
    color: #111111;
  }}
  .card .desc {{
    margin: 0 0 18px;
    color: var(--muted);
    font-size: 13px;
  }}
  .chart-wrap {{
    position: relative;
    height: 620px;
  }}
  .legend-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 10px;
    margin-top: 22px;
  }}
  .legend-item {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    border: 1px solid var(--border);
    border-radius: 12px;
    background: #fafafa;
    font-size: 13px;
    cursor: pointer;
    transition: background 0.15s;
  }}
  .legend-item:hover {{
    background: #f0f0f0;
  }}
  .legend-item.hidden {{
    opacity: 0.35;
  }}
  .dot {{
    width: 12px;
    height: 12px;
    border-radius: 50%;
    flex-shrink: 0;
    border: 1px solid rgba(0,0,0,0.15);
  }}
  .legend-name {{
    flex: 1;
    font-weight: 600;
    color: #1a1a1a;
  }}
  .legend-elo {{
    color: var(--muted);
    font-size: 12px;
    font-weight: 700;
  }}
  .note {{
    margin-top: 18px;
    padding: 14px 18px;
    border: 1px solid rgba(37,99,235,0.2);
    border-radius: 12px;
    background: rgba(37,99,235,0.04);
    color: var(--muted);
    font-size: 12.5px;
    line-height: 1.7;
  }}
</style>
</head>
<body>
<div class="shell">

<header>
  <div class="eyebrow">OWCS Elo Rating — 통합 시즌 차트</div>
  <h1>2024 + 2025 Combined Elo Trajectory</h1>
  <p class="subtitle">
    선택된 14개 팀의 Elo Rating 변화 &mdash;
    2024 S1부터 2025 World Finals까지 (11 phases) &middot;
    수직 점선: 2024 / 2025 시즌 경계
  </p>
</header>

<div class="card">
  <h2>Phase Elo Trend</h2>
  <p class="desc">각 Phase 종료 시점의 Elo. 클릭하여 팀 ON/OFF</p>
  <div class="chart-wrap">
    <canvas id="chart"></canvas>
  </div>
  <div class="legend-grid" id="legend"></div>
  <div class="note">
    <strong>⚠️ 표기 안내:</strong>
    "Team CC (→JDG 2026)" = 2025 데이터의 Team CC (2026 시즌에 JDG Gaming으로 리브랜딩 예정) &middot;
    T1 / Weibo Gaming / Team Liquid / Please Not Hero Ban = 2025 신규 팀 (2024 미참가, 1400에서 출발) &middot;
    Al Qadsiah = 2024 EMEA S3부터 등장
  </div>
</div>

</div>

<script>
const PHASES = {phase_labels_json};
const TEAMS  = {teams_json};
const BOUNDARY_AFTER = {boundary_idx};  // draw vertical line after this phase index

// ── Build datasets ──────────────────────────────────────────────────────────
const datasets = TEAMS.map(t => ({{
  label:           t.name,
  data:            t.phaseElo,
  borderColor:     t.color,
  backgroundColor: t.color + "28",
  borderWidth:     2.5,
  pointRadius:     5,
  pointHoverRadius: 8,
  pointBackgroundColor: t.color,
  tension:         0,
  spanGaps:        false,   // don't connect across null (team not yet active)
}}));

// ── Custom plugin: year-boundary vertical line ──────────────────────────────
const boundaryPlugin = {{
  id: "yearBoundary",
  afterDraw(chart) {{
    const {{ ctx, chartArea: {{ top, bottom }}, scales: {{ x }} }} = chart;
    // Draw line between index BOUNDARY_AFTER and BOUNDARY_AFTER+1
    const xPos = (x.getPixelForValue(BOUNDARY_AFTER) + x.getPixelForValue(BOUNDARY_AFTER + 1)) / 2;
    ctx.save();
    ctx.beginPath();
    ctx.setLineDash([6, 4]);
    ctx.strokeStyle = "rgba(245, 165, 36, 0.55)";
    ctx.lineWidth   = 1.5;
    ctx.moveTo(xPos, top);
    ctx.lineTo(xPos, bottom);
    ctx.stroke();
    // Labels
    ctx.setLineDash([]);
    ctx.fillStyle = "rgba(245, 165, 36, 0.75)";
    ctx.font      = "bold 11px Segoe UI, sans-serif";
    ctx.textAlign = "right";
    ctx.fillText("2024", xPos - 6, top + 16);
    ctx.textAlign = "left";
    ctx.fillText("2025", xPos + 6, top + 16);
    ctx.restore();
  }},
}};

// ── Chart ────────────────────────────────────────────────────────────────────
const ctx = document.getElementById("chart").getContext("2d");
const chart = new Chart(ctx, {{
  type: "line",
  data: {{ labels: PHASES, datasets }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    interaction: {{ mode: "nearest", intersect: true }},
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{
        backgroundColor: "rgba(255,255,255,0.97)",
        borderColor: "rgba(0,0,0,0.15)",
        borderWidth: 1,
        titleColor: "#111111",
        bodyColor: "#333333",
        padding: 14,
        callbacks: {{
          label(ctx) {{
            const v = ctx.parsed.y;
            if (v === null) return null;
            return ` ${{ctx.dataset.label}}: ${{v.toFixed(1)}}`;
          }},
        }},
      }},
    }},
    scales: {{
      x: {{
        grid:  {{ color: "rgba(0,0,0,0.07)" }},
        ticks: {{ color: "#555555", font: {{ size: 11 }} }},
      }},
      y: {{
        grid:  {{ color: "rgba(0,0,0,0.07)" }},
        ticks: {{
          color: "#555555",
          font:  {{ size: 11 }},
          callback: v => v.toFixed(0),
        }},
        title: {{
          display: true,
          text:    "Elo Rating",
          color:   "#555555",
          font:    {{ size: 12 }},
        }},
      }},
    }},
  }},
  plugins: [boundaryPlugin],
}});

// ── Custom legend ────────────────────────────────────────────────────────────
const legendEl = document.getElementById("legend");
TEAMS.forEach((t, i) => {{
  const item = document.createElement("div");
  item.className = "legend-item";
  item.dataset.idx = i;
  item.innerHTML = `
    <span class="dot" style="background:${{t.color}}"></span>
    <span class="legend-name">${{t.name}}</span>
    <span class="legend-elo">${{t.finalElo !== null ? t.finalElo.toFixed(1) : "—"}}</span>
  `;
  item.addEventListener("click", () => {{
    const meta = chart.getDatasetMeta(i);
    meta.hidden = !meta.hidden;
    item.classList.toggle("hidden", meta.hidden);
    chart.update();
  }});
  legendEl.appendChild(item);
}});
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=== OWCS Combined Elo Chart ===")
    print(f"  2024 history : {HISTORY_2024.name}")
    print(f"  2025 history : {HISTORY_2025.name}")
    print(f"  Target teams : {len(TARGET_TEAMS)}")
    print(f"  Phases       : {len(PHASE_DEFS)}")

    teams = load_data()

    print("\n  Team final Elo (sorted):")
    for t in teams:
        elo_str = f"{t['finalElo']:.1f}" if t["finalElo"] else "N/A"
        print(f"    {t['name']:<32} {elo_str}")

    html = build_html(teams)
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"\n  Generated: {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
