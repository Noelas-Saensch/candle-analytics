from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Candle Analytics</title>
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1a1a2e; color: #e0e0e0; }
.header { background: #16213e; padding: 8px 20px; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; border-bottom: 1px solid #0f3460; }
.header h1 { font-size: 16px; color: #e94560; margin-right: 8px; }
.tabs { display: flex; gap: 0; margin-right: 12px; }
.tab { padding: 6px 14px; font-size: 12px; color: #888; cursor: pointer; border: 1px solid #0f3460; background: transparent; border-radius: 4px 4px 0 0; margin-bottom: -1px; }
.tab:hover { color: #e0e0e0; }
.tab.active { color: #e94560; border-color: #e94560; border-bottom-color: #16213e; background: #16213e; }
.controls { display: flex; gap: 5px; align-items: center; flex-wrap: wrap; }
.controls label { font-size: 11px; color: #888; }
.controls select, .controls input { background: #0f3460; color: #e0e0e0; border: 1px solid #1a3a6b; padding: 4px 8px; border-radius: 4px; font-size: 12px; cursor: pointer; }
.controls select:focus, .controls input:focus { outline: none; border-color: #e94560; }
.controls input[type=date] { color-scheme: dark; }
.controls .btn { background: #0f3460; color: #e0e0e0; border: 1px solid #1a3a6b; padding: 4px 12px; border-radius: 4px; font-size: 12px; cursor: pointer; }
.controls .btn:hover { border-color: #e94560; }
.controls .btn:disabled { opacity: .5; cursor: not-allowed; }
.controls .btn-primary { background: #e94560; color: #fff; border: none; }
.controls .btn-primary:hover { background: #d63851; }
.controls .sep { width: 1px; height: 22px; background: #0f3460; margin: 0 3px; }
#chart-wrapper { position: relative; width: 100%; height: calc(100vh - 46px); }
#chart { width: 100%; height: 100%; }
#auto-scale-btn { position: absolute; top: 8px; right: 12px; z-index: 10; background: #16213e; color: #888; border: 1px solid #0f3460; border-radius: 4px; padding: 4px 8px; font-size: 16px; cursor: pointer; line-height: 1; }
#auto-scale-btn:hover { color: #e0e0e0; border-color: #e94560; }
#status { position: absolute; bottom: 8px; left: 12px; z-index: 10; font-size: 11px; color: #555; }
#empty { display: none; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; color: #888; z-index: 10; }
#empty h2 { font-size: 20px; margin-bottom: 8px; color: #e94560; }
#empty p { margin-bottom: 16px; }
#empty button { background: #0f3460; color: #e0e0e0; border: 1px solid #1a3a6b; padding: 8px 20px; border-radius: 4px; font-size: 14px; cursor: pointer; margin: 4px; }
#empty button:hover { border-color: #e94560; }
#loading { display: none; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: #888; font-size: 14px; z-index: 10; }
.view { display: none; }
.view.active { display: block; }
#analyze-view { padding: 12px 20px; }
#analyze-view .controls { margin-bottom: 12px; }
#analyze-table-wrap { overflow-x: auto; max-height: calc(100vh - 120px); }
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th, td { padding: 4px 8px; text-align: right; border-bottom: 1px solid #16213e; }
th { position: sticky; top: 0; background: #16213e; color: #888; font-weight: 500; cursor: pointer; user-select: none; }
th:hover { color: #e0e0e0; }
td:first-child, th:first-child { text-align: left; }
tr:hover { background: #16213e; }
.num { font-variant-numeric: tabular-nums; }
#astatus { color: #888; font-size: 12px; margin-bottom: 8px; }
#afooter { margin-top: 8px; font-size: 11px; color: #555; }
</style>
</head>
<body>
<div class="header">
  <h1>candle-analytics</h1>
  <div class="tabs">
    <div class="tab active" data-tab="chart" onclick="switchTab('chart')">Chart</div>
    <div class="tab" data-tab="analyze" onclick="switchTab('analyze')">Analyze</div>
  </div>
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
    <div class="sep"></div>
    <button class="btn" id="updateBtn" onclick="updateData()">Update</button>
    <button class="btn btn-primary" id="fetchAllBtn" onclick="fetchAllData()">Fetch all</button>
  </div>
</div>

<div id="chart-view" class="view active">
  <div id="chart-wrapper">
    <div id="chart"></div>
    <button id="auto-scale-btn" title="Auto-fit chart scale" onclick="autoScale()">&#x2921;</button>
    <div id="status"></div>
    <div id="loading">loading candles...</div>
    <div id="empty">
      <h2>No data</h2>
      <p>No candles for <span id="emptyKey">...</span></p>
      <button onclick="fetchAllData()">Fetch all</button>
    </div>
  </div>
</div>

<div id="analyze-view" class="view">
  <div class="controls">
    <label>metric</label>
    <select id="metricFilter">
      <option value="oc">OC%</option><option value="oh">OH%</option><option value="ol">OL%</option>
      <option value="hl">HL%</option><option value="hc">HC%</option><option value="lc">LC%</option>
      <option value="vol">Volume%</option><option value="all" selected>All</option>
    </select>
    <button class="btn btn-primary" onclick="loadAnalyze()">Load</button>
  </div>
  <div id="astatus">Select filters and click Load</div>
  <div id="analyze-table-wrap">
    <table id="atable">
      <thead id="atheed"></thead>
      <tbody id="atbody"></tbody>
    </table>
  </div>
  <div id="afooter"></div>
</div>

<script>
const METRICS = {
  oc: { label: 'OC%', desc: '(close-open)/open*100' },
  oh: { label: 'OH%', desc: '(high-open)/open*100' },
  ol: { label: 'OL%', desc: '(low-open)/open*100' },
  hl: { label: 'HL%', desc: '(high-low)/open*100' },
  hc: { label: 'HC%', desc: '(high-close)/open*100' },
  lc: { label: 'LC%', desc: '(low-close)/open*100' },
  vol: { label: 'Vol%', desc: 'volume/maxVolume*100' },
};

function switchTab(name) {
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === name));
  document.querySelectorAll('.view').forEach(v => v.classList.toggle('active', v.id === name + '-view'));
  document.getElementById('exchange').disabled = false;
  document.getElementById('symbol').disabled = false;
  document.getElementById('timeframe').disabled = false;
  document.getElementById('startDate').disabled = false;
  document.getElementById('endDate').disabled = false;
  if (name === 'chart') loadChart();
  else if (name === 'analyze') loadAnalyze();
}

const exchangeEl = document.getElementById('exchange');
const symbolEl = document.getElementById('symbol');
const timeframeEl = document.getElementById('timeframe');
const startDateEl = document.getElementById('startDate');
const endDateEl = document.getElementById('endDate');
const statusEl = document.getElementById('status');
const metricFilterEl = document.getElementById('metricFilter');

let chart, candleSeries, volumeSeries;
const TF_SEC = {
  '1m':60,'5m':300,'15m':900,'30m':1800,'1H':3600,'2H':7200,'4H':14400,'6H':21600,'12H':43200,
  '1D':86400,'2D':172800,'3D':259200,'1W':604800,'2W':1209600,'1M':2592000,
};

function initChart() {
  chart = LightweightCharts.createChart(document.getElementById('chart'), {
    layout: { textColor: '#888', background: { color: '#1a1a2e' } },
    grid: { vertLines: { color: '#16213e' }, horzLines: { color: '#16213e' } },
    timeScale: { timeVisible: true, borderColor: '#0f3460' },
    rightPriceScale: { borderColor: '#0f3460' },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
  });
  candleSeries = chart.addCandlestickSeries({
    upColor: '#26a69a', downColor: '#ef5350',
    borderUpColor: '#26a69a', borderDownColor: '#ef5350',
    wickUpColor: '#26a69a', wickDownColor: '#ef5350',
    priceScaleId: 'price',
  });
  volumeSeries = chart.addHistogramSeries({
    priceFormat: { type: 'volume' },
    priceScaleId: 'volume',
  });
  chart.priceScale('volume').applyOptions({
    scaleMargins: { top: 0.8, bottom: 0 },
  });
}

function autoScale() {
  chart.timeScale().fitContent();
  candleSeries.priceScale().applyOptions({ autoScale: true });
}

function msToDate(ms) { return new Date(ms).toISOString().slice(0, 10); }
function dateToMs(d) { return new Date(d + 'T00:00:00Z').getTime(); }

async function loadPairs() {
  const r = await fetch('/api/pairs');
  const data = await r.json();
  const exchanges = [...new Set(data.pairs.map(p => p.exchange))];
  exchangeEl.innerHTML = exchanges.map(e => `<option value="${e}">${e}</option>`).join('');
  exchangeEl.value = exchanges[0] || '';
  filterSymbols();
}

function filterSymbols() {
  const ex = exchangeEl.value;
  fetch('/api/pairs').then(r => r.json()).then(data => {
    const symbols = [...new Set(data.pairs.filter(p => p.exchange === ex).map(p => p.symbol))];
    symbolEl.innerHTML = symbols.map(s => `<option value="${s}">${s}</option>`).join('');
    symbolEl.value = symbols[0] || '';
    const active = document.querySelector('.tab.active');
    if (active) switchTab(active.dataset.tab);
  });
}

async function loadChart() {
  const ex = exchangeEl.value, sym = symbolEl.value, tf = timeframeEl.value;
  if (!ex || !sym) return;
  let url = `/api/candles?exchange=${ex}&symbol=${sym}&timeframe=${tf}&limit=99999`;
  if (startDateEl.value) url += `&start_time=${dateToMs(startDateEl.value)}`;
  if (endDateEl.value) url += `&end_time=${dateToMs(endDateEl.value) + 86400000}`;
  document.getElementById('loading').style.display = 'block';
  document.getElementById('empty').style.display = 'none';
  const r = await fetch(url);
  const data = await r.json();
  document.getElementById('loading').style.display = 'none';
  document.getElementById('emptyKey').textContent = `${ex} ${sym} ${tf}`;
  if (data.candles.length === 0) {
    document.getElementById('empty').style.display = 'block';
    statusEl.textContent = 'no data';
    return;
  }
  document.getElementById('empty').style.display = 'none';
  const candles = data.candles.map(c => ({
    time: Math.floor(c.timestamp / 1000),
    open: c.open, high: c.high, low: c.low, close: c.close,
  }));
  const vols = data.candles.map(c => ({
    time: Math.floor(c.timestamp / 1000),
    value: c.volume,
    color: c.close >= c.open ? 'rgba(38,166,154,0.3)' : 'rgba(239,83,80,0.3)',
  }));
  candleSeries.setData(candles);
  volumeSeries.setData(vols);
  chart.timeScale().fitContent();
  const from = msToDate(data.candles[0].timestamp);
  const to = msToDate(data.candles[data.candles.length - 1].timestamp);
  statusEl.textContent = `${data.count} candles  |  ${from} → ${to}`;
}

async function apiFetch(limit, startTime, endTime) {
  const ex = exchangeEl.value, sym = symbolEl.value, tf = timeframeEl.value;
  let url = `/api/fetch?exchange=${ex}&symbol=${sym}&timeframe=${tf}&limit=${limit}`;
  if (startTime) url += `&start_time=${startTime}`;
  if (endTime) url += `&end_time=${endTime}`;
  await fetch(url, { method: 'POST' });
}

async function updateData() {
  const btn = document.getElementById('updateBtn');
  btn.disabled = true; btn.textContent = 'updating...';
  const ex = exchangeEl.value, sym = symbolEl.value, tf = timeframeEl.value;
  const r = await fetch(`/api/candles?exchange=${ex}&symbol=${sym}&timeframe=${tf}&limit=1`);
  const data = await r.json();
  if (data.candles.length > 0) {
    const lastMs = data.candles[data.candles.length - 1].timestamp;
    const intervalMs = (TF_SEC[tf] || 3600) * 1000;
    await apiFetch(5000, lastMs - intervalMs, Date.now());
  }
  btn.disabled = false; btn.textContent = 'Update';
  loadChart();
}

async function fetchAllData() {
  const btn = document.getElementById('fetchAllBtn');
  btn.disabled = true; btn.textContent = 'fetching...';
  await apiFetch(99999);
  btn.disabled = false; btn.textContent = 'Fetch all';
  loadChart();
}

async function loadAnalyze() {
  const ex = exchangeEl.value, sym = symbolEl.value, tf = timeframeEl.value;
  if (!ex || !sym) return;
  let url = `/analyze/data?exchange=${ex}&symbol=${sym}&timeframe=${tf}`;
  if (startDateEl.value) url += `&start_time=${dateToMs(startDateEl.value)}`;
  if (endDateEl.value) url += `&end_time=${dateToMs(endDateEl.value) + 86400000}`;
  document.getElementById('astatus').textContent = 'loading...';
  const r = await fetch(url);
  const data = await r.json();
  document.getElementById('astatus').textContent = `${data.count} candles`;

  const showAll = metricFilterEl.value === 'all';
  const activeMetrics = showAll ? Object.keys(METRICS) : [metricFilterEl.value];

  let headerRow = '<tr><th onclick="sortTable(this,0)">Date</th><th onclick="sortTable(this,1)">Open</th><th onclick="sortTable(this,2)">Close</th>';
  for (const m of activeMetrics) {
    headerRow += `<th onclick="sortTable(this,3)">${METRICS[m].label}</th><th onclick="sortTable(this,3)">Pctl</th>`;
  }
  headerRow += '</tr>';
  document.getElementById('atheed').innerHTML = headerRow;
  document.getElementById('atbody').innerHTML = data.candles.map(c => {
    let row = `<tr><td class="num">${msToDate(c.t)}</td><td class="num">${c.o.toFixed(2)}</td><td class="num">${c.c.toFixed(2)}</td>`;
    for (const m of activeMetrics) {
      const val = c.metrics[m], pct = c.percentiles[m];
      row += `<td class="num" style="color:${val >= 0 ? '#26a69a' : '#ef5350'}">${val.toFixed(2)}</td><td class="num">${pct.toFixed(1)}%</td>`;
    }
    return row + '</tr>';
  }).join('');
  document.getElementById('afooter').textContent = 'Metrics are % distance from OPEN. Percentile rank = % of candles with lower value.';
}

let sortCol = 0, sortDir = 1;
function sortTable(th, col) {
  if (sortCol === col) sortDir *= -1;
  else { sortCol = col; sortDir = 1; }
  const tbody = document.getElementById('atbody');
  const rows = Array.from(tbody.children);
  rows.sort((a, b) => (parseFloat(a.children[col]?.textContent || '0') - parseFloat(b.children[col]?.textContent || '0')) * sortDir);
  tbody.replaceChildren(...rows);
}

exchangeEl.addEventListener('change', filterSymbols);
symbolEl.addEventListener('change', () => { const t = document.querySelector('.tab.active'); if (t) switchTab(t.dataset.tab); });
timeframeEl.addEventListener('change', () => { const t = document.querySelector('.tab.active'); if (t) switchTab(t.dataset.tab); });
startDateEl.addEventListener('change', () => { const t = document.querySelector('.tab.active'); if (t) switchTab(t.dataset.tab); });
endDateEl.addEventListener('change', () => { const t = document.querySelector('.tab.active'); if (t) switchTab(t.dataset.tab); });

initChart();
loadPairs();
</script>
</body>
</html>"""


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    return HTML
