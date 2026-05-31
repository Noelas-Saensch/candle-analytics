import json
from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from candles.storage.db import query_candles

router = APIRouter()

ANALYZE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Candle Analytics — Analyse</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1a1a2e; color: #e0e0e0; padding: 20px; }
h1 { font-size: 18px; color: #e94560; margin-bottom: 16px; }
a { color: #888; font-size: 12px; text-decoration: none; }
a:hover { color: #e94560; }
.controls { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin-bottom: 16px; }
.controls label { font-size: 11px; color: #888; }
.controls select, .controls input { background: #0f3460; color: #e0e0e0; border: 1px solid #1a3a6b; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
.controls select:focus, .controls input:focus { outline: none; border-color: #e94560; }
.controls input[type=date] { color-scheme: dark; }
.controls .btn { background: #e94560; color: #fff; border: none; padding: 4px 14px; border-radius: 4px; font-size: 12px; cursor: pointer; }
.controls .btn:hover { background: #d63851; }
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th, td { padding: 4px 8px; text-align: right; border-bottom: 1px solid #16213e; }
th { position: sticky; top: 0; background: #16213e; color: #888; font-weight: 500; text-align: right; cursor: pointer; user-select: none; }
th:hover { color: #e0e0e0; }
td:first-child, th:first-child { text-align: left; }
tr:hover { background: #16213e; }
.num { font-variant-numeric: tabular-nums; }
.bar { display: inline-block; height: 10px; border-radius: 2px; vertical-align: middle; }
.stat-row td { padding: 8px; font-weight: 600; }
#status { color: #888; font-size: 12px; margin-bottom: 8px; }
#footer { margin-top: 16px; font-size: 11px; color: #555; }
#metric-filter { background: #0f3460; color: #e0e0e0; border: 1px solid #1a3a6b; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
</style>
</head>
<body>
<h1><a href="/dashboard">&#x2190; Chart</a> &nbsp; Analyse — Percentile Rank</h1>
<div class="controls">
  <label>exchange</label>
  <select id="exchange"></select>
  <label>pair</label>
  <select id="symbol"></select>
  <label>timeframe</label>
  <select id="timeframe">
    <option value="1m">1m</option><option value="5m">5m</option><option value="15m">15m</option>
    <option value="30m">30m</option><option value="1H" selected>1H</option><option value="4H">4H</option>
    <option value="12H">12H</option><option value="1D">1D</option><option value="1W">1W</option><option value="1M">1M</option>
  </select>
  <label>from</label>
  <input type="date" id="startDate">
  <label>to</label>
  <input type="date" id="endDate">
  <label>metric</label>
  <select id="metricFilter">
    <option value="oc">OC%</option><option value="oh">OH%</option><option value="ol">OL%</option>
    <option value="hl">HL%</option><option value="hc">HC%</option><option value="lc">LC%</option>
    <option value="vol">Volume%</option><option value="all" selected>All</option>
  </select>
  <button class="btn" onclick="loadData()">Load</button>
</div>
<div id="status">Select filters and click Load</div>
<div style="overflow-x:auto;max-height:calc(100vh - 160px)">
<table id="table">
  <thead id="thead"></thead>
  <tbody id="tbody"></tbody>
</table>
</div>
<div id="footer"></div>
<script>
const METRICS = {
  oc: { label: 'OC%', desc: '(close-open)/open*100', unit: '%' },
  oh: { label: 'OH%', desc: '(high-open)/open*100', unit: '%' },
  ol: { label: 'OL%', desc: '(low-open)/open*100', unit: '%' },
  hl: { label: 'HL%', desc: '(high-low)/open*100', unit: '%' },
  hc: { label: 'HC%', desc: '(high-close)/open*100', unit: '%' },
  lc: { label: 'LC%', desc: '(low-close)/open*100', unit: '%' },
  vol: { label: 'Vol%', desc: 'volume/maxVolume*100', unit: '%' },
};

function msToDate(ms) {
  const d = new Date(ms);
  return d.toISOString().slice(0, 10);
}

function dateToMs(dateStr) {
  return new Date(dateStr + 'T00:00:00Z').getTime();
}

async function loadPairs() {
  const r = await fetch('/api/pairs');
  const data = await r.json();
  const exchanges = [...new Set(data.pairs.map(p => p.exchange))];
  exchangeEl.innerHTML = exchanges.map(e => `<option value="${e}">${e}</option>`).join('');
  exchangeEl.value = exchanges[0] || '';
  filterSymbols();
}

const exchangeEl = document.getElementById('exchange');
const symbolEl = document.getElementById('symbol');
const timeframeEl = document.getElementById('timeframe');
const startDateEl = document.getElementById('startDate');
const endDateEl = document.getElementById('endDate');
const metricFilterEl = document.getElementById('metricFilter');

exchangeEl.addEventListener('change', filterSymbols);
timeframeEl.addEventListener('change', () => {});

function filterSymbols() {
  const ex = exchangeEl.value;
  fetch('/api/pairs').then(r => r.json()).then(data => {
    const symbols = [...new Set(data.pairs.filter(p => p.exchange === ex).map(p => p.symbol))];
    symbolEl.innerHTML = symbols.map(s => `<option value="${s}">${s}</option>`).join('');
    symbolEl.value = symbols[0] || '';
  });
}

function percentileRank(sorted, value) {
  if (sorted.length === 0) return 0;
  let count = 0;
  for (const v of sorted) {
    if (v < value) count++;
  }
  return (count / sorted.length) * 100;
}

async function loadData() {
  const ex = exchangeEl.value;
  const sym = symbolEl.value;
  const tf = timeframeEl.value;
  if (!ex || !sym) return;

  let url = `/api/analyze/data?exchange=${ex}&symbol=${sym}&timeframe=${tf}`;
  if (startDateEl.value) url += `&start_time=${dateToMs(startDateEl.value)}`;
  if (endDateEl.value) url += `&end_time=${dateToMs(endDateEl.value) + 86400000}`;

  document.getElementById('status').textContent = 'loading...';
  const r = await fetch(url);
  const data = await r.json();
  document.getElementById('status').textContent = `${data.count} candles`;

  const showAll = metricFilterEl.value === 'all';
  const activeMetrics = showAll
    ? Object.keys(METRICS)
    : [metricFilterEl.value];

  // Build table
  const thead = document.getElementById('thead');
  const tbody = document.getElementById('tbody');

  let cols = ['time', 'open', 'close'];
  for (const m of activeMetrics) {
    cols.push(m, m + '_pct');
  }

  let headerRow = '<tr><th onclick="sortTable(this,0)">Date</th><th onclick="sortTable(this,1)">Open</th><th onclick="sortTable(this,2)">Close</th>';
  for (const m of activeMetrics) {
    headerRow += `<th onclick="sortTable(this,3)">${METRICS[m].label}</th><th onclick="sortTable(this,3)">Pctl</th>`;
  }
  headerRow += '</tr>';
  thead.innerHTML = headerRow;

  const rows = data.candles.map(c => {
    let row = `<tr><td class="num">${msToDate(c.t)}</td><td class="num">${c.o.toFixed(2)}</td><td class="num">${c.c.toFixed(2)}</td>`;
    for (const m of activeMetrics) {
      const val = c.metrics[m];
      const pct = c.percentiles[m];
      const color = val >= 0 ? '#26a69a' : '#ef5350';
      row += `<td class="num" style="color:${color}">${val.toFixed(2)}</td><td class="num">${pct.toFixed(1)}%</td>`;
    }
    row += '</tr>';
    return row;
  });
  tbody.innerHTML = rows.join('');

  document.getElementById('footer').textContent = `Metrics are % distance from OPEN. Percentile rank = % of candles with lower value.`;
}

let sortCol = 0, sortDir = 1;
function sortTable(th, col) {
  if (sortCol === col) sortDir *= -1;
  else { sortCol = col; sortDir = 1; }
  const tbody = document.getElementById('tbody');
  const rows = Array.from(tbody.children);
  rows.sort((a, b) => {
    const va = parseFloat(a.children[col]?.textContent || '0');
    const vb = parseFloat(b.children[col]?.textContent || '0');
    return (va - vb) * sortDir;
  });
  tbody.replaceChildren(...rows);
}

loadPairs();
</script>
</body>
</html>"""


@router.get("/analyze", response_class=HTMLResponse)
async def analyze_page():
    return ANALYZE_HTML


@router.get("/analyze/data")
async def analyze_data(
    exchange: str,
    symbol: str,
    timeframe: str,
    start_time: int | None = None,
    end_time: int | None = None,
    limit: int = Query(default=99999),
):
    rows = query_candles(
        exchange=exchange,
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
        start_time=start_time,
        end_time=end_time,
        desc=True,
    )
    rows.reverse()

    if not rows:
        return {"count": 0, "candles": []}

    candles = []
    for r in rows:
        o, h, l, cl, v = r["open"], r["high"], r["low"], r["close"], r["volume"]
        # use stored metrics if available, otherwise compute on the fly
        if r.get("metrics"):
            metrics = json.loads(r["metrics"])
        else:
            metrics = {
                "oc": (cl - o) / o * 100,
                "oh": (h - o) / o * 100,
                "ol": (l - o) / o * 100,
                "hl": (h - l) / o * 100,
                "hc": (h - cl) / o * 100,
                "lc": (l - cl) / o * 100,
            }
        candles.append({
            "t": r["timestamp"],
            "o": o, "h": h, "l": l, "c": cl, "v": v,
            "metrics": metrics,
        })

    max_vol = max(c["v"] for c in candles) or 1
    for c in candles:
        c["metrics"]["vol"] = (c["v"] / max_vol) * 100

    return {"count": len(candles), "candles": candles}
