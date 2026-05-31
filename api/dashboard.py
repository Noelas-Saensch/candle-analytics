from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Candle Analytics</title>
<script src="https://unpkg.com/lightweight-charts@5.0.0/dist/lightweight-charts.standalone.production.js" onerror="this.onerror=null;var s=document.createElement('script');s.src='https://cdn.jsdelivr.net/npm/lightweight-charts@5.0.0/dist/lightweight-charts.standalone.production.js';document.head.appendChild(s)"></script>
<script defer src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.2.0/dist/chartjs-plugin-zoom.min.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { height: 100%; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1a1a2e; color: #e0e0e0; overflow: hidden; }
.header { background: #16213e; padding: 8px 20px; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; border-bottom: 1px solid #0f3460; }
.header h1 { font-size: 16px; color: #e94560; margin-right: 8px; }
.tabs { display: flex; gap: 0; margin-right: 12px; }
.tab { padding: 6px 14px; font-size: 12px; color: #888; cursor: pointer; border: 1px solid #0f3460; background: transparent; border-radius: 4px 4px 0 0; margin-bottom: -1px; }
.tab:hover { color: #e0e0e0; }
.tab.active { color: #e94560; border-color: #e94560; border-bottom-color: #16213e; background: #16213e; }
.controls-bar { display: flex; align-items: center; gap: 5px; flex-wrap: wrap; padding: 6px 12px; background: #16213e; border-bottom: 1px solid #0f3460; }
.controls-bar label { font-size: 11px; color: #888; }
.controls-bar select, .controls-bar input { background: #0f3460; color: #e0e0e0; border: 1px solid #1a3a6b; padding: 4px 8px; border-radius: 4px; font-size: 12px; cursor: pointer; }
.controls-bar select:focus, .controls-bar input:focus { outline: none; border-color: #e94560; }
.controls-bar input[type=date] { color-scheme: dark; }
.controls-bar .btn { background: #0f3460; color: #e0e0e0; border: 1px solid #1a3a6b; padding: 4px 12px; border-radius: 4px; font-size: 12px; cursor: pointer; }
.controls-bar .btn:hover { border-color: #e94560; }
.controls-bar .btn:disabled { opacity: .5; cursor: not-allowed; }
.controls-bar .btn-primary { background: #e94560; color: #fff; border: none; }
.controls-bar .btn-primary:hover { background: #d63851; }
.controls-bar .sep { width: 1px; height: 22px; background: #0f3460; margin: 0 3px; }
.gear-btn { background: transparent; color: #888; border: 1px solid #1a3a6b; border-radius: 3px; padding: 4px 8px; font-size: 14px; cursor: pointer; line-height: 1; }
.gear-btn:hover { color: #e0e0e0; border-color: #e94560; }
#chart-wrapper { position: relative; width: 100%; height: calc(100vh - 46px - 42px - 25px); flex: 1; display: flex; flex-direction: column; }
#chart { width: 100%; flex: 1; min-height: 120px; }
#go-latest-btn { position:absolute;top:8px;right:12px;z-index:10;background:#16213e;color:#888;border:1px solid #0f3460;border-radius:4px;padding:4px 8px;font-size:14px;cursor:pointer;line-height:1; }
#go-latest-btn:hover { color:#e0e0e0; border-color:#e94560; }
#load-older-btn { position:absolute;top:50%;left:4px;z-index:10;transform:translateY(-50%);background:#16213e;color:#888;border:1px solid #0f3460;border-radius:4px;padding:4px 8px;font-size:14px;cursor:pointer;line-height:1; }
#load-older-btn:hover { color:#e0e0e0; border-color:#e94560; }
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
.mtog { font-size: 11px; color: #888; cursor: pointer; display: inline-flex; align-items: center; gap: 2px; }
.mtog:hover { color: #e0e0e0; }
.mtog input { accent-color: #e94560; }
.bull { color: #26a69a; }
.bear { color: #ef5350; }
.fam-tabs { display:flex;gap:2px;margin-bottom:6px;font-size:11px;flex-wrap:wrap; }
.fam-tab { padding:3px 10px;border-radius:3px;cursor:pointer;color:#888;background:#0f3460;border:1px solid transparent; }
.fam-tab:hover { color:#e0e0e0;border-color:#1a3a6b; }
.fam-tab.active { color:#e94560;background:#16213e;border-color:#e94560; }
.ctip { position:relative;display:inline-flex;align-items:center; }
.ctip .ctip-text { display:none;position:absolute;bottom:100%;left:50%;transform:translateX(-50%);background:#16213e;color:#e0e0e0;border:1px solid #0f3460;padding:6px 10px;border-radius:4px;font-size:11px;white-space:nowrap;z-index:20;pointer-events:none; }
.ctip:hover .ctip-text { display:block; }
#vizCanvas { min-height:220px; width:100%; }
.cf-icon { cursor:pointer; margin-left:3px; font-size:9px; color:#555; display:inline-block; }
.cf-icon:hover { color:#e0e0e0; }
.cf-icon.active { color:#e94560; }
.cf-drop { position:fixed; z-index:100; background:#16213e; border:1px solid #0f3460; border-radius:4px; padding:8px; font-size:11px; min-width:180px; max-height:280px; overflow-y:auto; box-shadow:0 4px 12px rgba(0,0,0,0.4); }
.cf-drop label { display:flex; align-items:center; gap:4px; color:#e0e0e0; padding:2px 0; cursor:pointer; }
.cf-drop label:hover { color:#e94560; }
.cf-drop input[type=number] { background:#0f3460; color:#e0e0e0; border:1px solid #1a3a6b; padding:2px 4px; border-radius:3px; font-size:10px; width:70px; }
.cf-drop input[type=text] { background:#0f3460; color:#e0e0e0; border:1px solid #1a3a6b; padding:2px 4px; border-radius:3px; font-size:10px; width:100px; }
.cf-drop input[type=checkbox] { accent-color:#e94560; }
.cf-drop .cf-sep { border-top:1px solid #0f3460; margin:4px 0; }
.cf-drop .cf-title { color:#888; font-size:10px; font-weight:600; margin-bottom:2px; }
.cf-drop .cf-act { cursor:pointer; color:#e94560; font-size:10px; padding:2px 0; display:block; }
.cf-drop .cf-act:hover { text-decoration:underline; }
/* INFO ARRAY styles */
.ia-wrap { width:100%; border-collapse:collapse; font-size:11px; margin-bottom:8px; table-layout:fixed; }
.ia-wrap th { background:#16213e; color:#888; font-weight:500; padding:2px 4px; border:1px solid #0f3460; text-align:center; position:sticky; top:0; z-index:2; overflow:hidden; }
.ia-wrap td { padding:2px 3px; border:1px solid #0f3460; text-align:center; color:#e0e0e0; cursor:pointer; overflow:hidden; }
.ia-wrap td:hover { background:#1a3a6b; }
.ia-wrap .ia-th-seuil { width:8%; }
.ia-wrap .ia-th-bb { width:4%; }
.ia-wrap .ia-th-stats { width:8%; }
.ia-wrap .ia-th-concu { width:7%; }
.ia-wrap .ia-edit { background:transparent; border:none; color:#e0e0e0; font-size:10px; text-align:center; width:100%; outline:none; }
.ia-wrap .ia-edit:focus { background:#0f3460; border:1px solid #e94560; border-radius:2px; }
.ia-wrap .ia-del { cursor:pointer; color:#ef5350; font-size:10px; padding:0 2px; }
.ia-wrap .ia-del:hover { color:#ff1744; }
.ia-wrap .ia-add { cursor:pointer; color:#26a69a; font-size:10px; padding:2px; text-align:center; display:block; }
.ia-wrap .ia-add:hover { color:#69f0ae; }
.ia-wrap .ia-bull { color:#26a69a; font-size:10px; }
.ia-wrap .ia-bear { color:#ef5350; font-size:10px; }
.ia-wrap .ia-corr { font-size:8px; color:#555; line-height:1.3; word-break:break-word; }
.ia-wrap .num { font-size:9px; }
.col-sep-ts { border-left:2px solid #0f3460 !important; }
.col-sep-ohlcv { border-left:2px solid #0f3460 !important; }
.col-sep-metric { border-left:2px solid #0f3460 !important; }
.col-sep-pctl { border-left:1px dashed #0f3460 !important; }
/* INFO ARRAY column tint backgrounds */
.ia-bg-oh td, .ia-bg-oh th:not(:first-child) { background:rgba(38,166,154,0.06) !important; }
.ia-bg-ol td, .ia-bg-ol th:not(:first-child) { background:rgba(38,166,154,0.06) !important; }
.ia-bg-hc td, .ia-bg-hc th:not(:first-child) { background:rgba(239,83,80,0.06) !important; }
.ia-bg-lc td, .ia-bg-lc th:not(:first-child) { background:rgba(239,83,80,0.06) !important; }
.ia-bg-hl td, .ia-bg-hl th:not(:first-child) { background:rgba(136,136,136,0.06) !important; }
.ia-bg-oc td, .ia-bg-oc th:not(:first-child) { background:rgba(136,136,136,0.06) !important; }
.ia-bg-vol td, .ia-bg-vol th:not(:first-child) { background:rgba(66,165,245,0.06) !important; }
/* INFO ARRAY fixed layout for no horizontal scroll */
.ia-wrap { table-layout:fixed; }
.ia-wrap .ia-th-seuil { width:70px; }
/* INFO ARRAY move btn */
.ia-mv { cursor:pointer; color:#555; font-size:9px; padding:0 2px; user-select:none; }
.ia-mv:hover { color:#e0e0e0; }
/* Chart stack blocks */
.chart-block { background:#16213e; border-radius:4px; padding:8px; margin-bottom:10px; }
.chart-block .cb-title { font-size:12px; color:#e94560; font-weight:500; margin-bottom:6px; display:flex; align-items:center; gap:8px; }
.chart-block .cb-params { display:flex; gap:6px; flex-wrap:wrap; align-items:center; font-size:10px; margin-bottom:4px; }
.chart-block .cb-params select, .chart-block .cb-params input { background:#0f3460; color:#e0e0e0; border:1px solid #1a3a6b; padding:2px 6px; border-radius:3px; font-size:10px; }
.chart-block .cb-params label { color:#888; display:inline-flex; align-items:center; gap:3px; cursor:pointer; }
.chart-block .cb-params input[type=range] { width:50px; accent-color:#e94560; }
.chart-block canvas { width:100%; min-height:160px; max-height:220px; background:#f5f5f5; border-radius:4px; }
.cb-reset { cursor:pointer; color:#888; font-size:12px; padding:2px 6px; border:1px solid #0f3460; border-radius:3px; background:transparent; }
.cb-reset:hover { color:#e0e0e0; border-color:#e94560; }

/* Indicator toolbar */
.ind-bar { display:flex;gap:4px;align-items:center;flex-wrap:wrap;padding:4px 12px;background:#16213e;border-bottom:1px solid #0f3460;font-size:12px;position:relative; }
.ind-chip { display:inline-flex;align-items:center;gap:4px;background:#0f3460;color:#e0e0e0;border:1px solid #1a3a6b;border-radius:3px;padding:2px 8px;font-size:11px;cursor:pointer; }
.ind-chip:hover { border-color:#e94560; }
.ind-chip .dot { width:8px;height:8px;border-radius:50%;display:inline-block; }
.ind-chip .close { cursor:pointer;color:#ef5350;font-size:12px;margin-left:2px; }
.ind-chip .close:hover { color:#ff1744; }
.ind-add { background:transparent;color:#888;border:1px dashed #0f3460;border-radius:3px;padding:2px 10px;font-size:18px;cursor:pointer;line-height:1; }
.ind-add:hover { color:#e94560;border-color:#e94560; }
.ind-menu { display:none;position:absolute;z-index:50;background:#16213e;border:1px solid #0f3460;border-radius:4px;padding:6px;min-width:200px;font-size:12px;top:100%;left:0; }
.ind-menu.show { display:block; }
.ind-menu-cat { color:#888;font-size:10px;font-weight:600;padding:4px 6px 2px; }
.ind-menu-item { padding:4px 8px;cursor:pointer;color:#e0e0e0;border-radius:3px;display:flex;align-items:center;gap:6px; }
.ind-menu-item:hover { background:#0f3460;color:#e94560; }
.ind-config { position:fixed;z-index:100;background:#16213e;border:1px solid #0f3460;border-radius:6px;padding:12px;min-width:280px;font-size:12px;box-shadow:0 8px 24px rgba(0,0,0,0.5);top:50%;left:50%;transform:translate(-50%,-50%); }
.pane-header { display:flex;align-items:center;background:#16213e;padding:2px 8px;font-size:11px;color:#888;border-bottom:1px solid #0f3460;border-top:1px solid #0f3460;cursor:default; }
.pane-header:hover { color:#e0e0e0; }
.pane-resize-handle { height:4px;cursor:ns-resize;background:#0f3460; }
.pane-resize-handle:hover { background:#e94560; }
.ind-config h3 { color:#e94560;margin-bottom:8px;font-size:14px; }
.ind-config label { display:flex;align-items:center;gap:6px;color:#888;margin:4px 0; }
.ind-config input[type=number] { background:#0f3460;color:#e0e0e0;border:1px solid #1a3a6b;padding:3px 6px;border-radius:3px;width:80px; }
.ind-config input[type=color] { width:32px;height:24px;padding:0;border:none;cursor:pointer;background:transparent; }
.ind-config select { background:#0f3460;color:#e0e0e0;border:1px solid #1a3a6b;padding:3px 6px;border-radius:3px; }
.ind-config .btn { margin-top:8px;margin-right:4px; }
.ind-overlay { display:none;position:fixed;z-index:99;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.4); }
.ind-overlay.show { display:block; }
.ind-pane-toggle { background:transparent;color:#555;border:none;cursor:pointer;font-size:10px;padding:0 4px; }
.ind-pane-toggle:hover { color:#e0e0e0; }
.ind-pane { border-top:1px solid #0f3460;margin-top:2px; }
.ind-config .line-section { border:1px solid #1a3a6b;border-radius:4px;padding:6px 8px;margin:6px 0;background:#0f3460; }
.ind-config .line-section h4 { color:#e0e0e0;font-size:11px;margin:0 0 4px; }
.ind-config .line-row { display:flex;align-items:center;gap:6px;margin:3px 0;font-size:11px; }
.ind-config .line-row label { color:#888;margin:0;font-size:10px; }
.ind-config .line-row input[type=color] { width:24px;height:18px;padding:0;border:none;cursor:pointer;background:transparent; }
.ind-config .line-row input[type=number] { width:50px;font-size:10px;padding:2px 4px; }
.ind-config .line-row select { font-size:10px;padding:2px 4px; }
.ind-config .zone-row { display:flex;align-items:center;gap:4px;margin:2px 0;font-size:10px;color:#888; }
.ind-config .zone-row input[type=number] { width:50px;font-size:10px;padding:2px 4px;background:#0f3460;color:#e0e0e0;border:1px solid #1a3a6b;border-radius:3px; }
.ind-config .zone-row input[type=color] { width:20px;height:16px;padding:0;border:none;cursor:pointer;background:transparent; }
.ind-config .zone-row label { font-size:10px;color:#888;margin:0; }
.ind-config .section-divider { border:none;border-top:1px solid #1a3a6b;margin:8px 0; }
/* Settings modal */
.settings-overlay { display:none; position:fixed; z-index:99; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.4); }
.settings-overlay.show { display:block; }
.settings-modal { display:none; position:fixed; z-index:100; top:50%; left:50%; transform:translate(-50%,-50%); background:#16213e; border:1px solid #0f3460; border-radius:6px; padding:16px; min-width:300px; box-shadow:0 8px 24px rgba(0,0,0,0.5); }
.settings-modal.show { display:block; }
.settings-modal h3 { color:#e94560; margin-bottom:12px; font-size:14px; }
.settings-row { display:flex; align-items:center; gap:12px; margin:8px 0; flex-wrap:wrap; }
.settings-row label { display:flex; align-items:center; gap:6px; color:#888; font-size:11px; cursor:pointer; }
.settings-row input[type=color] { width:32px; height:24px; padding:0; border:none; cursor:pointer; background:transparent; }
.settings-row .btn { font-size:12px; padding:4px 14px; }
/* Crosshair legend */
#crosshairLegend { display:none; position:absolute; z-index:15; pointer-events:none; background:rgba(22,33,62,0.9); border:1px solid #0f3460; border-radius:4px; padding:6px 10px; font-size:11px; line-height:1.6; white-space:nowrap; top:8px; left:12px; }
/* TV-style time scale — always visible below all panes */
</style>
</head>
<body>
<div class="header">
  <h1>candle-analytics</h1>
  <div class="tabs">
    <div class="tab active" data-tab="chart" onclick="switchTab('chart')">Chart</div>
    <div class="tab" data-tab="analyze" onclick="switchTab('analyze')">Metrics</div>
    <div class="tab" data-tab="rawdata" onclick="switchTab('rawdata')">RAW DATA</div>
    <a href="/strategy-lab" class="tab" style="text-decoration:none">Strategy Lab</a>
  </div>
</div>

<div class="controls-bar">
  <button class="gear-btn" id="settingsGear" onclick="toggleSettings()" title="Chart settings">&#x2699;</button>
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
  <label style="font-size:11px;color:#888;cursor:pointer"><input type="checkbox" id="regToggle" onchange="toggleRegression()"> Reg</label>
  <button class="btn" id="updateBtn" onclick="updateData()">Update</button>
  <button class="btn btn-primary" id="fetchAllBtn" onclick="fetchAllData()">Fetch all</button>
</div>

<!-- Settings modal -->
<div class="settings-overlay" id="settingsOverlay" onclick="closeSettings()"></div>
<div class="settings-modal" id="settingsModal">
  <h3>Chart Settings</h3>
  <div class="settings-row">
    <label>Bullish body <input type="color" id="cfg_bullBody" value="#808080"></label>
    <label>Bearish body <input type="color" id="cfg_bearBody" value="#2d2d2d"></label>
  </div>
  <div class="settings-row">
    <label>Bullish wick <input type="color" id="cfg_bullWick" value="#808080"></label>
    <label>Bearish wick <input type="color" id="cfg_bearWick" value="#2d2d2d"></label>
  </div>
  <div class="settings-row">
    <label>Chart bg <input type="color" id="cfg_chartBg" value="#f5f5f5"></label>
  </div>
  <h4 style="margin:12px 0 4px;color:#888">Crosshair</h4>
  <div class="settings-row">
    <label><input type="checkbox" id="cfg_crosshairLines"> Dotted value lines on hover</label>
  </div>
  <h4 style="margin:12px 0 4px;color:#888">Data</h4>
  <div class="settings-row">
    <label>Max bars <input type="number" id="cfg_maxBars" value="5000" min="1000" max="99999" step="500"></label>
  </div>
  <div class="settings-row">
    <button class="btn" onclick="resetChartSettings()">Reset defaults</button>
    <button class="btn btn-primary" onclick="applyChartSettings()">Apply</button>
  </div>
</div>

<div class="ind-bar" id="indBar">
  <span style="color:#888;font-size:11px">Indicators:</span>
  <span id="indChips"></span>
  <button class="ind-add" id="indAddBtn" title="Add indicator" onclick="showIndMenu()">+</button>
  <div class="ind-menu" id="indMenu"></div>
</div>

<div id="chart-view" class="view active">
  <div id="chart-wrapper">
    <div id="chart"></div>
    <div id="crosshairLegend"></div>
    <button id="go-latest-btn" title="Scroll to latest candle (resets zoom axes)" onclick="goToLatest()">&#x25B6;</button>
    <button id="load-older-btn" title="Load older candles" onclick="loadOlderCandles()" style="display:none">&#x21A9;</button>
    <div id="status"></div>
    <div id="loading">loading candles...</div>
    <div id="empty">
      <h2>No data</h2>
      <p>No candles for <span id="emptyKey">...</span></p>
      <button onclick="fetchAllData()">Fetch all</button>
    </div>
    <div id="init-error" style="display:none;position:fixed;top:0;left:0;right:0;background:#e94560;color:#fff;padding:8px 16px;font-size:13px;z-index:999;text-align:center">
      <span id="init-error-msg">The dashboard failed to initialize.</span>
      <button onclick="this.parentElement.style.display='none'" style="background:transparent;color:#fff;border:1px solid rgba(255,255,255,0.5);padding:2px 12px;border-radius:3px;cursor:pointer;font-size:11px;margin-left:12px">Dismiss</button>
      <button onclick="location.reload()" style="background:rgba(255,255,255,0.2);color:#fff;border:1px solid rgba(255,255,255,0.5);padding:2px 12px;border-radius:3px;cursor:pointer;font-size:11px;margin-left:6px">Reload</button>
    </div>
  </div>
</div>



<script>
try { Chart.register(ChartZoom); } catch(e) { console.warn('ChartZoom not available — zoom disabled'); }
const ZOOM_OPTS = {
  zoom: { wheel: { enabled: true, speed: 0.05 }, pinch: { enabled: true }, mode: 'xy' },
  pan: { enabled: true, mode: 'xy' },
};
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
  const viewId = name === 'rawdata' ? 'rawdata-view' : name + '-view';
  document.querySelectorAll('.view').forEach(v => v.classList.toggle('active', v.id === viewId));
  if (name !== 'chart') stopLive();
  if (name === 'chart') loadChart();
  else if (name === 'analyze') loadAnalyze();
  else if (name === 'rawdata') loadRawData();
}

const exchangeEl = document.getElementById('exchange');
const symbolEl = document.getElementById('symbol');
const timeframeEl = document.getElementById('timeframe');
const startDateEl = document.getElementById('startDate');
const endDateEl = document.getElementById('endDate');
const statusEl = document.getElementById('status');

let chart, candleSeries, regSeries = null;
let eventSource = null;
let lastCandleTime = 0;

function toggleRegression() {
  const show = document.getElementById('regToggle').checked;
  if (show && candleSeries && window._candleData && window._candleData.length > 20) {
    const candles = window._candleData;
    const n = candles.length;
    const xs = Array.from({length: n}, (_, i) => i);
    const ys = candles.map(c => c.close);
    const mx = xs.reduce((a,b) => a+b, 0) / n;
    const my = ys.reduce((a,b) => a+b, 0) / n;
    const num = xs.reduce((s, x, i) => s + (x - mx) * (ys[i] - my), 0);
    const den = xs.reduce((s, x) => s + (x - mx) ** 2, 0);
    const slope = den ? num / den : 0;
    const inter = my - slope * mx;
    const lines = xs.map(x => ({ time: candles[x].t / 1000, value: slope * x + inter }));
    if (regSeries) { chart.removeSeries(regSeries); regSeries = null; }
    regSeries = chart.addSeries(LightweightCharts.LineSeries, {
      color: '#f9a825', lineWidth: 1, priceScaleId: 'left',
    }, 0);
    regSeries.setData(lines);
  } else if (regSeries) {
    chart.removeSeries(regSeries);
    regSeries = null;
  }
}

// --- Chart settings (candle colors + bg) ---
var CHART_SETTINGS_KEY = 'candle_analytics_chart_settings';
var INDICATOR_SETTINGS_KEY = 'candle_analytics_indicator_settings';

var CHART_SETTINGS_DEFAULTS = {
  bullBody: '#808080',
  bearBody: '#2d2d2d',
  bullWick: '#808080',
  bearWick: '#2d2d2d',
  chartBg: '#f5f5f5',
  crosshairLines: false,
  maxBars: 5000,
};

function loadChartSettings() {
  try {
    var saved = JSON.parse(localStorage.getItem(CHART_SETTINGS_KEY));
    if (saved) return Object.assign({}, CHART_SETTINGS_DEFAULTS, saved);
  } catch(_) {}
  return Object.assign({}, CHART_SETTINGS_DEFAULTS);
}

function saveChartSettings(s) {
  try { localStorage.setItem(CHART_SETTINGS_KEY, JSON.stringify(s)); } catch(_) {}
}

function applyChartSettings() {
  var s = {
    bullBody: document.getElementById('cfg_bullBody').value,
    bearBody: document.getElementById('cfg_bearBody').value,
    bullWick: document.getElementById('cfg_bullWick').value,
    bearWick: document.getElementById('cfg_bearWick').value,
    chartBg: document.getElementById('cfg_chartBg').value,
    crosshairLines: document.getElementById('cfg_crosshairLines').checked,
    maxBars: parseInt(document.getElementById('cfg_maxBars').value) || 5000,
  };
  saveChartSettings(s);
  if (candleSeries) {
    candleSeries.applyOptions({
      upColor: s.bullBody, downColor: s.bearBody,
      borderUpColor: s.bullBody, borderDownColor: s.bearBody,
      wickUpColor: s.bullWick, wickDownColor: s.bearWick,
    });
  }
  if (chart) {
    chart.applyOptions({ layout: { background: { color: s.chartBg } } });
    chart.applyOptions({
      crosshair: {
        vertLine: { visible: s.crosshairLines, labelBackgroundColor: '#e94560', color: '#e94560', width: 1 },
        horzLine: { visible: s.crosshairLines, labelBackgroundColor: '#e94560', color: '#e94560', width: 1 },
      },
    });
  }
  // Update maxBars and reload chart
  var newMaxBars = s.maxBars;
  if (newMaxBars !== _maxBars) {
    _maxBars = newMaxBars;
    loadChart();
  }
  closeSettings();
}

function resetChartSettings() {
  var d = CHART_SETTINGS_DEFAULTS;
  document.getElementById('cfg_bullBody').value = d.bullBody;
  document.getElementById('cfg_bearBody').value = d.bearBody;
  document.getElementById('cfg_bullWick').value = d.bullWick;
  document.getElementById('cfg_bearWick').value = d.bearWick;
  document.getElementById('cfg_chartBg').value = d.chartBg;
  document.getElementById('cfg_crosshairLines').checked = d.crosshairLines;
  document.getElementById('cfg_maxBars').value = d.maxBars;
  applyChartSettings();
}

function toggleSettings() {
  var s = loadChartSettings();
  document.getElementById('cfg_bullBody').value = s.bullBody;
  document.getElementById('cfg_bearBody').value = s.bearBody;
  document.getElementById('cfg_bullWick').value = s.bullWick;
  document.getElementById('cfg_bearWick').value = s.bearWick;
  document.getElementById('cfg_chartBg').value = s.chartBg;
  document.getElementById('cfg_crosshairLines').checked = s.crosshairLines;
  document.getElementById('cfg_maxBars').value = s.maxBars;
  document.getElementById('settingsOverlay').classList.add('show');
  document.getElementById('settingsModal').classList.add('show');
}

function closeSettings() {
  document.getElementById('settingsOverlay').classList.remove('show');
  document.getElementById('settingsModal').classList.remove('show');
}

function saveIndicatorSettings() {
  try {
    var data = [];
    for (var i = 0; i < activeIndicators.length; i++) {
      var ind = activeIndicators[i];
      data.push({ name: ind.name, label: ind.label, params: ind.params, paneMode: ind.paneMode });
    }
    localStorage.setItem(INDICATOR_SETTINGS_KEY, JSON.stringify(data));
  } catch(e) {}
}

function loadIndicatorSettings() {
  try {
    var raw = localStorage.getItem(INDICATOR_SETTINGS_KEY);
    if (!raw) return null;
    var data = JSON.parse(raw);
    if (!Array.isArray(data) || data.length === 0) return null;
    return data;
  } catch(e) { return null; }
}

// --- Indicator overlay management ---
var activeIndicators = [];
var indicatorSeries = {};
var indicatorPanes = {};
var nextPaneId = 1;

var INDICATOR_CATALOG = {
  "Cloud": [
    { name: "ichimoku", label: "Ichimoku Cloud", params: { tenkan: 9, kijun: 26, senkou: 52 }, defaults: { tenkan: 9, kijun: 26, senkou: 52, color: "#26a69a", priceLabels: false }, paneMode: "main" },
  ],
  "Trend": [
    { name: "sma", label: "SMA", params: { period: 20 }, defaults: { period: 20, color: "#26a69a", priceLabels: false }, paneMode: "main" },
    { name: "ema", label: "EMA", params: { period: 20 }, defaults: { period: 20, color: "#e94560", priceLabels: false }, paneMode: "main" },
    { name: "bbands", label: "Bollinger Bands", params: { period: 20, stddev: 2 }, defaults: { period: 20, stddev: 2, color: "#e94560", priceLabels: false }, paneMode: "main" },
    { name: "vwap", label: "VWAP", params: {}, defaults: { color: "#f9a825", priceLabels: false }, paneMode: "main" },
  ],
  "Oscillators": [
    { name: "rsi", label: "RSI", params: { period: 14 }, defaults: { period: 14, color: "#ab47bc", priceLabels: false }, paneMode: "shared" },
    { name: "stoch", label: "Stochastic", params: { period: 14 }, defaults: { period: 14, color: "#26a69a", priceLabels: false }, paneMode: "shared" },
    { name: "macd", label: "MACD", params: { fast: 12, slow: 26, signal: 9 }, defaults: { fast: 12, slow: 26, signal: 9, color: "#26a69a", priceLabels: false }, paneMode: "shared" },
    { name: "cci", label: "CCI", params: { period: 20 }, defaults: { period: 20, color: "#7b1fa2", priceLabels: false }, paneMode: "shared" },
    { name: "mfi", label: "MFI", params: { period: 14 }, defaults: { period: 14, color: "#26a69a", priceLabels: false }, paneMode: "shared" },
    { name: "williams_r", label: "Williams %R", params: { period: 14 }, defaults: { period: 14, color: "#ef5350", priceLabels: false }, paneMode: "shared" },
    { name: "adx", label: "ADX", params: { period: 14 }, defaults: { period: 14, color: "#f9a825", priceLabels: false }, paneMode: "shared" },
  ],
  "Volatility": [
    { name: "atr", label: "ATR", params: { period: 14 }, defaults: { period: 14, color: "#ff7043", priceLabels: false }, paneMode: "shared" },
  ],
  "Volume": [
    { name: "volume", label: "Volume", params: {}, defaults: { color: "#808080" }, paneMode: "main" },
    { name: "obv", label: "OBV", params: {}, defaults: { color: "#42a5f5", priceLabels: false }, paneMode: "dedicated" },
  ],
};

// Per-line configuration for multi-line indicators (TV-style)
var INDICATOR_LINES = {
  "ichimoku": {
    members: ["ichimoku_tenkan", "ichimoku_kijun", "ichimoku_senkou_a", "ichimoku_senkou_b", "ichimoku_chikou"],
    cloud: true,
    defaults: {
      "ichimoku_tenkan": { color: "#4fc3f7", width: 1, visible: true, label: "Tenkan" },
      "ichimoku_kijun": { color: "#4fc3f7", width: 2, visible: true, label: "Kijun" },
      "ichimoku_senkou_a": { color: "#26a69a", width: 1, visible: true, label: "Senkou A" },
      "ichimoku_senkou_b": { color: "#ef5350", width: 2, visible: true, label: "Senkou B" },
      "ichimoku_chikou": { color: "#ff9800", width: 1, visible: true, label: "Chikou" },
      "cloud": { green: "#26a69a", red: "#ef5350", opacity: 0.9 },
    },
  },
  "bbands": {
    members: ["bbands_upper", "bbands_middle", "bbands_lower"],
    cloud: true,
    defaults: {
      "bbands_upper": { color: "#e94560", width: 1, visible: true, label: "Upper" },
      "bbands_middle": { color: "#e94560", width: 2, visible: true, label: "Middle" },
      "bbands_lower": { color: "#e94560", width: 1, visible: true, label: "Lower" },
      "cloud": { color: "#e94560", opacity: 0.1 },
    },
  },
  "macd": {
    members: ["macd_line", "macd_signal", "macd_histogram"],
    defaults: {
      "macd_line": { color: "#26a69a", width: 2, visible: true, label: "MACD" },
      "macd_signal": { color: "#e94560", width: 2, visible: true, label: "Signal" },
      "macd_histogram": { color: "#7b1fa2", visible: true, label: "Histogram" },
    },
  },
  "stoch": {
    members: ["stoch_k", "stoch_d"],
    defaults: {
      "stoch_k": { color: "#26a69a", width: 2, visible: true, label: "%K" },
      "stoch_d": { color: "#e94560", width: 2, visible: true, label: "%D" },
    },
  },
  "rsi": { members: ["rsi"], defaults: { "rsi": { color: "#ab47bc", width: 2, visible: true, label: "RSI" } } },
  "sma": { members: ["sma"], defaults: { "sma": { color: "#26a69a", width: 2, visible: true, label: "SMA" } } },
  "ema": { members: ["ema"], defaults: { "ema": { color: "#e94560", width: 2, visible: true, label: "EMA" } } },
  "vwap": { members: ["vwap"], defaults: { "vwap": { color: "#f9a825", width: 2, visible: true, label: "VWAP" } } },
  "cci": { members: ["cci"], defaults: { "cci": { color: "#7b1fa2", width: 2, visible: true, label: "CCI" } } },
  "mfi": { members: ["mfi"], defaults: { "mfi": { color: "#26a69a", width: 2, visible: true, label: "MFI" } } },
  "williams_r": { members: ["williams_r"], defaults: { "williams_r": { color: "#ef5350", width: 2, visible: true, label: "Williams %R" } } },
  "adx": { members: ["adx"], defaults: { "adx": { color: "#f9a825", width: 2, visible: true, label: "ADX" } } },
  "atr": { members: ["atr"], defaults: { "atr": { color: "#ff7043", width: 2, visible: true, label: "ATR" } } },
  "obv": { members: ["obv"], defaults: { "obv": { color: "#42a5f5", width: 2, visible: true, label: "OBV" } } },
};

// Zone defaults for momentum oscillators
var INDICATOR_ZONES = {
  "rsi": { levels: [{ value: 70, color: "#ef5350", label: "Overbought", width: 1 }, { value: 50, color: "#888", label: "Mid", width: 1 }, { value: 30, color: "#26a69a", label: "Oversold", width: 1 }] },
  "stoch": { levels: [{ value: 80, color: "#ef5350", label: "Overbought", width: 1 }, { value: 50, color: "#888", label: "Mid", width: 1 }, { value: 20, color: "#26a69a", label: "Oversold", width: 1 }] },
  "williams_r": { levels: [{ value: -20, color: "#ef5350", label: "Overbought", width: 1 }, { value: -50, color: "#888", label: "Mid", width: 1 }, { value: -80, color: "#26a69a", label: "Oversold", width: 1 }] },
  "cci": { levels: [{ value: 100, color: "#ef5350", label: "Overbought", width: 1 }, { value: 0, color: "#888", label: "Mid", width: 1 }, { value: -100, color: "#26a69a", label: "Oversold", width: 1 }] },
  "mfi": { levels: [{ value: 80, color: "#ef5350", label: "Overbought", width: 1 }, { value: 50, color: "#888", label: "Mid", width: 1 }, { value: 20, color: "#26a69a", label: "Oversold", width: 1 }] },
};

function showIndMenu() {
  var menu = document.getElementById("indMenu");
  if (menu.classList.contains("show")) { menu.classList.remove("show"); return; }
  var html = "";
  for (var cat in INDICATOR_CATALOG) {
    html += '<div class="ind-menu-cat">' + cat + "</div>";
    for (var i = 0; i < INDICATOR_CATALOG[cat].length; i++) {
      var ind = INDICATOR_CATALOG[cat][i];
      html += '<div class="ind-menu-item" data-ind="' + ind.name + '">' +
        '<span class="dot" style="background:' + ind.defaults.color + '"></span>' +
        ind.label + "</div>";
    }
  }
  menu.innerHTML = html;
  menu.onclick = function(e) {
    var item = e.target.closest(".ind-menu-item");
    if (item) { addIndicator(item.dataset.ind); }
  };
  menu.classList.add("show");
  setTimeout(function() {
    document.addEventListener("click", function _close(e) {
      if (!document.getElementById("indBar").contains(e.target)) {
        menu.classList.remove("show");
        document.removeEventListener("click", _close);
      }
    });
  }, 10);
}

function initLineSettings(name) {
  var lineCfg = INDICATOR_LINES[name];
  if (!lineCfg || !lineCfg.members) return {};
  var lines = {};
  for (var m = 0; m < lineCfg.members.length; m++) {
    var member = lineCfg.members[m];
    var def = (lineCfg.defaults && lineCfg.defaults[member]) || { color: "#26a69a", width: 2, visible: true };
    lines[member] = { color: def.color, width: def.width || 2, visible: def.visible !== false, label: def.label || member };
  }
  if (lineCfg.cloud) {
    var cdef = (lineCfg.defaults && lineCfg.defaults.cloud) || { green: "#26a69a", red: "#ef5350", opacity: 0.2 };
    lines.cloud = { green: cdef.green, red: cdef.red, opacity: cdef.opacity || 0.2 };
  }
  return lines;
}

function initZoneSettings(name) {
  var zdef = INDICATOR_ZONES[name];
  if (!zdef) return null;
  var zones = {};
  for (var z = 0; z < zdef.levels.length; z++) {
    var lv = zdef.levels[z];
    zones[lv.label] = { value: lv.value, color: lv.color, label: lv.label, visible: true, width: lv.width || 1 };
  }
  return zones;
}

function addIndicator(name) {
  document.getElementById("indMenu").classList.remove("show");
  var entry = null;
  for (var cat in INDICATOR_CATALOG) {
    for (var i = 0; i < INDICATOR_CATALOG[cat].length; i++) {
      if (INDICATOR_CATALOG[cat][i].name === name) { entry = INDICATOR_CATALOG[cat][i]; break; }
    }
    if (entry) break;
  }
  if (!entry) return;
  for (var j = 0; j < activeIndicators.length; j++) {
    if (activeIndicators[j].name === name) return;
  }
  var params = JSON.parse(JSON.stringify(entry.defaults));
  params.lines = initLineSettings(name);
  var zones = initZoneSettings(name);
  if (zones) params.zones = zones;
  activeIndicators.push({ name: name, label: entry.label, params: params, paneMode: entry.paneMode || "shared" });
  renderIndChips();
  computeAndRenderIndicators();
}

function renderIndChips() {
  var chips = document.getElementById("indChips");
  chips.innerHTML = "";
  for (var i = 0; i < activeIndicators.length; i++) {
    var ind = activeIndicators[i];
    var chip = document.createElement("span");
    chip.className = "ind-chip";
    chip.innerHTML =
      '<span class="dot" style="background:' + (ind.params.color || "#26a69a") + '"></span>' +
      ind.label +
      ' <span class="close" onclick="event.stopPropagation();removeIndicator(' + i + ')">&times;</span>';
    chip.onclick = function(idx) {
      return function() { openIndicatorConfig(idx); };
    }(i);
    chips.appendChild(chip);
  }
}

function removeIndicator(idx) {
  var ind = activeIndicators[idx];
  if (!ind) return;
  // Remove LightweightCharts series
  if (indicatorSeries[ind.name]) {
    var seriesList = indicatorSeries[ind.name];
    for (var s in seriesList) {
      if (chart) { try { chart.removeSeries(seriesList[s]); } catch(_) {} }
    }
    delete indicatorSeries[ind.name];
  }
  activeIndicators.splice(idx, 1);
  renderIndChips();
  if (activeIndicators.filter(function(a) { return a.name === ind.name; }).length === 0) {
    computeAndRenderIndicators();
  }
}

function openIndicatorConfig(idx) {
  var ind = activeIndicators[idx];
  if (!ind) return;
  var overlay = document.createElement("div");
  overlay.className = "ind-overlay show";
  overlay.id = "indConfigOverlay";
  overlay.onclick = function() { closeIndicatorConfig(); };
  var panel = document.createElement("div");
  panel.className = "ind-config";
  panel.onclick = function(e) { e.stopPropagation(); };
  var html = '<h3>' + ind.label + '</h3>';

  // ── Parameter fields ──
  if (ind.params.period !== undefined) {
    html += '<label>Period <input type="number" id="icfg_period" value="' + ind.params.period + '" min="2" max="200"></label>';
  }
  if (ind.params.stddev !== undefined) {
    html += '<label>Std Dev <input type="number" id="icfg_stddev" value="' + ind.params.stddev + '" min="0.5" max="5" step="0.1"></label>';
  }
  if (ind.params.fast !== undefined) {
    html += '<label>Fast <input type="number" id="icfg_fast" value="' + ind.params.fast + '" min="2" max="100"></label>';
  }
  if (ind.params.slow !== undefined) {
    html += '<label>Slow <input type="number" id="icfg_slow" value="' + ind.params.slow + '" min="2" max="200"></label>';
  }
  if (ind.params.signal !== undefined) {
    html += '<label>Signal <input type="number" id="icfg_signal" value="' + ind.params.signal + '" min="2" max="100"></label>';
  }
  if (ind.params.tenkan !== undefined) {
    html += '<label>Tenkan <input type="number" id="icfg_tenkan" value="' + ind.params.tenkan + '" min="2" max="200"></label>';
  }
  if (ind.params.kijun !== undefined) {
    html += '<label>Kijun <input type="number" id="icfg_kijun" value="' + ind.params.kijun + '" min="2" max="200"></label>';
  }
  if (ind.params.senkou !== undefined) {
    html += '<label>Senkou <input type="number" id="icfg_senkou" value="' + ind.params.senkou + '" min="2" max="200"></label>';
  }

  // ── Per-line settings (TV-style) ──
  var lineCfg = INDICATOR_LINES[ind.name];
  if (lineCfg && lineCfg.members && lineCfg.members.length > 0) {
    html += '<hr class="section-divider">';
    for (var li = 0; li < lineCfg.members.length; li++) {
      var member = lineCfg.members[li];
      var ls = (ind.params.lines && ind.params.lines[member]) || {};
      var def = (lineCfg.defaults && lineCfg.defaults[member]) || {};
      var lc = ls.color || def.color || "#26a69a";
      var lw = ls.width || def.width || 2;
      var lv = ls.visible !== false;
      var lm = ls.crosshair === true;
      var ll = def.label || member;
      html += '<div class="line-section" id="icfg_line_' + member + '">';
      html += '<h4>' + ll + '</h4>';
      html += '<div class="line-row">';
      html += '<label><input type="checkbox" id="icfg_vis_' + member + '" ' + (lv ? 'checked' : '') + ' onchange="var el=document.getElementById(' + "'icfg_line_" + member + "'" + ');if(el)el.style.opacity=this.checked?1:0.3"> Show</label>';
      html += '<label>Color <input type="color" id="icfg_color_' + member + '" value="' + lc + '"></label>';
      html += '<label>Width <select id="icfg_width_' + member + '">';
      for (var wi = 1; wi <= 4; wi++) {
        html += '<option value="' + wi + '"' + (lw == wi ? ' selected' : '') + '>' + wi + '</option>';
      }
      html += '</select></label>';
      html += '<label><input type="checkbox" id="icfg_crosshair_' + member + '" ' + (lm ? 'checked' : '') + '> Dotted</label>';
      html += '</div></div>';
    }
    // Cloud settings
    if (lineCfg.cloud) {
      var cs = (ind.params.lines && ind.params.lines.cloud) || {};
      var cdef = (lineCfg.defaults && lineCfg.defaults.cloud) || {};
      var cg = cs.green || cdef.green || "#26a69a";
      var cr = cs.red || cdef.red || "#ef5350";
      var co = (cs.opacity !== undefined ? cs.opacity : (cdef.opacity !== undefined ? cdef.opacity : 0.2));
      html += '<div class="line-section">';
      html += '<h4>Cloud Fill</h4>';
      html += '<div class="line-row">';
      html += '<label>Bull <input type="color" id="icfg_cloud_green" value="' + cg + '" title="Green cloud color"></label>';
      html += '<label>Bear <input type="color" id="icfg_cloud_red" value="' + cr + '" title="Red cloud color"></label>';
      html += '<label>Opacity <select id="icfg_cloud_opacity">';
      var opts = [0.1, 0.15, 0.2, 0.3, 0.4, 0.5];
      for (var oi = 0; oi < opts.length; oi++) {
        html += '<option value="' + opts[oi] + '"' + (Math.abs(co - opts[oi]) < 0.01 ? ' selected' : '') + '>' + Math.round(opts[oi] * 100) + '%</option>';
      }
      html += '</select></label>';
      html += '</div></div>';
    }
  }

  // ── Price labels toggle ──
  if (ind.name !== "volume") {
    var pl = ind.params.priceLabels !== false;
    html += '<hr class="section-divider">';
    html += '<div class="line-section"><h4>Price Labels</h4><div class="line-row">';
    html += '<label><input type="checkbox" id="icfg_priceLabels" ' + (pl ? 'checked' : '') + '> Show labels on price axis</label>';
    html += '</div></div>';
  }

  // ── Zone settings (momentum oscillators) ──
  if (ind.params.zones) {
    html += '<hr class="section-divider">';
    html += '<div class="line-section"><h4>Levels / Zones</h4>';
    for (var zk in ind.params.zones) {
      var zv = ind.params.zones[zk];
      var zw = zv.width || 1;
      html += '<div class="zone-row">';
      html += '<label><input type="checkbox" id="icfg_zone_vis_' + zk + '" ' + (zv.visible !== false ? 'checked' : '') + '></label>';
      html += '<label>' + zv.label + '</label>';
      html += '<input type="number" id="icfg_zone_val_' + zk + '" value="' + zv.value + '" step="1">';
      html += '<input type="color" id="icfg_zone_color_' + zk + '" value="' + zv.color + '">';
      html += '<select id="icfg_zone_width_' + zk + '">';
      for (var wi = 1; wi <= 4; wi++) {
        html += '<option value="' + wi + '"' + (zw == wi ? ' selected' : '') + '>' + wi + '</option>';
      }
      html += '</select>';
      html += '</div>';
    }
    html += '</div>';
  }

  html += '<hr class="section-divider">';
  html += '<button class="btn btn-primary" onclick="applyIndicatorConfig(' + idx + ')">Apply</button> ';
  html += '<button class="btn" onclick="closeIndicatorConfig()">Cancel</button>';
  html += '<button class="btn" style="float:right;color:#ef5350" onclick="closeIndicatorConfig();removeIndicator(' + idx + ')">Remove</button>';
  panel.innerHTML = html;
  overlay.appendChild(panel);
  document.body.appendChild(overlay);
}

function closeIndicatorConfig() {
  var overlay = document.getElementById("indConfigOverlay");
  if (overlay) { overlay.parentNode.removeChild(overlay); }
}

function applyIndicatorConfig(idx) {
  var ind = activeIndicators[idx];
  if (!ind) return;

  // Read basic params
  var paramFields = ["period", "stddev", "fast", "slow", "signal", "tenkan", "kijun", "senkou"];
  for (var pi = 0; pi < paramFields.length; pi++) {
    var el = document.getElementById("icfg_" + paramFields[pi]);
    if (el) ind.params[paramFields[pi]] = parseFloat(el.value) || paramFields[pi] === "stddev" ? parseFloat(el.value) || 2 : parseInt(el.value) || 1;
  }

  // Read per-line settings
  var lineCfg = INDICATOR_LINES[ind.name];
  if (lineCfg && lineCfg.members) {
    if (!ind.params.lines) ind.params.lines = {};
    for (var li = 0; li < lineCfg.members.length; li++) {
      var member = lineCfg.members[li];
      var visEl = document.getElementById("icfg_vis_" + member);
      var colEl = document.getElementById("icfg_color_" + member);
      var widEl = document.getElementById("icfg_width_" + member);
      var chEl = document.getElementById("icfg_crosshair_" + member);
      if (visEl || colEl || widEl) {
        ind.params.lines[member] = {
          visible: visEl ? visEl.checked : true,
          color: colEl ? colEl.value : "#26a69a",
          width: widEl ? parseInt(widEl.value) || 2 : 2,
          crosshair: chEl ? chEl.checked : false,
        };
      }
    }
    // Cloud settings
    if (lineCfg.cloud) {
      var cgEl = document.getElementById("icfg_cloud_green");
      var crEl = document.getElementById("icfg_cloud_red");
      var coEl = document.getElementById("icfg_cloud_opacity");
      if (cgEl || crEl || coEl) {
        ind.params.lines.cloud = {
          green: cgEl ? cgEl.value : "#26a69a",
          red: crEl ? crEl.value : "#ef5350",
          opacity: coEl ? parseFloat(coEl.value) : 0.2,
        };
      }
    }
  }

  // Read priceLabels toggle
  var plEl = document.getElementById("icfg_priceLabels");
  if (plEl) ind.params.priceLabels = plEl.checked;

  // Read zone settings
  if (ind.params.zones) {
    for (var zk in ind.params.zones) {
      var zvisEl = document.getElementById("icfg_zone_vis_" + zk);
      var zvalEl = document.getElementById("icfg_zone_val_" + zk);
      var zcolEl = document.getElementById("icfg_zone_color_" + zk);
      var zwidEl = document.getElementById("icfg_zone_width_" + zk);
      if (zvisEl) ind.params.zones[zk].visible = zvisEl.checked;
      if (zvalEl) ind.params.zones[zk].value = parseFloat(zvalEl.value) || 0;
      if (zcolEl) ind.params.zones[zk].color = zcolEl.value;
      if (zwidEl) ind.params.zones[zk].width = parseInt(zwidEl.value) || 1;
    }
  }

  closeIndicatorConfig();
  renderIndChips();
  computeAndRenderIndicators();
  saveIndicatorSettings();
}

function hexToRgba(hex, alpha) {
  var r = parseInt(hex.slice(1, 3), 16) || 0;
  var g = parseInt(hex.slice(3, 5), 16) || 0;
  var b = parseInt(hex.slice(5, 7), 16) || 0;
  return "rgba(" + r + "," + g + "," + b + "," + alpha + ")";
}

// ── Cloud Canvas Overlay (draws outside chart pipeline via single-shot rAF) ──
var _cloudOverlays = {};
var _cloudDrawRequestId = null;

function ensureCloudCanvas() {
  var c = document.getElementById('cloudCanvas');
  if (c) return c;
  var container = document.getElementById('chart');
  if (!container) return null;
  container.style.position = 'relative';
  c = document.createElement('canvas');
  c.id = 'cloudCanvas';
  c.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:10;';
  container.appendChild(c);
  return c;
}

function scheduleCloudDraw() {
  if (_cloudDrawRequestId) return;
  _cloudDrawRequestId = requestAnimationFrame(function() {
    _cloudDrawRequestId = null;
    drawCloud();
  });
}

function drawCloud() {
  var canvas = ensureCloudCanvas();
  if (!canvas) return;
  var chartEl = document.getElementById('chart');
  if (!chartEl) return;
  var dpr = window.devicePixelRatio || 1;
  var w = chartEl.clientWidth;
  var h = chartEl.clientHeight;
  if (w === 0 || h === 0) return;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  var ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, w, h);

  var ts = chart.timeScale();
  var vr = ts.getVisibleRange();
  if (!vr) return;
  var pad = (vr.to - vr.from) * 0.15;
  var lo = vr.from - pad, hi = vr.to + pad;

  for (var key in _cloudOverlays) {
    var cloud = _cloudOverlays[key];
    var points = cloud.points;
    var colors = cloud.colors;
    var seriesA = cloud.seriesA;
    var seriesB = cloud.seriesB;

    var pixelData = [];
    for (var i = 0; i < points.length; i++) {
      var p = points[i];
      if (p.time < lo || p.time > hi) continue;
      var x = ts.timeToCoordinate(p.time);
      if (x === null) continue;
      var ya = seriesA.priceToCoordinate(p.a);
      var yb = seriesB.priceToCoordinate(p.b);
      if (ya === null || yb === null) continue;
      pixelData.push({ x: x, yA: ya, yB: yb });
    }
    if (pixelData.length < 2) continue;

    var i = 0;
    while (i < pixelData.length - 1) {
      var mA = (pixelData[i].yA + pixelData[i + 1].yA) / 2;
      var mB = (pixelData[i].yB + pixelData[i + 1].yB) / 2;
      var isGreen = mA <= mB;
      ctx.fillStyle = isGreen ? colors.green : colors.red;
      var start = i;
      i++;
      while (i < pixelData.length - 1) {
        mA = (pixelData[i].yA + pixelData[i + 1].yA) / 2;
        mB = (pixelData[i].yB + pixelData[i + 1].yB) / 2;
        if ((mA <= mB) !== isGreen) break;
        i++;
      }
      var end = i;
      ctx.beginPath();
      ctx.moveTo(pixelData[start].x, pixelData[start].yA);
      for (var j = start + 1; j <= end; j++) ctx.lineTo(pixelData[j].x, pixelData[j].yA);
      for (var j = end; j >= start; j--) ctx.lineTo(pixelData[j].x, pixelData[j].yB);
      ctx.closePath();
      ctx.fill();
    }
  }
}

function removeCloudOverlay() {
  _cloudOverlays = {};
  if (_cloudDrawRequestId) { cancelAnimationFrame(_cloudDrawRequestId); _cloudDrawRequestId = null; }
}

function renderCloudFill(candles, topName, bottomName, inds) {
  // Resolve cloud colors from active indicator settings
  var indicatorName = null;
  for (var key in _cloudOverlays) { delete _cloudOverlays[key]; }
  // Find which indicator this cloud belongs to
  for (var a = 0; a < activeIndicators.length; a++) {
    if (topName.indexOf(activeIndicators[a].name) === 0) {
      indicatorName = activeIndicators[a].name;
      break;
    }
  }
  if (!indicatorName) return;

  var cloudColors = { green: "rgba(38,166,154,0.2)", red: "rgba(239,83,80,0.2)" };
  for (var a = 0; a < activeIndicators.length; a++) {
    if (activeIndicators[a].name === indicatorName && activeIndicators[a].params.lines && activeIndicators[a].params.lines.cloud) {
      var cl = activeIndicators[a].params.lines.cloud;
      var opacity = cl.opacity !== undefined ? cl.opacity : 0.2;
      cloudColors.green = cl.green ? hexToRgba(cl.green, opacity) : cloudColors.green;
      cloudColors.red = cl.red ? hexToRgba(cl.red, opacity) : cloudColors.red;
      break;
    }
  }

  var sa = inds[topName];
  var sb = inds[bottomName];
  if (!sa || !sb || sa.error || sb.error) return;
  var aVals = sa.values;
  var bVals = sb.values;
  if (!aVals || !bVals) return;

  var cloudShift = sa.shift || 0;
  var barMs = candles.length > 1 ? candles[candles.length - 1].t - candles[candles.length - 2].t : 60000;
  var points = [];
  for (var i = 0; i < Math.min(aVals.length, bVals.length, candles.length); i++) {
    if (aVals[i] === null || aVals[i] === undefined) continue;
    if (bVals[i] === null || bVals[i] === undefined) continue;
    var idx = i + cloudShift;
    var t;
    if (idx >= 0 && idx < candles.length) {
      t = Math.floor(candles[idx].t / 1000);
    } else if (idx >= candles.length) {
      t = Math.floor((candles[candles.length - 1].t + (idx - candles.length + 1) * barMs) / 1000);
    } else {
      t = Math.floor((candles[0].t + idx * barMs) / 1000);
    }
    points.push({ time: t, a: aVals[i], b: bVals[i] });
  }
  if (points.length === 0) return;

  var seriesA = indicatorSeries[topName];
  var seriesB = indicatorSeries[bottomName];
  var senkouASeries = null, senkouBSeries = null;
  for (var k in seriesA) { senkouASeries = seriesA[k]; break; }
  for (var k in seriesB) { senkouBSeries = seriesB[k]; break; }
  if (!senkouASeries || !senkouBSeries) return;

  var cloudKey = "cloud_" + topName + "_" + bottomName;
  _cloudOverlays[cloudKey] = { seriesA: senkouASeries, seriesB: senkouBSeries, points: points, colors: cloudColors };
  scheduleCloudDraw();
}

function showStatus(msg, isError) {
  var el = document.getElementById("status");
  if (el) { el.textContent = msg; el.style.color = isError ? "#ef5350" : "#888"; }
}

function renderVolumeIndicator() {
  if (indicatorSeries["volume"]) {
    var seriesList = indicatorSeries["volume"];
    for (var s in seriesList) {
      if (chart) { try { chart.removeSeries(seriesList[s]); } catch(_) {} }
    }
    delete indicatorSeries["volume"];
  }
  var data = _cachedCandles;
  if (!data || !data.candles || data.candles.length === 0) return;
  var candles = data.candles;
  var cs = loadChartSettings();
  var bullColor = cs.bullBody || "#808080";
  var bearColor = cs.bearBody || "#2d2d2d";
  var vols = candles.map(function(c) {
    return {
      time: Math.floor(c.t / 1000),
      value: c.v,
      color: c.c >= c.o ? bullColor : bearColor,
    };
  });
  if (vols.length === 0) return;
  var series = chart.addSeries(LightweightCharts.HistogramSeries, {
    color: bullColor,
    priceFormat: { type: 'volume' },
    priceScaleId: 'volume',
    axisLabelVisible: false,
  }, 0);
  chart.priceScale('volume').applyOptions({
    scaleMargins: { top: 0.8, bottom: 0 },
  });
  series.setData(vols);
  if (!indicatorSeries["volume"]) indicatorSeries["volume"] = {};
  indicatorSeries["volume"][0] = series;
}

function computeAndRenderIndicators() {
  if (!chart || activeIndicators.length === 0) return;

  // Filter out client-only indicators (volume) from API request
  var hasVolume = false;
  var apiIndicators = [];
  for (var i = 0; i < activeIndicators.length; i++) {
    var ind = activeIndicators[i];
    if (ind.name === "volume") {
      hasVolume = true;
    } else {
      apiIndicators.push(ind);
    }
  }

  if (apiIndicators.length > 0) {
    var req = {
      exchange: exchangeEl.value,
      symbol: symbolEl.value,
      timeframe: timeframeEl.value,
      limit: window._candleData ? window._candleData.length : _maxBars,
      indicators: apiIndicators.map(function(ind) {
        var params = {};
        for (var k in ind.params) {
          if (k !== "color" && k !== "width" && k !== "label" && k !== "lines" && k !== "zones") params[k] = ind.params[k];
        }
        return { name: ind.name, params: params };
      }),
    };
    var url = "/api/indicators/compute";
    showStatus("Computing indicators...");
    fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (data.error) { showStatus("Indicator error: " + data.error, true); return; }
        renderIndicatorSeries(data);
        if (hasVolume) renderVolumeIndicator();
        showStatus("");
      })
      .catch(function(e) { showStatus("Indicator compute failed: " + e.message, true); });
  } else {
    // Only client-side indicators active — clean up API series & panes, render volume
    for (var name in indicatorSeries) {
      if (name === "volume") continue;
      var seriesList = indicatorSeries[name];
      for (var s in seriesList) {
        if (chart) { try { chart.removeSeries(seriesList[s]); } catch(_) {} }
      }
      delete indicatorSeries[name];
    }
    for (var pid in _panes) {
      if (chart) { try { chart.removePane(parseInt(pid)); } catch(_) {} }
      var header = document.getElementById("paneHeader_" + pid);
      if (header) header.parentNode.removeChild(header);
      var handle = document.getElementById("paneHandle_" + pid);
      if (handle) handle.parentNode.removeChild(handle);
    }
    _panes = {};
    _paneIndicators = {};
    removeCloudOverlay();
    if (hasVolume) renderVolumeIndicator();
    showStatus("");
  }
}

function findCatalogEntry(name) {
  for (var cat in INDICATOR_CATALOG) {
    for (var i = 0; i < INDICATOR_CATALOG[cat].length; i++) {
      if (INDICATOR_CATALOG[cat][i].name === name) return INDICATOR_CATALOG[cat][i];
    }
  }
  return null;
}

var _panes = {};
var _paneIndicators = {};
var _nextPaneNum = 1;

function getOrCreatePane(mode, indicatorName) {
  if (mode === "main") return 0;
  var shared = false;
  if (mode === "shared") shared = true;
  for (var pid in _panes) {
    var p = _panes[pid];
    if (shared && p.mode === "shared") return parseInt(pid);
  }
  var num = _nextPaneNum++;
  var height = shared ? 50 : 70;
  // Pane will be created implicitly by addSeries(..., paneIndex) later
  _panes[num] = { mode: shared ? "shared" : "dedicated", height: height };
  _paneIndicators[num] = [];
  return num;
}

function renderIndicatorSeries(data) {
  for (var name in indicatorSeries) {
    var seriesList = indicatorSeries[name];
    for (var s in seriesList) {
      if (chart) { try { chart.removeSeries(seriesList[s]); } catch(_) {} }
    }
  }
  indicatorSeries = {};

  for (var pid in _panes) {
    if (chart) { try { chart.removePane(parseInt(pid)); } catch(_) {} }
    var header = document.getElementById("paneHeader_" + pid);
    if (header) header.parentNode.removeChild(header);
    var handle = document.getElementById("paneHandle_" + pid);
    if (handle) handle.parentNode.removeChild(handle);
  }
  _panes = {};
  _paneIndicators = {};
  removeCloudOverlay();

  var inds = data.indicators;
  if (!inds) return;
  var groups = data.indicator_groups || {};

  var paneAssignments = {};
  for (var a = 0; a < activeIndicators.length; a++) {
    var act = activeIndicators[a];
    var entry = findCatalogEntry(act.name);
    var mode = entry ? entry.paneMode : "shared";
    act.paneMode = mode;
    var pid;
    var assignKey = mode === "dedicated" ? act.name : mode;
    if (paneAssignments[assignKey] !== undefined) {
      pid = paneAssignments[assignKey];
    } else {
      pid = getOrCreatePane(mode, act.name);
      paneAssignments[assignKey] = pid;
    }
    if (_paneIndicators[pid]) _paneIndicators[pid].push(act.name);
  }

  for (var name in inds) {
    var ind = inds[name];
    if (ind.error || !ind.values) continue;

    var resolvedPane = ind.pane || 0;
    if (resolvedPane > 0) {
      for (var a = 0; a < activeIndicators.length; a++) {
        if (name.indexOf(activeIndicators[a].name) === 0) {
          var act = activeIndicators[a];
          var mode = act.paneMode || "shared";
          resolvedPane = mode === "main" ? 0 : paneAssignments[mode === "dedicated" ? act.name : mode];
          break;
        }
      }
    }

    var activeMatch = null;
    for (var a = 0; a < activeIndicators.length; a++) {
      if (name.indexOf(activeIndicators[a].name) === 0) { activeMatch = activeIndicators[a]; break; }
    }

    // Per-line settings lookup
    var lineColor = ind.color || "#26a69a";
    var lineWidth = 2;
    var lineVisible = true;
    var lineCrosshair = false;
    var activeName = activeMatch ? activeMatch.name : "";
    if (activeMatch && activeMatch.params.lines && activeMatch.params.lines[name]) {
      var ls = activeMatch.params.lines[name];
      lineColor = ls.color || lineColor;
      lineWidth = ls.width || lineWidth;
      lineVisible = ls.visible !== false;
      lineCrosshair = ls.crosshair === true;
    }
    if (!lineVisible) continue;

    var candles = data.candles || [];
    var points = [];
    var shift = ind.shift || 0;
    var barMs = candles.length > 1 ? candles[candles.length - 1].t - candles[candles.length - 2].t : 60000;

    for (var i = 0; i < ind.values.length; i++) {
      if (ind.values[i] === null || ind.values[i] === undefined) continue;
      var idx = i + shift;
      var time;
      if (shift === 0) {
        if (i >= candles.length) break;
        time = Math.floor(candles[i].t / 1000);
      } else if (idx >= 0 && idx < candles.length) {
        time = Math.floor(candles[idx].t / 1000);
      } else if (idx >= candles.length) {
        var barsPast = idx - (candles.length - 1);
        time = Math.floor((candles[candles.length - 1].t + barsPast * barMs) / 1000);
      } else {
        // idx < 0: project backward (e.g. Chikou lagging span)
        time = Math.floor((candles[0].t + idx * barMs) / 1000);
      }
      points.push({ time: time, value: ind.values[i] });
    }
    if (points.length === 0) continue;

    var showLabel = activeMatch && activeMatch.params.priceLabels !== false;
    var series;
    var scaleOpts = resolvedPane === 0 ? { priceScaleId: 'price' } : {};
    if (ind.style === "histogram") {
      series = chart.addSeries(LightweightCharts.HistogramSeries, Object.assign({ color: lineColor, priceFormat: { type: "volume" }, crosshairMarkerVisible: false, axisLabelVisible: false }, scaleOpts), resolvedPane);
    } else {
      series = chart.addSeries(LightweightCharts.LineSeries, Object.assign({ color: lineColor, lineWidth: lineWidth, crosshairMarkerVisible: lineCrosshair, axisLabelVisible: showLabel }, scaleOpts), resolvedPane);
    }
    series.setData(points);
    // Leave pane height auto-managed by LightweightCharts so time scale stays visible
    if (!indicatorSeries[name]) indicatorSeries[name] = {};
    indicatorSeries[name][resolvedPane] = series;
  }

  for (var gname in groups) {
    var g = groups[gname];
    if (g.cloud) {
      renderCloudFill(data.candles || [], g.cloud.top, g.cloud.bottom, inds);
    }
  }

  // Render zone lines for momentum oscillators
  for (var a = 0; a < activeIndicators.length; a++) {
    var act = activeIndicators[a];
    if (!act.params.zones) continue;
    var zonePid = act.paneMode === "main" ? 0 : (paneAssignments[act.paneMode === "dedicated" ? act.name : act.paneMode] || 0);
    var firstSeriesInPane = null;
    for (var sn in indicatorSeries) {
      if (indicatorSeries[sn][zonePid]) { firstSeriesInPane = indicatorSeries[sn][zonePid]; break; }
    }
    if (!firstSeriesInPane) continue;
    for (var zk in act.params.zones) {
      var z = act.params.zones[zk];
      if (z.visible === false) continue;
      // Remove old price line if it exists
      var plKey = "_pline_" + act.name + "_" + zk;
      if (firstSeriesInPane[plKey]) {
        try { firstSeriesInPane.removePriceLine(firstSeriesInPane[plKey]); } catch(_) {}
      }
      var pl = firstSeriesInPane.createPriceLine({
        price: z.value,
        color: z.color || "#888",
        lineWidth: z.width || 1,
        lineStyle: LightweightCharts.LineStyle.Dashed,
        axisLabelVisible: true,
        title: z.label,
      });
      firstSeriesInPane[plKey] = pl;
    }
  }

  for (var pid in _panes) {
    var p = _panes[pid];
    var indsInPane = _paneIndicators[pid] || [];
    var label = indsInPane.map(function(n) {
      for (var a = 0; a < activeIndicators.length; a++) {
        if (activeIndicators[a].name === n) return activeIndicators[a].label;
      }
      return n;
    }).join(", ") || "Pane " + pid;

    var header = document.createElement("div");
    header.id = "paneHeader_" + pid;
    header.className = "pane-header";
    header.style.cssText = "display:flex;align-items:center;background:#16213e;padding:2px 8px;font-size:11px;color:#888;border-bottom:1px solid #0f3460;cursor:default;";
    header.innerHTML = '<span style="flex:1">' + label + '</span><span style="color:#555;font-size:10px;cursor:pointer" onclick="removePaneIndicators(' + pid + ')">×</span>';

    var wrapper = document.getElementById("chart-wrapper");
    wrapper.appendChild(header);
    var handle = document.createElement("div");
    handle.id = "paneHandle_" + pid;
    handle.className = "pane-resize-handle";
    handle.style.cssText = "height:4px;cursor:ns-resize;background:#0f3460;";
    wrapper.appendChild(handle);
  }
}

function removePaneIndicators(pid) {
  var paneNames = _paneIndicators[pid] || [];
  for (var i = activeIndicators.length - 1; i >= 0; i--) {
    if (paneNames.indexOf(activeIndicators[i].name) >= 0) {
      removeIndicator(i);
    }
  }
}

function stopLive() {
  if (window._liveRetryTimer) { clearTimeout(window._liveRetryTimer); window._liveRetryTimer = null; }
  if (eventSource) { eventSource.close(); eventSource = null; }
}

function startLive() {
  stopLive();
  const ex = exchangeEl.value, sym = symbolEl.value, tf = timeframeEl.value;
  if (!ex || !sym || !lastCandleTime) return;
  const url = `/api/events?exchange=${ex}&symbol=${sym}&timeframe=${tf}&since=${lastCandleTime}`;
  eventSource = new EventSource(url);
  eventSource.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      if (!data.candles || data.candles.length === 0) return;
      // normalise: SSE returns raw SQLite rows, convert to {t, o, h, l, c, v}
      const normalized = data.candles.map(c => ({
        t: c.timestamp, o: c.open, h: c.high, l: c.low, c: c.close, v: c.volume,
        timestamp: c.timestamp,
        open: c.open, high: c.high, low: c.low, close: c.close, volume: c.volume,
      }));
      const newC = normalized.filter(c => c.t > lastCandleTime);
      if (newC.length === 0) return;
      for (const c of newC) {
        const point = {
          time: Math.floor(c.t / 1000),
          open: c.o, high: c.h, low: c.l, close: c.c,
        };
        candleSeries.update(point);
        if (indicatorSeries["volume"] && indicatorSeries["volume"][0]) {
          const __cs = loadChartSettings();
          indicatorSeries["volume"][0].update({
            time: Math.floor(c.t / 1000),
            value: c.v,
            color: c.c >= c.o ? __cs.bullBody : __cs.bearBody,
          });
        }
        if (window._candleData) {
          const idx = window._candleData.findIndex(d => d.time === point.time);
          if (idx >= 0) window._candleData[idx] = point;
          else {
            window._candleData.push(point);
            // Cap memory — trim oldest when exceeding maxBars buffer
            if (window._candleData.length > _maxBars + 200) {
              window._candleData = window._candleData.slice(-_maxBars);
              candleSeries.setData(window._candleData);
              // Update price levels when data is trimmed
              updatePriceLevels(window._candleData);
            }
          }
        }
      }
      // Schedule cloud redraw for live candles
      scheduleCloudDraw();
      lastCandleTime = newC[newC.length - 1].t;
      const to = msToDate(lastCandleTime);
      statusEl.textContent = `${data.count} candles  |  ... → ${to}  (live)`;
    } catch (_) {}
  };
  eventSource.onerror = () => {
    // SSE connection lost — fall back to polling after 30s
    window._liveRetryTimer = setTimeout(() => { if (!eventSource) startLive(); }, 30000);
  };
}

const TF_SEC = {
  '1m':60,'5m':300,'15m':900,'30m':1800,'1H':3600,'2H':7200,'4H':14400,'6H':21600,'12H':43200,
  '1D':86400,'2D':172800,'3D':259200,'1W':604800,'2W':1209600,'1M':2592000,
};

function initChart() {
  chart = LightweightCharts.createChart(document.getElementById('chart'), {
    layout: { textColor: '#555', background: { color: '#f5f5f5' } },
    grid: { vertLines: { color: '#d0d0d0' }, horzLines: { color: '#c0c0c0', style: LightweightCharts.LineStyle.Dashed } },
    timeScale: {
      visible: true,
      timeVisible: true,
      secondsVisible: false,
      borderColor: '#0f3460',
      entireTextOnly: false,
      tickMarkFormatter: (time, tickMarkType, locale) => {
        const d = new Date(time * 1000);
        return d.toLocaleString('fr-FR', {
          timeZone: 'Europe/Paris',
          hour: '2-digit', minute: '2-digit',
          day: tickMarkType > 2 ? '2-digit' : undefined,
          month: tickMarkType > 2 ? 'short' : undefined,
        });
      },
    },
    rightPriceScale: { visible: true, borderColor: '#0f3460', entireTextOnly: false, ticksVisible: true },
    leftPriceScale: { visible: true, borderColor: '#0f3460', entireTextOnly: false, ticksVisible: true },
    handleScroll: { vertTouchDrag: true, horzTouchDrag: true, pressedMouseMove: true },
    handleScale: { axisPressedMouseMove: { time: true, price: true }, pinch: true, mouseWheel: true },
    crosshair: {
      mode: LightweightCharts.CrosshairMode.Normal,
      vertLine: { visible: false, labelBackgroundColor: '#e94560', color: '#e94560', width: 1 },
      horzLine: { visible: false, labelBackgroundColor: '#e94560', color: '#e94560', width: 1 },
    },
    localization: {
      locale: 'fr-FR',
      timeFormatter: (time) => {
        const d = new Date(time * 1000);
        return d.toLocaleString('fr-FR', { timeZone: 'Europe/Paris', hour: '2-digit', minute: '2-digit', day: '2-digit', month: 'short', year: 'numeric' });
      },
      dateFormatter: (time) => {
        const d = new Date(time * 1000);
        return d.toLocaleDateString('fr-FR', { timeZone: 'Europe/Paris', day: '2-digit', month: 'short', year: 'numeric' });
      },
    },
  });
  candleSeries = chart.addSeries(LightweightCharts.CandlestickSeries, {
    upColor: '#26a69a', downColor: '#ef5350',
    borderUpColor: '#26a69a', borderDownColor: '#ef5350',
    wickUpColor: '#26a69a', wickDownColor: '#ef5350',
    priceScaleId: 'price',
  }, 0);

  // Create an invisible series to drive the left price scale (Option A)
  var leftScaleDummy = chart.addSeries(LightweightCharts.LineSeries, {
    priceScaleId: 'left',
    visible: false,
  }, 0);
  window._leftScaleDummy = leftScaleDummy;

  // Apply saved chart settings
  var cs = loadChartSettings();
  candleSeries.applyOptions({
    upColor: cs.bullBody, downColor: cs.bearBody,
    borderUpColor: cs.bullBody, borderDownColor: cs.bearBody,
    wickUpColor: cs.bullWick, wickDownColor: cs.bearWick,
  });
  chart.applyOptions({ layout: { background: { color: cs.chartBg } } });
  // Apply saved crosshair lines visibility
  chart.applyOptions({
    crosshair: {
      vertLine: { visible: cs.crosshairLines, labelBackgroundColor: '#e94560', color: '#e94560', width: 1 },
      horzLine: { visible: cs.crosshairLines, labelBackgroundColor: '#e94560', color: '#e94560', width: 1 },
    },
  });

  // Ensure time scale is visible (needed for sub-panes in v5)
  chart.timeScale().applyOptions({ visible: true, timeVisible: true });

  // Subscribe to time range changes for cloud overlay redraw
  try { chart.timeScale().subscribeVisibleTimeRangeChange(function() { scheduleCloudDraw(); }); } catch(e) { /* v5 removed this method */ }

  // Crosshair legend: show indicator values on hover
  var legendEl = document.getElementById('crosshairLegend');
  // Unsubscribe previous legend handler to prevent pile-up
  if (window._legendHandler) {
    chart.unsubscribeCrosshairMove(window._legendHandler);
    window._legendHandler = null;
  }
  window._legendHandler = function(param) {
    if (!param.point || !param.time) {
      legendEl.style.display = 'none';
      return;
    }
    if (!window.loadedIndicators) {
      legendEl.style.display = 'none';
      return;
    }
    var lines = [];
    // Timestamp at top
    if (param.time) {
      var d = new Date(param.time * 1000);
      lines.push('<span style="color:#888">' + d.toLocaleString('fr-FR', { timeZone: 'Europe/Paris', hour: '2-digit', minute: '2-digit', day: '2-digit', month: 'short', year: 'numeric' }) + '</span>');
    }
    // Candle price
    if (param.seriesData && param.seriesData.has(candleSeries)) {
      var cd = param.seriesData.get(candleSeries);
      if (cd && typeof cd.value !== 'undefined') {
        lines.push('O: ' + cd.open.toFixed(2) + ' H: ' + cd.high.toFixed(2) + ' L: ' + cd.low.toFixed(2) + ' C: ' + cd.close.toFixed(2));
      }
    }
    // Indicator series values
    for (var name in indicatorSeries) {
      for (var pid in indicatorSeries[name]) {
        var s = indicatorSeries[name][pid];
        if (param.seriesData && param.seriesData.has(s)) {
          var d = param.seriesData.get(s);
          if (d && typeof d.value !== 'undefined') {
            var label = name.replace(/^ichimoku_/, '');
            lines.push(label + ': ' + d.value.toFixed(2));
          }
        }
      }
    }
    if (lines.length > 0) {
      legendEl.innerHTML = lines.join('<br>');
      legendEl.style.display = 'block';
    } else {
      legendEl.style.display = 'none';
    }
  };
  chart.subscribeCrosshairMove(window._legendHandler);
}

var _zoomLock = 'both'; // 'time', 'price', or 'both'

function goToLatest() {
  try {
    chart.timeScale().fitContent();
    chart.timeScale().scrollToRealTime();
    candleSeries.priceScale().applyOptions({ autoScale: true });
    setZoomLock('both');
  } catch(e) { console.error('goToLatest failed:', e); }
}

function setZoomLock(mode) {
  _zoomLock = mode;
  try {
    chart.applyOptions({
      handleScale: {
        axisPressedMouseMove: {
          time: mode === 'both' || mode === 'time',
          price: mode === 'both' || mode === 'price',
        },
      },
    });
  } catch(e) {}
}

document.addEventListener('keydown', function(e) {
  if ((e.key === 'z' || e.key === 'Z') && !e.ctrlKey && !e.metaKey && document.activeElement && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA' && document.activeElement.getAttribute('contenteditable') !== 'true') {
    var modes = ['both', 'time', 'price'];
    var idx = modes.indexOf(_zoomLock);
    setZoomLock(modes[(idx + 1) % modes.length]);
  }
});

var _candleEarliestTime = 0;
var _loadOlderTimer = null;

function startLoadOlderPolling() {
  stopLoadOlderPolling();
  _loadOlderTimer = setInterval(function() {
    var btn = document.getElementById('load-older-btn');
    if (!btn || !chart || !window._candleData || window._candleData.length === 0) return;
    try {
      var vr = chart.timeScale().getVisibleRange();
      if (!vr) { btn.style.display = 'none'; return; }
      // Show button if visible range includes the earliest loaded candle
      var firstTime = window._candleData[0].time;
      var show = vr.from <= firstTime + 5;
      btn.style.display = show ? 'block' : 'none';
    } catch(_) { btn.style.display = 'none'; }
  }, 1000);
}
function stopLoadOlderPolling() {
  if (_loadOlderTimer) { clearInterval(_loadOlderTimer); _loadOlderTimer = null; }
}

async function loadOlderCandles() {
  if (!window._candleData || window._candleData.length === 0) return;
  var btn = document.getElementById('load-older-btn');
  if (btn) btn.style.display = 'none';
  var ex = exchangeEl.value, sym = symbolEl.value, tf = timeframeEl.value;
  var firstMs = _candleEarliestTime || (window._candleData[0].time * 1000);
  var url = '/api/candles?exchange=' + ex + '&symbol=' + sym + '&timeframe=' + tf + '&limit=' + _maxBars + '&end_time=' + (firstMs - 1);
  try {
    var r = await fetch(url);
    var data = await r.json();
    if (!data.candles || data.candles.length === 0) {
      if (btn) btn.title = 'No more data';
      return;
    }
    var oldCandles = data.candles.map(function(c) {
      return { time: Math.floor(c.timestamp / 1000), open: c.open, high: c.high, low: c.low, close: c.close };
    });
    // data.candles is in ascending order, window._candleData is also ascending — concat preserves sorted order
    // NO .reverse() — that would create non-monotonic data, breaking LightweightCharts' setData
    // Prepend older candles
    window._candleData = oldCandles.concat(window._candleData);
    _candleEarliestTime = data.candles[0].timestamp;
    candleSeries.setData(window._candleData);
    _priceLevelRange = 0; // force rebuild on wider range
    updatePriceLevels(window._candleData);
    // Re-compute indicators with full dataset
    if (activeIndicators.length > 0) computeAndRenderIndicators();
    chart.timeScale().fitContent();
  } catch(e) { console.error('loadOlderCandles failed:', e); }
}

function autoResizePanes() {
  try {
    // Auto-scale main pane's price scale
    if (candleSeries) candleSeries.priceScale().applyOptions({ autoScale: true });
    // Auto-scale all sub-pane price scales via their first series
    for (var name in indicatorSeries) {
      if (name === "volume") continue;
      var seriesList = indicatorSeries[name];
      for (var pid in seriesList) {
        if (parseInt(pid) > 0) {
          try { seriesList[pid].priceScale().applyOptions({ autoScale: true }); } catch(_) {}
        }
      }
    }
  } catch(e) { console.error('autoResizePanes failed:', e); }
}

function goToLatest() {
  try {
    chart.timeScale().scrollToRealTime();
  } catch(e) { console.error('goToLatest failed:', e); }
}

// Mousedown on price scale → select price zoom, time scale → select time zoom, else both
// This lets you click-drag the scale labels to zoom that axis, then wheel-zoom on chart uses same axis
document.getElementById('chart-wrapper').addEventListener('mousedown', function(e) {
  var chartEl = document.getElementById('chart');
  var rect = chartEl.getBoundingClientRect();
  var x = e.clientX - rect.left;
  var y = e.clientY - rect.top;
  var w = chartEl.clientWidth;
  var h = chartEl.clientHeight;
  if (x > w - 55) { setZoomLock('price'); }
  else if (y > h - 30) { setZoomLock('time'); }
  else { setZoomLock('both'); }
});

function msToDateTime(ms) {
  return new Date(ms).toLocaleString('fr-FR', { timeZone: 'Europe/Paris', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
}
function msToDate(ms) {
  return new Date(ms).toLocaleDateString('fr-FR', { timeZone: 'Europe/Paris', year: 'numeric', month: '2-digit', day: '2-digit' });
}
function dateToMs(d) {
  const [y, m, day] = d.split('-').map(Number);
  return new Date(y, m - 1, day).getTime();
}

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

var _priceLevelLines = [];
var _priceLevelRange = 0;

function updatePriceLevels(candles) {
  if (!candles || candles.length < 2) return;
  var lo = Infinity, hi = -Infinity;
  for (var ci = 0; ci < candles.length; ci++) {
    if (candles[ci].low < lo) lo = candles[ci].low;
    if (candles[ci].high > hi) hi = candles[ci].high;
  }
  var range = hi - lo;
  if (range <= 0) return;
  // Throttle: only rebuild if range changed by >1%
  if (_priceLevelRange > 0 && Math.abs(range - _priceLevelRange) / _priceLevelRange < 0.01) return;
  _priceLevelRange = range;
  // Remove old price level lines
  for (var pi = 0; pi < _priceLevelLines.length; pi++) {
    try { candleSeries.removePriceLine(_priceLevelLines[pi]); } catch(_) {}
  }
  _priceLevelLines = [];
  // Compute "nice" interval
  var rawStep = range / 8;
  var magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)));
  var residual = rawStep / magnitude;
  var niceStep;
  if (residual <= 1.5) niceStep = magnitude;
  else if (residual <= 3.5) niceStep = 2 * magnitude;
  else if (residual <= 7.5) niceStep = 5 * magnitude;
  else niceStep = 10 * magnitude;
  var start = Math.ceil(lo / niceStep) * niceStep;
  for (var p = start; p <= hi; p += niceStep) {
    _priceLevelLines.push(candleSeries.createPriceLine({
      price: p,
      color: 'rgba(255,255,255,0.25)',
      lineWidth: 1,
      lineStyle: LightweightCharts.LineStyle.Dashed,
      axisLabelVisible: true,
    }));
  }
}

async function loadChart() {
  stopLive();
  // Reset price levels for fresh chart load
  _priceLevelRange = 0;
  for (var pi = 0; pi < _priceLevelLines.length; pi++) {
    try { candleSeries.removePriceLine(_priceLevelLines[pi]); } catch(_) {}
  }
  _priceLevelLines = [];
  const ex = exchangeEl.value, sym = symbolEl.value, tf = timeframeEl.value;
  if (!ex || !sym) return;
  document.getElementById('loading').style.display = 'block';
  document.getElementById('empty').style.display = 'none';
  document.getElementById('emptyKey').textContent = `${ex} ${sym} ${tf}`;
  const data = await ensureDataLoaded();
  document.getElementById('loading').style.display = 'none';
  if (!data || !data.candles || data.candles.length === 0) {
    document.getElementById('empty').style.display = 'block';
    statusEl.textContent = 'no data';
    return;
  }
  document.getElementById('empty').style.display = 'none';
  var candles = data.candles.map(c => ({
    time: Math.floor(c.t / 1000),
    open: c.o, high: c.h, low: c.l, close: c.c,
  }));
  // Cap to _maxBars to prevent unbounded memory growth
  if (candles.length > _maxBars) candles = candles.slice(-_maxBars);
  candleSeries.setData(candles);
  window._candleData = candles;
  updatePriceLevels(candles);
  // Update left scale dummy to mirror the visible price range
  if (window._leftScaleDummy) {
    var lo = Infinity, hi = -Infinity;
    for (var ci = 0; ci < candles.length; ci++) {
      if (candles[ci].low < lo) lo = candles[ci].low;
      if (candles[ci].high > hi) hi = candles[ci].high;
    }
    window._leftScaleDummy.setData([
      { time: candles[0].time, value: lo },
      { time: candles[candles.length - 1].time, value: hi },
    ]);
  }
  _candleEarliestTime = candles.length > 0 ? candles[0].time * 1000 : 0;
  startLoadOlderPolling();

  // Auto-add volume indicator if not present
  if (!activeIndicators.some(function(a) { return a.name === "volume"; })) {
    var volEntry = findCatalogEntry("volume");
    if (volEntry) {
      var volParams = JSON.parse(JSON.stringify(volEntry.defaults));
      volParams.lines = {};
      activeIndicators.push({ name: "volume", label: "Volume", params: volParams, paneMode: volEntry.paneMode || "main" });
      renderIndChips();
    }
  }
  lastCandleTime = data.candles[data.candles.length - 1].t;
  chart.timeScale().fitContent();
  // Scroll to the latest candle so the right side of the chart is visible
  chart.timeScale().scrollToRealTime();
  const from = msToDate(data.candles[0].t);
  const to = msToDate(lastCandleTime);
  statusEl.textContent = `${data.count} candles  |  ${from} → ${to}`;
  toggleRegression();
  startLive();
  if (activeIndicators.length > 0) computeAndRenderIndicators();
}

async function ensureDataLoaded() {
  const ex = exchangeEl.value, sym = symbolEl.value, tf = timeframeEl.value;
  if (!ex || !sym) return null;
  const key = cacheKey();

  // 1. Check in-memory cache
  if (_cachedCandles && _cacheKey === key) return _cachedCandles;

  // 2. Check sessionStorage
  const cached = cacheGet(key);
  if (cached) {
    _cachedCandles = cached;
    _cacheKey = key;
    return cached;
  }

  // 3. Lightweight count check before full fetch
  try {
    let countUrl = `/api/candles/count?exchange=${ex}&symbol=${sym}&timeframe=${tf}`;
    if (startDateEl.value) countUrl += `&start_time=${dateToMs(startDateEl.value)}`;
    if (endDateEl.value) countUrl += `&end_time=${dateToMs(endDateEl.value) + 86400000}`;
    const countR = await fetch(countUrl);
    const countData = await countR.json();
    // If no new data and we have cached data, skip fetch
    if (cached && countData.count === (cached.count || 0)) {
      _cachedCandles = cached;
      _cacheKey = key;
      return cached;
    }
  } catch(_) {}

  // 4. Full fetch from analyze endpoint (has metrics + OHLCV)
  let url = `/analyze/data?exchange=${ex}&symbol=${sym}&timeframe=${tf}&limit=${_maxBars}`;
  if (startDateEl.value) url += `&start_time=${dateToMs(startDateEl.value)}`;
  if (endDateEl.value) url += `&end_time=${dateToMs(endDateEl.value) + 86400000}`;
  try {
    const r = await fetch(url);
    const data = await r.json();
    _cachedCandles = data;
    _cacheKey = key;
    cacheSet(key, data);
    return data;
  } catch(_) { return null; }
}

async function loadAllData() {
  // background fetch — fire and forget, any tab can use ensureDataLoaded
  ensureDataLoaded().catch(() => {});
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
  await apiFetch(5000);
  btn.disabled = false; btn.textContent = 'Update';
  loadChart();
}

async function fetchAllData() {
  stopLive();
  const btn = document.getElementById('fetchAllBtn');
  btn.disabled = true; btn.textContent = 'fetching...';
  await apiFetch(99999, null, null);
  btn.disabled = false; btn.textContent = 'Fetch all';
  loadChart();
}

/* ─── Chart Family System ─── */
const CHART_FAMILIES = {
  dist: { label: 'Distribution', desc: 'What values do metrics take, and how are they spread?' },
  ts: { label: 'Time Series', desc: 'How do metrics evolve over time? Spot trends, regimes, cycles.' },
  corr: { label: 'Correlation', desc: 'Which metrics move together? Find leading indicators and relationships.' },
  pctl: { label: 'Percentile', desc: 'Where does each candle rank? Identify extreme events and thresholds.' },
  pat: { label: 'Pattern', desc: 'Are there hidden structures? Volatility clusters, regimes, groupings.' },
};

const CHART_CONFIG = {
  // ── DISTRIBUTION ──
  hist: {
    label: 'Histogram', family: 'dist',
    params: [
      { id: 'metric', type: 'metric', label: 'Metric' },
      { id: 'bins', type: 'range', label: 'Bins', min: 5, max: 100, step: 5, def: 20 },
    ],
    desc: 'Bar chart of value frequency. Taller bars = more candles in that range. Use to see the typical range of a metric and spot outliers. A wide spread means high variance; a narrow peak means the metric is stable.',
  },
  box: {
    label: 'Box plot', family: 'dist',
    params: [{ id: 'metric', type: 'metric', label: 'Metric' }],
    desc: 'Shows min, Q1 (25th), median (50th), Q3 (75th), and max as a box with whiskers. Dots = outliers >1.5×IQR. Use to compare distribution shape and detect skewness or extreme values at a glance.',
  },
  cdf: {
    label: 'CDF', family: 'dist',
    params: [{ id: 'metric', type: 'metric', label: 'Metric' }],
    desc: 'Cumulative Distribution Function: for any value X on the x-axis, the y-axis shows what % of candles have a metric value ≤ X. Use: "95% of candles have OC% < 1% → a 1% move is a 95th-percentile event."',
  },
  qq: {
    label: 'QQ-plot', family: 'dist',
    params: [{ id: 'metric', type: 'metric', label: 'Metric' }],
    desc: 'Plots your metric quantiles against theoretical normal quantiles. If the points follow the diagonal line, your metric is roughly normal. Deviations at the ends = fat tails (more extreme events than normal).',
  },
  kde: {
    label: 'KDE', family: 'dist',
    params: [
      { id: 'metric', type: 'metric', label: 'Metric' },
      { id: 'bw', type: 'range', label: 'Bandwidth', min: 0.1, max: 5, step: 0.1, def: 0.5 },
    ],
    desc: 'Kernel Density Estimation: a smooth curve approximating the probability density of the metric. Smoother than a histogram. Use to understand the underlying distribution shape without binning artifacts.',
  },
  violin: {
    label: 'Violin plot', family: 'dist',
    params: [{ id: 'metric', type: 'metric', label: 'Metric' }],
    desc: 'Mirrored KDE drawn vertically, one per metric. Shows the full distribution shape — thicker sections mean more candles at that value. Use to compare distribution shapes, skewness, and multimodality across metrics.',
  },
  // ── TIME SERIES ──
  line: {
    label: 'Metric line', family: 'ts',
    params: [
      { id: 'metric', type: 'metric', label: 'Metric' },
      { id: 'smooth', type: 'range', label: 'Smoothing', min: 1, max: 50, step: 1, def: 1 },
    ],
    desc: 'Metric value plotted against candle time. Each point = one candle. Use to see how a metric evolves: regime changes, trends, volatility shifts. Smoothing averages adjacent candles for a cleaner view.',
  },
  rolling: {
    label: 'Rolling stats', family: 'ts',
    params: [
      { id: 'metric', type: 'metric', label: 'Metric' },
      { id: 'rwindow', type: 'range', label: 'Window', min: 3, max: 200, step: 1, def: 20 },
      { id: 'rstat', type: 'select', label: 'Stat', options: ['mean', 'std', 'skew'], def: 'mean' },
    ],
    desc: 'Rolling mean (μ) or standard deviation (σ) over a sliding window. Use: rising rolling mean = bullish trend; rising rolling σ = volatility expansion, often precedes a breakout.',
  },
  bollinger: {
    label: 'Bollinger bands', family: 'ts',
    params: [
      { id: 'metric', type: 'metric', label: 'Metric' },
      { id: 'bwindow', type: 'range', label: 'Window', min: 5, max: 100, step: 1, def: 20 },
      { id: 'bk', type: 'range', label: 'K (std)', min: 1, max: 4, step: 0.5, def: 2 },
    ],
    desc: 'Rolling mean ± K×rolling std as shaded bands. When the metric touches the upper/lower band, it may signal overextension and a mean-reversion opportunity. Band squeeze = low volatility, often precedes expansion.',
  },
  hourbb: {
    label: 'Bull/Bear by hour', family: 'ts',
    params: [{ id: 'metric', type: 'metric', label: 'Metric', hide: true }],
    desc: 'Bar chart of bull vs bear candle count for each hour of the day (UTC). Use to find hours with a directional bias. E.g., "Hour 14-16 have 60% bull candles → avoid shorts during this window."',
  },
  weekpat: {
    label: 'Week pattern', family: 'ts',
    params: [{ id: 'metric', type: 'metric', label: 'Metric' }],
    desc: 'Heatmap of average metric value by hour of day (x) × day of week (y). Use to find recurring temporal patterns. E.g., "Wednesdays at 15:00 have consistently high Vol% → liquidity events."',
  },
  // ── CORRELATION ──
  scatter: {
    label: 'Scatter + regression', family: 'corr',
    params: [
      { id: 'sx', type: 'metric', label: 'X metric' },
      { id: 'sy', type: 'metric', label: 'Y metric' },
    ],
    desc: 'Each candle = one dot (x=X metric, y=Y metric). The line is linear regression (best fit). r = Pearson correlation coefficient (-1 to 1). Use to see if two metrics are related. r near 0 = no linear relationship; r > 0.5 or < -0.5 = meaningful link.',
  },
  heatmap: {
    label: 'Correlation heatmap', family: 'corr',
    params: [{ id: 'metric', type: 'metric', label: 'Metric', hide: true }],
    desc: 'Color matrix showing Pearson correlation between every pair of metrics. Green = positive (move together), red = negative (move opposite), intensity = strength. Use to quickly find which metrics are redundant or inversely related.',
  },
  autocorr: {
    label: 'Autocorrelation', family: 'corr',
    params: [
      { id: 'metric', type: 'metric', label: 'Metric' },
      { id: 'maxlag', type: 'range', label: 'Max lag', min: 1, max: 100, step: 1, def: 20 },
    ],
    desc: 'Correlation of a metric with itself at different time lags. Lag 1 = correlation with the previous candle, lag 2 = 2 candles ago, etc. Use to detect momentum (positive at lag 1), mean reversion (negative at lag 1), or cycles (peaks at regular intervals).',
  },
  xcorr: {
    label: 'Cross-correlation', family: 'corr',
    params: [
      { id: 'xca', type: 'metric', label: 'Metric A' },
      { id: 'xcb', type: 'metric', label: 'Metric B' },
      { id: 'xclag', type: 'range', label: 'Max lag', min: 1, max: 50, step: 1, def: 10 },
    ],
    desc: 'Correlation between two metrics at different time lags. Positive lag = Metric A leads Metric B. Use to find leading indicators. E.g., "Vol% at lag -2 correlates with OC% at lag 0 → high volume predicts a move 2 bars ahead."',
  },
  splom: {
    label: 'Pair plot (SPLOM)', family: 'corr',
    params: [{ id: 'metric', type: 'metric', label: 'Metric', hide: true }],
    desc: 'Scatter plot matrix: each pair of metrics gets its own scatter plot. Use to scan all pairwise relationships at once. Look for non-linear patterns that Pearson correlation misses.',
  },
  // ── PERCENTILE ──
  pctlcurve: {
    label: 'Percentile curve', family: 'pctl',
    params: [{ id: 'metric', type: 'metric', label: 'Metric' }],
    desc: 'Inverse CDF: for each metric value (x), shows the percentile rank (y). Steep sections = many candles cluster in that range. Flat sections = rare values. Use to set thresholds: "A 2% OC% is the 97th percentile → extreme."',
  },
  rankcorr: {
    label: 'Rank corridor', family: 'pctl',
    params: [{ id: 'metric', type: 'metric', label: 'Metric' }],
    desc: 'Each candleʼs percentile rank plotted over time. Moving from 50th to 90th percentile = building momentum. Breaking above/below the shaded 10-90% corridor = anomalous behavior, potential reversal.',
  },
  fanchart: {
    label: 'Fan chart', family: 'pctl',
    params: [{ id: 'metric', type: 'metric', label: 'Metric' }],
    desc: 'Shaded percentile bands (10/25/50/75/90) over time. The 50% band (median) is the center line. Wider bands = more uncertainty/variance. When the metric breaks out of the 90% band, it may be a regime change.',
  },
  pctltable: {
    label: 'Percentile table', family: 'pctl',
    params: [{ id: 'metric', type: 'metric', label: 'Metric' }],
    desc: 'Tabular view of the percentile distribution: buckets (0-10%, 10-20%, …, 90-100%) with the value range and candle count for each. Use for precise quantitative reference.',
  },
  // ── PATTERN ──
  volcluster: {
    label: 'Volatility clustering', family: 'pat',
    params: [
      { id: 'metric', type: 'metric', label: 'Metric' },
      { id: 'vw', type: 'range', label: 'Window', min: 5, max: 100, step: 1, def: 20 },
    ],
    desc: 'Rolling standard deviation over time, colored by magnitude. High volatility tends to cluster (periods of high vol follow high vol). Use to identify calm vs turbulent regimes and avoid trading during high vol.',
  },
  regimehist: {
    label: 'Regime histogram', family: 'pat',
    params: [{ id: 'metric', type: 'metric', label: 'Metric' }],
    desc: 'Two overlaid histograms: bull candles (green) vs bear candles (red). Use to see if bull/bear distributions differ. E.g., "Bull OC% averages +0.15% while bear averages -0.18% → asymmetry favors bulls."',
  },
  clusterscatter: {
    label: 'Cluster scatter', family: 'pat',
    params: [
      { id: 'cxa', type: 'metric', label: 'X metric' },
      { id: 'cyb', type: 'metric', label: 'Y metric' },
      { id: 'ck', type: 'range', label: 'Clusters (k)', min: 2, max: 8, step: 1, def: 3 },
    ],
    desc: 'k-means clustering on the selected X,Y metrics. Each color = one cluster/regime. Use to discover natural market regimes. E.g., 3 clusters may reveal: low-vol sideways, high-vol bull, high-vol bear.',
  },
};

/* ─── SessionStorage-backed cache ─── */
const CACHE_PREFIX = 'ca_cache_';
function cacheKey() {
  return `${exchangeEl.value}/${symbolEl.value}/${timeframeEl.value}/${startDateEl.value}/${endDateEl.value}`;
}
function cacheGet(key) {
  try {
    const raw = sessionStorage.getItem(CACHE_PREFIX + key);
    return raw ? JSON.parse(raw) : null;
  } catch(_) { return null; }
}
function cacheSet(key, data) {
  try { sessionStorage.setItem(CACHE_PREFIX + key, JSON.stringify(data)); } catch(_) {}
}
function cacheRemove(key) {
  try { sessionStorage.removeItem(CACHE_PREFIX + key); } catch(_) {}
}
function invalidateCache() {
  const key = cacheKey();
  cacheRemove(key);
} 
let _cachedCandles = null;
let _cacheKey = '';

/* ─── INFO ARRAY state ─── */
let _thresholds = [1, 2, 3, 5, 10];
let _maxBars = (loadChartSettings().maxBars) || 5000;
let _metricOrder = [];

function getActiveToggles(prefix) {
  return Array.from(document.querySelectorAll(`.mtog[data-${prefix}] input:checked`))
    .map(cb => cb.closest('.mtog').dataset[prefix]);
}

/* ─── Family / chart switching ─── */
function switchFamily(fam) {
  document.querySelectorAll('.fam-tab').forEach(t => t.classList.toggle('active', t.dataset.fam === fam));
  const sel = document.getElementById('chartType');
  const types = Object.entries(CHART_CONFIG).filter(([k, v]) => v.family === fam);
  sel.innerHTML = types.map(([k, v]) => `<option value="${k}">${v.label}</option>`).join('');
  sel.value = types[0]?.[0] || '';
  updateChartParams();
  renderViz();
}

function updateChartParams() {
  const type = document.getElementById('chartType').value;
  const cfg = CHART_CONFIG[type];
  if (!cfg) return;
  const container = document.getElementById('chartParams');
  const info = document.getElementById('chartInfo');
  let html = '';
  for (const p of cfg.params) {
    if (p.hide) continue;
    if (p.type === 'metric') {
      const active = getActiveToggles('m');
      html += `<span style="color:#888;font-size:10px">${p.label}</span>`;
      html += `<select id="cp_${p.id}" style="background:#0f3460;color:#e0e0e0;border:1px solid #1a3a6b;padding:2px 6px;border-radius:3px;font-size:10px">`;
      for (const m of METRICS_ORDER) {
        const sel = m === (active[0] || 'oc') ? ' selected' : '';
        html += `<option value="${m}"${sel}>${METRICS[m].label}</option>`;
      }
      html += `</select>`;
    } else if (p.type === 'range') {
      const d = p.def ?? 20;
      html += `<span style="color:#888;font-size:10px">${p.label}</span>`;
      html += `<input type="range" id="cp_${p.id}" min="${p.min}" max="${p.max}" step="${p.step||1}" value="${d}" style="width:60px;accent-color:#e94560">`;
      html += `<span id="cp_${p.id}_v" style="color:#888;font-size:10px;min-width:20px">${d}</span>`;
    } else if (p.type === 'select') {
      html += `<span style="color:#888;font-size:10px">${p.label}</span>`;
      html += `<select id="cp_${p.id}" style="background:#0f3460;color:#e0e0e0;border:1px solid #1a3a6b;padding:2px 6px;border-radius:3px;font-size:10px">`;
      for (const o of p.options) {
        html += `<option value="${o}"${o===p.def?' selected':''}>${o}</option>`;
      }
      html += `</select>`;
    }
  }
  container.innerHTML = html;
  // range display
  for (const p of cfg.params) {
    if (p.type === 'range') {
      const el = document.getElementById(`cp_${p.id}`);
      if (el) el.addEventListener('input', () => {
        const v = document.getElementById(`cp_${p.id}_v`);
        if (v) v.textContent = el.value;
      });
    }
  }
  // info tooltip
  info.style.display = 'inline';
  info.title = cfg.desc || '';
}

/* ─── loadAnalyze with cache ─── */
async function loadAnalyze() {
  const ex = exchangeEl.value, sym = symbolEl.value, tf = timeframeEl.value;
  if (!ex || !sym) return;
  document.getElementById('astatus').textContent = 'loading...';
  const allData = await ensureDataLoaded() || _cachedCandles;
  if (!allData) { document.getElementById('astatus').textContent = 'no data'; return; }

  // read MAX LAST BAR
  const maxBarsEl = document.getElementById('maxBars');
  _maxBars = parseInt(maxBarsEl?.value) || 5000;

  const totalCount = allData.candles.length;
  const workingCount = Math.min(_maxBars, totalCount);
  const candles = allData.candles.slice(-workingCount);

  let activeMetrics = getActiveToggles('m');
  document.getElementById('astatus').textContent = `${workingCount} of ${totalCount} candles`;

  // compute per-candle percentiles locally for working set
  const localPctls = {};
  for (const m of activeMetrics) {
    const vals = candles.map(c => c.metrics[m]);
    const sorted = [...vals].sort((a, b) => a - b);
    const n = sorted.length;
    localPctls[m] = vals.map(v => sorted.filter(x => x < v).length / n * 100);
  }
  for (let i = 0; i < candles.length; i++) {
    candles[i].percentiles = candles[i].percentiles || {};
    for (const m of activeMetrics) {
      candles[i].percentiles[m] = localPctls[m][i];
    }
  }

  // init metric order — keep existing order, add new metrics, remove unchecked
  _metricOrder = _metricOrder.filter(m => activeMetrics.includes(m));
  for (const m of activeMetrics) {
    if (!_metricOrder.includes(m)) _metricOrder.push(m);
  }
  if (_metricOrder.length === 0) _metricOrder = [...activeMetrics];

  // render INFO ARRAY
  renderInfoArray(candles, activeMetrics);

  // store data for chart rendering
  window._analyzeData = { count: workingCount, candles };
  window._activeMetrics = activeMetrics;
  renderAllCharts();
}

/* ─── INFO ARRAY rendering ─── */
function renderInfoArray(candles, activeMetrics) {
  const container = document.getElementById('infoArray');
  const maxThresh = 5;
  while (_thresholds.length > maxThresh) _thresholds.pop();
  if (_thresholds.length === 0) _thresholds.push(1);
  const threshSorted = [..._thresholds].sort((a, b) => a - b);

  // compute per-metric values
  const metricValsSorted = {}, metricAllVals = {};
  for (const m of activeMetrics) {
    const vals = candles.map(c => c.metrics[m]);
    metricAllVals[m] = vals;
    metricValsSorted[m] = [...vals].sort((a, b) => a - b);
  }

  // compute bucket data
  const bucketData = {};
  for (const m of activeMetrics) {
    bucketData[m] = {};
    const vals = metricAllVals[m], sorted = metricValsSorted[m], n = vals.length;
    for (const t of threshSorted) {
      const cutoffIdx = Math.floor(n * (1 - t / 100));
      const cutoffVal = sorted[Math.min(cutoffIdx, n - 1)];
      const bucket = [], bucketIdx = [];
      for (let i = 0; i < n; i++) {
        if (vals[i] >= cutoffVal) { bucket.push(vals[i]); bucketIdx.push(i); }
      }
      if (bucket.length === 0) {
        bucketData[m][t] = { bull:0, bear:0, min:0, med:0, max:0, mean:0, size:0, concurrence:{} };
        continue;
      }
      const bSorted = [...bucket].sort((a,b)=>a-b), bSize = bucket.length;
      const bMean = bucket.reduce((s,v)=>s+v,0)/bSize;
      const bMed = bSize%2===0 ? (bSorted[bSize/2-1]+bSorted[bSize/2])/2 : bSorted[Math.floor(bSize/2)];
      let bBull=0, bBear=0;
      for (const idx of bucketIdx) { if (candles[idx].c >= candles[idx].o) bBull++; else bBear++; }
      const concurrence = {};
      for (const other of activeMetrics) {
        if (other === m) continue;
        const otherCutoff = metricValsSorted[other][Math.min(Math.floor(n*(1-t/100)), n-1)];
        let both = 0;
        for (const idx of bucketIdx) { if (metricAllVals[other][idx] >= otherCutoff) both++; }
        concurrence[other] = bSize > 0 ? both/bSize*100 : 0;
      }
      bucketData[m][t] = { bull:bBull, bear:bBear, min:bSorted[0], med:bMed, max:bSorted[bSize-1], mean:bMean, size:bSize, concurrence };
    }
  }

  const sym = symbolEl.value, tf = timeframeEl.value;
  const title = `${sym} ${tf} — Statistiques par Percentile — ${candles.length} barres`;
  let html = `<div style="font-size:12px;color:#888;margin-bottom:4px;padding:4px 0;border-bottom:1px solid #16213e">${title}</div>`;
  html += '<table class="ia-wrap">';

  const subCols = 3;
  const totalCols = 1 + _metricOrder.length * subCols;

  // Color class map
  const bgClass = { oh:'ia-bg-oh', ol:'ia-bg-ol', hc:'ia-bg-hc', lc:'ia-bg-lc', hl:'ia-bg-hl', oc:'ia-bg-oc', vol:'ia-bg-vol' };

  // Level 1 header: metrics with ◀▶ and colors
  html += `<tr><th rowspan="2" class="ia-th-seuil">Seuil</th>`;
  for (let mi = 0; mi < _metricOrder.length; mi++) {
    const m = _metricOrder[mi];
    const leftBtn = mi > 0 ? `<span class="ia-mv" onclick="moveMetric(${mi},-1)">◀</span>` : '<span style="display:inline-block;width:13px"></span>';
    const rightBtn = mi < _metricOrder.length-1 ? `<span class="ia-mv" onclick="moveMetric(${mi},1)">▶</span>` : '<span style="display:inline-block;width:13px"></span>';
    html += `<th colspan="${subCols}" class="${bgClass[m]||''}" style="color:#e94560">${leftBtn} ${METRICS[m].label} ${rightBtn}</th>`;
  }
  html += '</tr>';

  // Level 2 header
  html += '<tr>';
  for (const m of _metricOrder) {
    html += `<th class="${bgClass[m]||''} ia-th-bb">B/B</th><th class="${bgClass[m]||''} ia-th-stats">Min·Méd·Max<br>Moy.</th><th class="${bgClass[m]||''} ia-th-concu">Concu</th>`;
  }
  html += '</tr>';

  // Body rows
  for (const t of threshSorted) {
    const thIdx = _thresholds.indexOf(t);
    html += `<tr><td style="text-align:left;padding:4px 6px;white-space:nowrap">
      TOP&nbsp;<span class="ia-edit" contenteditable="true" onblur="editThreshold(${thIdx},this)" title="Modifier">${t}</span>%
      <span class="ia-del" onclick="removeThreshold(${thIdx})" style="margin-left:2px">✕</span>
    </td>`;
    for (const m of _metricOrder) {
      const bd = bucketData[m][t];
      if (!bd || bd.size === 0) {
        html += `<td colspan="${subCols}" class="${bgClass[m]||''}" style="color:#555">—</td>`;
        continue;
      }
      const total = bd.bull + bd.bear;
      const bPct = total > 0 ? (bd.bull/total*100).toFixed(1) : '0';
      const bPctB = total > 0 ? (bd.bear/total*100).toFixed(1) : '0';
      const gPct = (bd.size/candles.length*100).toFixed(1);
      const bbHtml = `<span class="ia-bull">${bPct}%</span>/<span class="ia-bear">${bPctB}%</span><br><span style="font-size:9px;color:#555">${gPct}% global</span>`;
      const pctlHtml = `<span class="num">${bd.min.toFixed(2)}</span> · <span class="num">${bd.med.toFixed(2)}</span> · <span class="num">${bd.max.toFixed(2)}</span><br><span class="num" style="color:#888">${bd.mean.toFixed(2)}</span>`;
      const corrEntries = Object.entries(bd.concurrence).sort((a,b)=>b[1]-a[1]);
      const corrHtml = corrEntries.map(([k,v])=>`${METRICS[k]?.label||k}:<span class="num">${v.toFixed(0)}%</span>`).join('<br>') || '<span style="color:#555">—</span>';
      html += `<td class="${bgClass[m]||''}">${bbHtml}</td><td class="${bgClass[m]||''}">${pctlHtml}</td><td class="${bgClass[m]||''} ia-corr">${corrHtml}</td>`;
    }
    html += '</tr>';
  }

  // Add row
  html += `<tr><td style="text-align:center"><span class="ia-add" onclick="addThreshold()">+ Ajouter seuil</span></td>`;
  html += `<td colspan="${totalCols-1}" style="color:#555;font-size:10px">Max 5 seuils</td></tr>`;
  html += '</table>';
  container.innerHTML = html;
  document.getElementById('iaStatus').innerHTML = `Seuils: ${threshSorted.map(t=>`TOP ${t}%`).join(' · ')} — Max ${maxThresh} seuils`;
}

function moveMetric(idx, dir) {
  const newIdx = idx + dir;
  if (newIdx < 0 || newIdx >= _metricOrder.length) return;
  [_metricOrder[idx], _metricOrder[newIdx]] = [_metricOrder[newIdx], _metricOrder[idx]];
  reRenderAnalyze();
}

/* ─── Threshold management ─── */
function addThreshold() {
  const val = prompt('Nouveau seuil (ex: 2.5) :', '5');
  if (val === null) return;
  const num = parseFloat(val);
  if (isNaN(num) || num <= 0 || num >= 100) { alert('Invalide (0-100)'); return; }
  if (_thresholds.length >= 5) { alert('Max 5 seuils'); return; }
  _thresholds.push(num);
  reRenderAnalyze();
}
function removeThreshold(idx) {
  if (_thresholds.length <= 1) return;
  _thresholds.splice(idx, 1);
  reRenderAnalyze();
}
function editThreshold(idx, span) {
  const num = parseFloat(span.textContent.trim());
  if (isNaN(num) || num <= 0 || num >= 100) { span.textContent = _thresholds[idx]; return; }
  _thresholds[idx] = num;
  reRenderAnalyze();
}
function reRenderAnalyze() {
  const candles = window._analyzeData?.candles;
  if (!candles) return;
  renderInfoArray(candles, window._activeMetrics || getActiveToggles('m'));
}

/* ─── Stacked charts ─── */
const OVERLAY_COLORS = ['#e94560','#26a69a','#42a5f5','#ab47bc','#ffa726','#ef5350','#66bb6a'];
const _chartInstances = {};

const CHART_TYPES = {
  dist: [
    { id:'hist', label:'Histogramme', render: renderHistogram },
    { id:'box', label:'Boîte', render: renderBoxPlot },
    { id:'cdf', label:'CDF', render: renderCDF },
    { id:'qq', label:'QQ Plot', render: renderQQ },
    { id:'kde', label:'KDE', render: renderKDE },
    { id:'violin', label:'Violin', render: renderViolin },
  ],
  ts: [
    { id:'line', label:'Ligne', render: renderMetricLine },
    { id:'rolling', label:'Moy. mobile', render: renderRolling },
    { id:'bollinger', label:'Bollinger', render: renderBollinger },
  ],
  corr: [
    { id:'heatmap', label:'Heatmap', render: renderHeatmap },
    { id:'scatter', label:'Nuage', render: renderScatter },
    { id:'autocorr', label:'Autocorrélation', render: renderAutoCorr },
    { id:'xcorr', label:'Cross-corr.', render: renderXCorr },
    { id:'splom', label:'SPLOM', render: renderSPLOM },
  ],
  pctl: [
    { id:'pctlcurve', label:'Courbe', render: renderPctlCurve },
    { id:'fan', label:'Fan chart', render: renderFanChart },
    { id:'rankcorridor', label:'Couloir rang', render: renderRankCorridor },
    { id:'pctltable', label:'Tableau', render: renderPctlTable },
  ],
  pat: [
    { id:'volcluster', label:'Volatilité', render: renderVolCluster },
    { id:'weekpattern', label:'Semaine', render: renderWeekPattern },
    { id:'regimehist', label:'Régimes', render: renderRegimeHist },
  ],
  overlay: [
    { id:'overlay', label:'Comparaison', render: renderOverlay },
  ],
};

function getFamMetrics(famId, activeMetrics) {
  const cbs = document.querySelectorAll(`.fam_ck[data-fam="${famId}"]:checked`);
  const checked = Array.from(cbs).map(cb => cb.value);
  return checked.length > 0 ? checked.filter(m => activeMetrics.includes(m)) : activeMetrics.slice(0, 1);
}

function renderAllCharts() {
  const data = window._analyzeData, activeMetrics = window._activeMetrics;
  if (!data || !activeMetrics || activeMetrics.length === 0) return;
  const stack = document.getElementById('chart-stack');
  const families = [
    { id:'dist', label:'Distribution' },
    { id:'ts', label:'Time Series' },
    { id:'corr', label:'Correlation' },
    { id:'pctl', label:'Percentile' },
    { id:'pat', label:'Pattern' },
    { id:'overlay', label:'Overlay' },
  ];

  let html = '';
  const canvasIds = [];
  for (const fam of families) {
    const cid = `cb_${fam.id}`;
    canvasIds.push(cid);
    html += `<div class="chart-block" id="${cid}-block">
      <div class="cb-title">${fam.label}
        <button class="cb-reset" onclick="resetChart('${fam.id}')" title="Réinitialiser le zoom">⟲</button>
      </div>
      <div class="cb-params" id="${cid}-params"></div>
      <canvas id="${cid}"></canvas>
    </div>`;
  }
  stack.innerHTML = html;

  // Destroy old instances
  for (const key of Object.keys(_chartInstances)) {
    try { _chartInstances[key].destroy(); } catch(_) {}
  }
  for (const key of Object.keys(_chartInstances)) delete _chartInstances[key];

  // Render each chart
  for (const fam of families) {
    renderOneChart(fam, data, activeMetrics);
  }
}

function renderOneChart(fam, data, activeMetrics) {
  const cid = `cb_${fam.id}`;
  const canvas = document.getElementById(cid);
  if (!canvas) return;

  // Build params FIRST so DOM elements exist
  const paramsEl = document.getElementById(`${cid}-params`);
  if (paramsEl) buildChartParams(fam, paramsEl, data, activeMetrics);

  // Read chart type from DOM
  const typeEl = document.getElementById(`cp_${fam.id}_type`);
  const chartType = typeEl ? typeEl.value : (CHART_TYPES[fam.id]?.[0]?.id || '');

  const ctx = canvas.getContext('2d');
  canvas.style.width = '100%'; canvas.style.height = '';
  canvas.width = Math.max(canvas.offsetWidth || 600, 300);
  canvas.height = Math.max(canvas.offsetHeight || 160, 160);

  try { if (_chartInstances[fam.id]) { _chartInstances[fam.id].destroy(); } } catch(_) {}

  // family-scoped param reader
  const getFamParam = (id) => {
    const el = document.getElementById(`cp_${fam.id}_${id}`);
    return el ? (el.type === 'checkbox' ? el.checked : el.value) : null;
  };

  // Dispatch by chart type
  const found = CHART_TYPES[fam.id]?.find(t => t.id === chartType);
  if (found && found.render) {
    found.render(ctx, canvas, data, activeMetrics, getFamParam, fam.id);
  }
}


/* ─── Render heatmap static ─── */
function renderHeatmapStatic(ctx, canvas, data, activeMetrics, fam) {
  // Reuse existing renderHeatmap
  renderHeatmap(ctx, canvas, data, activeMetrics);
}

/* ─── Overlay chart: multiple metrics on one canvas ─── */
function renderOverlay(ctx, canvas, data, activeMetrics, fam) {
  const selected = window._overlayMetrics || activeMetrics;
  if (selected.length === 0) return;
  const smooth = parseInt(document.getElementById('cp_overlay_smooth')?.value) || 1;
  const normalize = document.getElementById('cp_overlay_norm')?.checked || false;

  const datasets = [];
  for (let i = 0; i < selected.length; i++) {
    const m = selected[i];
    let vals = data.candles.map(c => ({ x: c.t, y: c.metrics[m] }));
    if (smooth > 1) {
      for (let j = smooth; j < vals.length; j++) {
        let s = 0;
        for (let k = 0; k < smooth; k++) s += vals[j - k].y;
        vals[j].y = s / smooth;
      }
    }
    if (normalize) {
      const base = vals[0]?.y || 0;
      vals = vals.map(v => ({ x: v.x, y: base !== 0 ? (v.y - base) / Math.abs(base) * 100 : v.y }));
    }
    datasets.push({
      label: METRICS[m]?.label || m,
      data: vals, showLine: true,
      borderColor: OVERLAY_COLORS[i % OVERLAY_COLORS.length],
      backgroundColor: OVERLAY_COLORS[i % OVERLAY_COLORS.length] + '22',
      pointRadius: 0, borderWidth: 1.5, fill: false,
    });
  }

  _chartInstances.overlay = _chart(ctx, {
    type: 'scatter',
    data: { datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        title: { display: true, text: `Comparaison: ${selected.map(m=>METRICS[m]?.label||m).join(', ')}${normalize?' (normalisé)':''}`, color: '#888', font: { size: 11 } },
        legend: { labels: { color: '#888', font: { size: 9 } } },
      },
      scales: {
        x: { type:'linear', ticks: { callback: v=>new Date(v).toLocaleDateString('fr-FR',{timeZone:'Europe/Paris',day:'2-digit',month:'short'}), maxTicksLimit:8, color:'#888', font:{size:9} }, grid: { color:'#16213e' } },
        y: { ticks: { color:'#888', font:{size:9} }, grid: { color:'#16213e' } },
      },
    },
  });
}

function resetChart(famId) {
  try { if (_chartInstances[famId]) _chartInstances[famId].resetZoom(); } catch(_) {}
}

function buildChartParams(fam, container, data, activeMetrics) {
  const p = id => `cp_${fam.id}_${id}`;
  const types = CHART_TYPES[fam.id] || [];
  const curType = document.getElementById(p('type'))?.value || types[0]?.id || '';
  const allOn = document.getElementById(p('all'))?.checked || false;

  // chart type dropdown + metric checkboxes (shared across families)
  let html = `<label>Type <select id="${p('type')}" onchange="paramChanged()">${types.map(t => `<option value="${t.id}"${t.id===curType?' selected':''}>${t.label}</option>`).join('')}</select></label>`;
  html += `<span class="sep"></span><span style="color:#888;font-size:10px">Met:</span>`;
  for (const m of activeMetrics) {
    const checked = allOn || !document.getElementById(p('m_'+m)) || document.getElementById(p('m_'+m))?.checked;
    html += `<label style="color:#888;font-size:10px"><input type="checkbox" class="fam_ck" data-fam="${fam.id}" id="${p('m_'+m)}" value="${m}" onchange="paramChanged()" ${checked?'checked':''}> ${METRICS[m].label}</label>`;
  }
  html += `<label style="color:#888;font-size:10px;margin-left:4px"><input type="checkbox" id="${p('all')}" onchange="paramChanged()"> Ttes</label>`;

  // family-specific params
  if (fam.id === 'dist') {
    const v = document.getElementById(p('bins'))?.value || 20;
    html += `<span class="sep"></span><label>Bins <input type="range" id="${p('bins')}" min="5" max="100" step="5" value="${v}" oninput="paramChanged()"> <span>${v}</span></label>`;
  } else if (fam.id === 'ts') {
    const v = document.getElementById(p('smooth'))?.value || 1;
    html += `<span class="sep"></span><label>Smooth <input type="range" id="${p('smooth')}" min="1" max="50" step="1" value="${v}" oninput="paramChanged()"> <span>${v}</span></label>`;
  } else if (fam.id === 'pat') {
    const v = document.getElementById(p('vw'))?.value || 20;
    html += `<span class="sep"></span><label>Window <input type="range" id="${p('vw')}" min="5" max="100" step="1" value="${v}" oninput="paramChanged()"> <span>${v}</span></label>`;
  } else if (fam.id === 'overlay') {
    const sv = document.getElementById(p('smooth'))?.value || 1;
    html += `<span class="sep"></span><label>Smooth <input type="range" id="${p('smooth')}" min="1" max="50" step="1" value="${sv}" oninput="overlayChanged()"> <span>${sv}</span></label>
      <label><input type="checkbox" id="${p('norm')}" onchange="overlayChanged()"> Normaliser</label>`;
  } else if (fam.id === 'corr') {
    // no extra params
  } else if (fam.id === 'pctl') {
    const sv = document.getElementById(p('smooth'))?.value || 1;
    html += `<span class="sep"></span><label>Smooth <input type="range" id="${p('smooth')}" min="1" max="50" step="1" value="${sv}" oninput="paramChanged()"> <span>${sv}</span></label>`;
  }
  container.innerHTML = html;
}

function paramChanged() {
  renderAllCharts();
}

function overlayChanged() {
  const cbs = document.querySelectorAll('.fam_ck[data-fam="overlay"]:checked');
  window._overlayMetrics = Array.from(cbs).map(cb => cb.value);
  renderAllCharts();
}

/* ─── loadRawData ─── */
async function loadRawData() {
  const ex = exchangeEl.value, sym = symbolEl.value, tf = timeframeEl.value;
  if (!ex || !sym) return;
  document.getElementById('astatus-r').textContent = 'loading...';
  const d = await ensureDataLoaded();
  if (!d) { document.getElementById('astatus-r').textContent = 'no data'; return; }
  resetRawPage();
  renderRawTable(d);
}

/* ─── RAW DATA pagination ─── */
let _rawPageSize = 100;
function renderRawTable(data) {
  const activeMetrics = getActiveToggles('m');
  let candles = data.candles;
  document.getElementById('astatus-r').textContent = `${candles.length} candles`;

  // ensure percentiles are initialized for every candle
  for (const c of candles) {
    c.percentiles = c.percentiles || {};
    for (const m of activeMetrics) {
      if (c.percentiles[m] == null) c.percentiles[m] = 0;
    }
  }

  let sorted = [...candles];
  const metricCount = activeMetrics.length;
  const getSortVal = (c, col) => {
    if (col === 0) return c.t;
    if (col === 1) return c.c - c.o;
    if (col === 2) return c.o; if (col === 3) return c.c;
    if (col === 4) return c.h; if (col === 5) return c.l; if (col === 6) return c.v;
    const mIdx = Math.floor((col-7)/2);
    if (mIdx >= 0 && mIdx < metricCount) { const k = activeMetrics[mIdx]; return (col-7)%2===0 ? c.metrics[k] : c.percentiles[k]; }
    return 0;
  };
  if (sorted.length > 0) sorted.sort((a,b)=>{ const va=getSortVal(a,sortCol), vb=getSortVal(b,sortCol); return (va-vb)*sortDir; });

  const hasColFilters = Object.keys(_colFilters).length > 0;
  if (hasColFilters) sorted = sorted.filter(c => applyColumnFilters(c));

  window._rawSortedCandles = sorted;
  window._rawActiveMetrics = activeMetrics;
  renderRawPage();
}

function renderRawPage() {
  const sorted = window._rawSortedCandles || [];
  const activeMetrics = window._rawActiveMetrics || getActiveToggles('m');
  const total = sorted.length;
  const show = Math.min(_rawPageSize, total);

  // Render header
  let colIdx = 0;
  let headerRow = '<tr>';
  const colNames = ['Date','Dir','Open','Close','H','L','Vol'];
  for (let i = 0; i < colNames.length; i++) {
    const ci = colIdx++;
    const active = _colFilters[ci] ? ' active' : '';
    const sep = i === 0 ? ' class="col-sep-ts"' : '';
    headerRow += `<th${sep}><span onclick="sortRawTable(${ci})">${colNames[i]}</span><span class="cf-icon${active}" onclick="event.stopPropagation();toggleFilter(${ci},this)">▾</span></th>`;
  }
  for (const m of activeMetrics) {
    const ci = colIdx, a1 = _colFilters[ci] ? ' active' : '';
    headerRow += `<th class="col-sep-metric"><span onclick="sortRawTable(${colIdx})">${METRICS[m].label}</span><span class="cf-icon${a1}" onclick="event.stopPropagation();toggleFilter(${colIdx},this)">▾</span></th>`;
    colIdx++;
    headerRow += `<th class="col-sep-pctl"><span onclick="sortRawTable(${colIdx})">Pctl</span></th>`;
    colIdx++;
  }
  headerRow += '</tr>';
  document.getElementById('atheed').innerHTML = headerRow;

  // Render visible rows
  const visible = sorted.slice(0, show);
  document.getElementById('atbody').innerHTML = visible.map(c => {
    const dir = c.c >= c.o ? '<span class="bull">▲</span>' : '<span class="bear">▼</span>';
    let row = `<tr><td class="num col-sep-ts">${msToDateTime(c.t)}</td><td>${dir}</td><td class="num">${c.o.toFixed(2)}</td><td class="num">${c.c.toFixed(2)}</td><td class="num">${c.h.toFixed(2)}</td><td class="num">${c.l.toFixed(2)}</td><td class="num">${c.v.toFixed(2)}</td>`;
    for (const m of activeMetrics) {
      row += `<td class="num col-sep-metric" style="color:${c.metrics[m]>=0?'#26a69a':'#ef5350'}">${c.metrics[m].toFixed(2)}</td><td class="num col-sep-pctl">${(c.percentiles[m]||0).toFixed(1)}%</td>`;
    }
    return row + '</tr>';
  }).join('');

  const bullCount = sorted.filter(c=>c.c>c.o).length;
  const bearCount = sorted.filter(c=>c.c<c.o).length;
  let footerText = `${show} of ${total} candles · <span class="bull">${bullCount} bull</span> / <span class="bear">${bearCount} bear</span>`;
  if (show < total) {
    footerText += ` · <a href="#" onclick="loadMoreRaw();return false" style="color:#e94560;font-size:11px">Load more (${Math.min(100, total - show)} more)</a>`;
  }
  document.getElementById('afooter').innerHTML = footerText;
}

function loadMoreRaw() {
  _rawPageSize += 100;
  renderRawPage();
}

function resetRawPage() {
  _rawPageSize = 100;
}

function getParam(id) {
  const el = document.getElementById(`cp_${id}`);
  if (!el) return null;
  return el.type === 'checkbox' ? el.checked : el.value;
}

function _chart(ctx, cfg) {
  cfg.options = cfg.options || {};
  cfg.options.plugins = cfg.options.plugins || {};
  cfg.options.plugins.zoom = JSON.parse(JSON.stringify(ZOOM_OPTS));
  const chart = new Chart(ctx, cfg);
  setTimeout(() => {
    if (chart.scales && chart.scales.x) {
      const xRange = chart.scales.x.max - chart.scales.x.min;
      const yRange = chart.scales.y ? chart.scales.y.max - chart.scales.y.min : undefined;
      chart.options.plugins.zoom.limits = {};
      chart.options.plugins.zoom.limits.x = { maxRange: xRange };
      if (yRange) chart.options.plugins.zoom.limits.y = { maxRange: yRange };
      chart.update();
    }
  }, 200);
  return chart;
}

/* ─── Column Filter System ─── */
const _colFilters = {};

function renderFilterDropdown(colIdx, iconEl) {
  // close existing dropdowns
  document.querySelectorAll('.cf-drop').forEach(d => d.remove());
  const rect = iconEl.getBoundingClientRect();
  const div = document.createElement('div');
  div.className = 'cf-drop';
  div.style.left = Math.min(rect.left, window.innerWidth - 200) + 'px';
  div.style.top = (rect.bottom + 4) + 'px';

  const colNames = ['Date', 'Dir', 'Open', 'Close', 'H', 'L', 'Vol'];
  const colLabels = ['Date', 'Direction', 'Open', 'Close', 'High', 'Low', 'Volume'];

  const fil = _colFilters[colIdx] || {};

  let html = '';

  // Sort section
  html += '<div class="cf-title">Sort</div>';
  html += `<label class="cf-act" onclick="sortTable(this,${colIdx});closeDropdown()">${sortCol === colIdx && sortDir > 0 ? '✓ ' : ''}▲ Ascending</label>`;
  html += `<label class="cf-act" onclick="sortTable(this,${colIdx});closeDropdown()">${sortCol === colIdx && sortDir < 0 ? '✓ ' : ''}▼ Descending</label>`;
  html += '<div class="cf-sep"></div>';

  if (colIdx === 0) { // Date
    html += '<div class="cf-title">Filter</div>';
    html += `<label>Search <input type="text" id="cf_search" value="${fil.search || ''}" placeholder="date..."></label>`;
    html += `<label>From <input type="date" id="cf_from" value="${fil.from || ''}"></label>`;
    html += `<label>To <input type="date" id="cf_to" value="${fil.to || ''}"></label>`;
  } else if (colIdx === 1) { // Dir
    html += '<div class="cf-title">Type</div>';
    html += `<label><input type="checkbox" id="cf_bull" ${fil.bull !== false ? 'checked' : ''}> Bull</label>`;
    html += `<label><input type="checkbox" id="cf_bear" ${fil.bear !== false ? 'checked' : ''}> Bear</label>`;
  } else if (colIdx >= 2 && colIdx <= 6) { // OHLCV
    html += '<div class="cf-title">Range</div>';
    html += `<label>Min <input type="number" id="cf_min" value="${fil.min ?? ''}" step="any"></label>`;
    html += `<label>Max <input type="number" id="cf_max" value="${fil.max ?? ''}" step="any"></label>`;
    html += `<label><input type="checkbox" id="cf_pos" ${fil.pos ? 'checked' : ''}> Positive only</label>`;
    html += `<label><input type="checkbox" id="cf_neg" ${fil.neg ? 'checked' : ''}> Negative only</label>`;
  } else { // Metric or Pctl columns
    html += '<div class="cf-title">Range</div>';
    html += `<label>Min <input type="number" id="cf_min" value="${fil.min ?? ''}" step="any"></label>`;
    html += `<label>Max <input type="number" id="cf_max" value="${fil.max ?? ''}" step="any"></label>`;
    html += `<label><input type="checkbox" id="cf_pos" ${fil.pos ? 'checked' : ''}> Positive only</input></label>`;
    html += `<label><input type="checkbox" id="cf_neg" ${fil.neg ? 'checked' : ''}> Negative only</input></label>`;
    // percentile filter for metric value columns (not pctl columns)
    if ((colIdx - 7) % 2 === 0) {
      html += `<label>Pctl above <input type="number" id="cf_pctl" value="${fil.pctl ?? ''}" min="0" max="100" step="1" style="width:50px"> %</label>`;
    }
  }

  html += '<div class="cf-sep"></div>';
  html += `<label class="cf-act" onclick="applyFilter(${colIdx})">✓ Apply</label>`;
  html += `<label class="cf-act" onclick="resetFilter(${colIdx});closeDropdown()">⟳ Reset column</label>`;
  html += `<label class="cf-act" onclick="resetAllFilters();closeDropdown()">⟳ Reset all</label>`;

  div.innerHTML = html;

  // apply button handler
  const applyBtn = div.querySelector('[onclick*="applyFilter"]');
  if (applyBtn) {
    applyBtn.onclick = (e) => {
      e.stopPropagation();
      applyFilter(colIdx);
      closeDropdown();
    };
  }

  document.body.appendChild(div);

  // position adjustment
  const dr = div.getBoundingClientRect();
  if (dr.right > window.innerWidth) div.style.left = (window.innerWidth - dr.width - 10) + 'px';
  if (dr.bottom > window.innerHeight) div.style.top = (rect.top - dr.height - 4) + 'px';
}

function closeDropdown() {
  document.querySelectorAll('.cf-drop').forEach(d => d.remove());
}

document.addEventListener('click', (e) => {
  if (!e.target.closest('.cf-drop') && !e.target.closest('.cf-icon')) closeDropdown();
});

function toggleFilter(colIdx, iconEl) {
  // if dropdown already open for this column, close it
  const existing = document.querySelector('.cf-drop');
  if (existing) { closeDropdown(); return; }
  renderFilterDropdown(colIdx, iconEl);
}

function applyFilter(colIdx) {
  const fil = {};
  const el = id => document.getElementById(id);
  if (colIdx === 0) {
    fil.search = el('cf_search')?.value || '';
    fil.from = el('cf_from')?.value || '';
    fil.to = el('cf_to')?.value || '';
  } else if (colIdx === 1) {
    fil.bull = el('cf_bull')?.checked ?? true;
    fil.bear = el('cf_bear')?.checked ?? true;
  } else {
    const min = parseFloat(el('cf_min')?.value);
    const max = parseFloat(el('cf_max')?.value);
    if (!isNaN(min)) fil.min = min;
    if (!isNaN(max)) fil.max = max;
    fil.pos = el('cf_pos')?.checked ?? false;
    fil.neg = el('cf_neg')?.checked ?? false;
    const pctl = parseFloat(el('cf_pctl')?.value);
    if (!isNaN(pctl)) fil.pctl = pctl;
  }
  if (Object.keys(fil).length > 0) _colFilters[colIdx] = fil;
  else delete _colFilters[colIdx];
  loadAnalyze();
}

function resetFilter(colIdx) {
  delete _colFilters[colIdx];
  loadAnalyze();
}

function resetAllFilters() {
  Object.keys(_colFilters).forEach(k => delete _colFilters[k]);
  loadAnalyze();
}

function applyColumnFilters(c) {
  const getVal = (col) => {
    if (col === 0) return c.t;
    if (col === 1) return c.c - c.o;
    if (col === 2) return c.o; if (col === 3) return c.c;
    if (col === 4) return c.h; if (col === 5) return c.l; if (col === 6) return c.v;
    const mIdx = Math.floor((col - 7) / 2);
    const active = window._activeMetrics || [];
    if (mIdx >= 0 && mIdx < active.length) {
      const key = active[mIdx];
      return (col - 7) % 2 === 0 ? c.metrics[key] : c.percentiles[key];
    }
    return 0;
  };
  for (const [colIdx, fil] of Object.entries(_colFilters)) {
    const col = parseInt(colIdx);
    const val = getVal(col);
    if (col === 0) {
      if (fil.search && !msToDateTime(c.t).toLowerCase().includes(fil.search.toLowerCase())) return false;
      if (fil.from && c.t < new Date(fil.from + 'T00:00:00').getTime()) return false;
      if (fil.to && c.t > new Date(fil.to + 'T23:59:59').getTime()) return false;
    } else if (col === 1) {
      if (fil.bull === false && c.c >= c.o) return false;
      if (fil.bear === false && c.c < c.o) return false;
    } else {
      if (fil.min !== undefined && val < fil.min) return false;
      if (fil.max !== undefined && val > fil.max) return false;
      if (fil.pos && val <= 0) return false;
      if (fil.neg && val >= 0) return false;
      if (fil.pctl !== undefined) {
        const sorted = [...(window._cachedCandles?.candles || []).map(x => getVal(col))].sort((a,b)=>a-b);
        const p = sorted.filter(v => v < val).length / sorted.length * 100;
        if (p < fil.pctl) return false;
      }
    }
  }
  return true;
}

const METRICS_ORDER = ['oc','oh','ol','hl','hc','lc','vol'];

function renderChart(type, cfg, data, activeMetrics) {
  if (!type || !cfg) return;
  const canvas = document.getElementById('vizCanvas');
  const ctx = canvas.getContext('2d');

  if (type === 'hist') renderHistogram(ctx, canvas, data, activeMetrics);
  else if (type === 'box') renderBoxPlot(ctx, canvas, data, activeMetrics);
  else if (type === 'cdf') renderCDF(ctx, canvas, data, activeMetrics);
  else if (type === 'qq') renderQQ(ctx, canvas, data, activeMetrics);
  else if (type === 'kde') renderKDE(ctx, canvas, data, activeMetrics);
  else if (type === 'violin') renderViolin(ctx, canvas, data, activeMetrics);
  else if (type === 'line') renderMetricLine(ctx, canvas, data, activeMetrics);
  else if (type === 'rolling') renderRolling(ctx, canvas, data, activeMetrics);
  else if (type === 'bollinger') renderBollinger(ctx, canvas, data, activeMetrics);
  else if (type === 'hourbb') renderHourBB(ctx, canvas, data, activeMetrics);
  else if (type === 'weekpat') renderWeekPattern(ctx, canvas, data, activeMetrics);
  else if (type === 'scatter') renderScatter(ctx, canvas, data, activeMetrics);
  else if (type === 'heatmap') renderHeatmap(ctx, canvas, data, activeMetrics);
  else if (type === 'autocorr') renderAutoCorr(ctx, canvas, data, activeMetrics);
  else if (type === 'xcorr') renderXCorr(ctx, canvas, data, activeMetrics);
  else if (type === 'splom') renderSPLOM(ctx, canvas, data, activeMetrics);
  else if (type === 'pctlcurve') renderPctlCurve(ctx, canvas, data, activeMetrics);
  else if (type === 'rankcorr') renderRankCorridor(ctx, canvas, data, activeMetrics);
  else if (type === 'fanchart') renderFanChart(ctx, canvas, data, activeMetrics);
  else if (type === 'pctltable') renderPctlTable(ctx, canvas, data, activeMetrics);
  else if (type === 'volcluster') renderVolCluster(ctx, canvas, data, activeMetrics);
  else if (type === 'regimehist') renderRegimeHist(ctx, canvas, data, activeMetrics);
  else if (type === 'clusterscatter') renderClusterScatter(ctx, canvas, data, activeMetrics);
}

function metricVals(data, m) { return data.candles.map(c => c.metrics[m]); }
function metricLabel(m) { return METRICS[m]?.label || m; }

/* ─── Distribution charts ─── */
function renderHistogram(ctx, canvas, data, activeMetrics, getFamParam, famId) {
  const metrics = getFamMetrics(famId, activeMetrics);
  if (!metrics.length) return;
  const bins = parseInt(getFamParam ? getFamParam('bins') : 20) || 20;
  const datasets = [];
  const COLORS = ['#e94560','#26a69a','#42a5f5','#ab47bc','#ffa726','#66bb6a','#ef5350'];
  for (let mi = 0; mi < metrics.length; mi++) {
    const m = metrics[mi];
    const vals = metricVals(data, m);
    if (!vals.length) continue;
    const min = Math.min(...vals), max = Math.max(...vals), bw = (max - min) / bins || 1;
    const hist = new Array(bins).fill(0);
    for (const v of vals) hist[Math.min(Math.floor((v - min) / bw), bins - 1)]++;
    const c = COLORS[mi % COLORS.length];
    datasets.push({
      label: metricLabel(m), data: hist,
      backgroundColor: mi === 0 ? c : c + '44',
      borderColor: c, borderWidth: mi === 0 ? 1.5 : 0.5,
    });
  }
  if (!datasets.length) return;
  _chartInstances[famId] = _chart(ctx, {
    type: 'bar',
    data: {
      labels: datasets[0].data.map((_, i) => (Math.min(...metricVals(data, metrics[0])) + i * (Math.max(...metricVals(data, metrics[0])) - Math.min(...metricVals(data, metrics[0]))) / bins || 1).toFixed(2)),
      datasets,
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: '#888', font: { size: 9 } } },
        title: { display: true, text: `Distribution (${bins} bins)`, color: '#888', font: { size: 11 } },
      },
      scales: {
        x: { ticks: { color: '#888', font: { size: 9 }, maxTicksLimit: 20 }, grid: { color: '#16213e' }, title: { display: true, text: metrics.length === 1 ? metricLabel(metrics[0]) : 'Valeur', color: '#888', font: { size: 10 } } },
        y: { ticks: { color: '#888', font: { size: 9 } }, grid: { color: '#16213e' }, title: { display: true, text: 'Count', color: '#888', font: { size: 10 } } },
      },
    },
  });
}

function renderBoxPlot(ctx, canvas, data, activeMetrics, getFamParam, famId) {
  const metric = (getFamMetrics(famId, activeMetrics)[0] || activeMetrics[0]);
  const vals = metricVals(data, metric);
  if (!vals.length) return;
  const s = [...vals].sort((a, b) => a - b);
  const n = s.length;
  const q1 = s[Math.floor(n * 0.25)], med = n % 2 === 0 ? (s[n/2-1] + s[n/2]) / 2 : s[Math.floor(n/2)], q3 = s[Math.floor(n * 0.75)];
  const iqr = q3 - q1, fenceLo = q1 - 1.5 * iqr, fenceHi = q3 + 1.5 * iqr;
  const whiskerLo = Math.min(...vals.filter(v => v >= fenceLo));
  const whiskerHi = Math.max(...vals.filter(v => v <= fenceHi));
  const outlierVals = vals.filter(v => v < fenceLo || v > fenceHi);
  // render as bar chart with box+whisker info in labels
  _chartInstances[famId] = _chart(ctx, {
    type: 'bar',
    data: {
      labels: [metricLabel(metric)],
      datasets: [
        { label: 'Min', data: [s[0]], backgroundColor: '#0f3460' },
        { label: 'Q1', data: [q1], backgroundColor: '#f0a030' },
        { label: 'Median', data: [med], backgroundColor: '#e94560' },
        { label: 'Q3', data: [q3], backgroundColor: '#26a69a' },
        { label: 'Max', data: [s[n-1]], backgroundColor: '#0f3460' },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        title: { display: true, text: `Box plot: ${metricLabel(metric)} (IQR=${iqr.toFixed(2)}, ${outlierVals.length} outliers)`, color: '#888', font: { size: 11 } },
        legend: { labels: { color: '#888', font: { size: 9 } } },
        tooltip: { callbacks: { title: () => `${metricLabel(metric)} summary`, label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y.toFixed(4)}` } },
      },
      scales: {
        x: { ticks: { color: '#888', font: { size: 10 } }, grid: { display: false } },
        y: { ticks: { color: '#888', font: { size: 9 } }, grid: { color: '#16213e' }, title: { display: true, text: metricLabel(metric), color: '#888', font: { size: 10 } } },
      },
    },
  });
}

function cdfData(vals) {
  const s = [...vals].sort((a, b) => a - b);
  return s.map((v, i) => ({ x: v, y: (i + 1) / s.length * 100 }));
}

function renderCDF(ctx, canvas, data, activeMetrics, getFamParam, famId) {
  const metric = (getFamMetrics(famId, activeMetrics)[0] || activeMetrics[0]);
  const vals = metricVals(data, metric);
  if (!vals.length) return;
  const pts = cdfData(vals);
  _chartInstances[famId] = _chart(ctx, {
    type: 'scatter',
    data: {
      datasets: [{
        label: metricLabel(metric), data: pts, showLine: true,
        borderColor: '#26a69a', backgroundColor: 'rgba(38,166,154,0.1)', fill: true,
        pointRadius: 0, borderWidth: 2,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        title: { display: true, text: `CDF: ${metricLabel(metric)}`, color: '#888', font: { size: 11 } },
        legend: { display: false },
      },
      scales: {
        x: { title: { display: true, text: metricLabel(metric), color: '#888', font: { size: 10 } }, ticks: { color: '#888', font: { size: 9 } }, grid: { color: '#16213e' } },
        y: { title: { display: true, text: 'Cumulative %', color: '#888', font: { size: 10 } }, ticks: { color: '#888', font: { size: 9 }, callback: v => v + '%' }, grid: { color: '#16213e' } },
      },
    },
  });
}

function renderQQ(ctx, canvas, data, activeMetrics, getFamParam, famId) {
  const metric = (getFamMetrics(famId, activeMetrics)[0] || activeMetrics[0]);
  const vals = metricVals(data, metric);
  if (!vals.length) return;
  const s = [...vals].sort((a, b) => a - b);
  const n = s.length;
  const mean = s.reduce((a, b) => a + b, 0) / n;
  const std = Math.sqrt(s.reduce((a, v) => a + (v - mean) ** 2, 0) / n);
  const theoretical = Array.from({length: n}, (_, i) => {
    // approximate normal quantile
    const p = (i + 0.5) / n;
    // simple normal quantile approximation
    const t = Math.sqrt(-2 * Math.log(1 - p));
    return mean + std * (t - (2.515517 + 0.802853 * t + 0.010328 * t * t) / (1 + 1.432788 * t + 0.189269 * t * t + 0.001308 * t * t * t));
  });
  const pts = theoretical.map((x, i) => ({ x, y: s[i] }));
  const minX = Math.min(...theoretical), maxX = Math.max(...theoretical);
  const diag = [{ x: minX, y: minX }, { x: maxX, y: maxX }];
  _chartInstances[famId] = _chart(ctx, {
    type: 'scatter',
    data: {
      datasets: [
        { label: 'Quantiles', data: pts, backgroundColor: 'rgba(233,69,96,0.5)', pointRadius: 1.5 },
        { label: 'Normal', data: diag, type: 'line', borderColor: '#26a69a', borderWidth: 1, pointRadius: 0, borderDash: [4, 4], fill: false },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        title: { display: true, text: `QQ-plot: ${metricLabel(metric)}`, color: '#888', font: { size: 11 } },
        legend: { labels: { color: '#888', font: { size: 9 } } },
      },
      scales: {
        x: { title: { display: true, text: 'Theoretical normal', color: '#888', font: { size: 10 } }, ticks: { color: '#888', font: { size: 9 } }, grid: { color: '#16213e' } },
        y: { title: { display: true, text: `Sample ${metricLabel(metric)}`, color: '#888', font: { size: 10 } }, ticks: { color: '#888', font: { size: 9 } }, grid: { color: '#16213e' } },
      },
    },
  });
}

function renderKDE(ctx, canvas, data, activeMetrics, getFamParam, famId) {
  const metric = (getFamMetrics(famId, activeMetrics)[0] || activeMetrics[0]);
  const bw = parseFloat(getFamParam('bw')) || 0.5;
  const vals = metricVals(data, metric);
  if (!vals.length) return;
  const min = Math.min(...vals), max = Math.max(...vals), pts = 200;
  const step = (max - min) / pts;
  const n = vals.length;
  const density = Array.from({length: pts}, (_, i) => {
    const x = min + i * step;
    let sum = 0;
    for (const v of vals) sum += Math.exp(-0.5 * ((x - v) / bw) ** 2) / Math.sqrt(2 * Math.PI);
    return { x, y: sum / (n * bw) };
  });
  _chartInstances[famId] = _chart(ctx, {
    type: 'scatter',
    data: {
      datasets: [{
        label: metricLabel(metric), data: density, showLine: true,
        borderColor: '#e94560', backgroundColor: 'rgba(233,69,96,0.15)', fill: true,
        pointRadius: 0, borderWidth: 2,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        title: { display: true, text: `KDE: ${metricLabel(metric)} (bw=${bw})`, color: '#888', font: { size: 11 } },
        legend: { display: false },
      },
      scales: {
        x: { title: { display: true, text: metricLabel(metric), color: '#888', font: { size: 10 } }, ticks: { color: '#888', font: { size: 9 } }, grid: { color: '#16213e' } },
        y: { title: { display: true, text: 'Density', color: '#888', font: { size: 10 } }, ticks: { color: '#888', font: { size: 9 } }, grid: { color: '#16213e' } },
      },
    },
  });
}

function renderViolin(ctx, canvas, data, activeMetrics, getFamParam, famId) {
  const metric = (getFamMetrics(famId, activeMetrics)[0] || activeMetrics[0]);
  const vals = metricVals(data, metric);
  if (!vals.length) return;
  const bw = 0.3;
  const min = Math.min(...vals), max = Math.max(...vals), pts = 100;
  const step = (max - min) / pts;
  const n = vals.length;
  const density = Array.from({length: pts}, (_, i) => {
    const x = min + i * step;
    let sum = 0;
    for (const v of vals) sum += Math.exp(-0.5 * ((x - v) / bw) ** 2);
    return { x: x, d: sum / (n * bw) };
  });
  const maxD = Math.max(...density.map(d => d.d));
  const violPts = density.flatMap(p => [
    { x: 1 - p.d / maxD, y: p.x },
    { x: 1 + p.d / maxD, y: p.x },
  ]);
  _chartInstances[famId] = _chart(ctx, {
    type: 'scatter',
    data: {
      datasets: [{
        label: metricLabel(metric), data: violPts, showLine: true,
        borderColor: '#e94560', backgroundColor: 'rgba(233,69,96,0.3)', fill: false,
        pointRadius: 0, borderWidth: 1.5,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        title: { display: true, text: `Violin: ${metricLabel(metric)}`, color: '#888', font: { size: 11 } },
        legend: { display: false },
      },
      scales: {
        x: { display: false, grid: { display: false } },
        y: { title: { display: true, text: metricLabel(metric), color: '#888', font: { size: 10 } }, ticks: { color: '#888', font: { size: 9 } }, grid: { color: '#16213e' } },
      },
    },
  });
}

/* ─── Time Series charts ─── */
function renderMetricLine(ctx, canvas, data, activeMetrics, getFamParam, famId) {
  const metrics = getFamMetrics(famId, activeMetrics);
  if (!metrics.length) return;
  const smooth = parseInt(getFamParam ? getFamParam('smooth') : 1) || 1;
  const COLORS = ['#e94560','#26a69a','#42a5f5','#ab47bc','#ffa726','#66bb6a','#ef5350'];
  const datasets = [];
  for (let mi = 0; mi < metrics.length; mi++) {
    const m = metrics[mi];
    const vals = metricVals(data, m);
    if (!vals.length) continue;
    const pts = vals.map((v, i) => ({ x: data.candles[i].t, y: v }));
    if (smooth > 1) {
      for (let i = smooth; i < pts.length; i++) {
        let s = 0;
        for (let j = 0; j < smooth; j++) s += pts[i - j].y;
        pts[i].y = s / smooth;
      }
    }
    const c = COLORS[mi % COLORS.length];
    datasets.push({
      label: metricLabel(m), data: pts, showLine: true,
      borderColor: c, backgroundColor: mi === 0 ? c + '22' : c + '11',
      fill: mi === 0, pointRadius: 0, borderWidth: mi === 0 ? 2 : 1,
    });
  }
  if (!datasets.length) return;
  const titleMetrics = metrics.map(m => metricLabel(m)).join(', ');
  _chartInstances[famId] = _chart(ctx, {
    type: 'scatter',
    data: { datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        title: { display: true, text: `${titleMetrics} (smooth=${smooth})`, color: '#888', font: { size: 11 } },
        legend: { labels: { color: '#888', font: { size: 9 } } },
      },
      scales: {
        x: { type: 'linear', ticks: { callback: v => new Date(v).toLocaleDateString('fr-FR', { timeZone: 'Europe/Paris', day: '2-digit', month: 'short' }), maxTicksLimit: 12, color: '#888', font: { size: 9 } }, grid: { color: '#16213e' }, title: { display: true, text: 'Date (Europe/Paris)', color: '#888', font: { size: 10 } } },
        y: { title: { display: true, text: metrics.length === 1 ? metricLabel(metrics[0]) : 'Valeur', color: '#888', font: { size: 10 } }, ticks: { color: '#888', font: { size: 9 } }, grid: { color: '#16213e' } },
      },
    },
  });
}

function renderRolling(ctx, canvas, data, activeMetrics, getFamParam, famId) {
  const metric = (getFamMetrics(famId, activeMetrics)[0] || activeMetrics[0]);
  const w = parseInt(getFamParam('rwindow')) || 20;
  const stat = getFamParam('rstat') || 'mean';
  const vals = metricVals(data, metric);
  if (!vals.length) return;
  const n = vals.length;
  const pts = [];
  for (let i = w - 1; i < n; i++) {
    const window = vals.slice(i - w + 1, i + 1);
    const m = window.reduce((a, b) => a + b, 0) / w;
    const s = Math.sqrt(window.reduce((a, v) => a + (v - m) ** 2, 0) / w);
    pts.push({ x: data.candles[i].t, y: stat === 'std' ? s : stat === 'skew' ? window.reduce((a,v)=> a + ((v-m)/s)**3, 0) / w : m });
  }
  _chartInstances[famId] = _chart(ctx, {
    type: 'scatter',
    data: {
      datasets: [{
        label: `Rolling ${stat}(${metricLabel(metric)}, ${w})`, data: pts, showLine: true,
        borderColor: '#26a69a', pointRadius: 0, borderWidth: 1.5, fill: false,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        title: { display: true, text: `Rolling ${stat}: ${metricLabel(metric)} (w=${w})`, color: '#888', font: { size: 11 } },
        legend: { labels: { color: '#888', font: { size: 9 } } },
      },
      scales: {
        x: { type: 'linear', ticks: { callback: v => new Date(v).toLocaleDateString('fr-FR', { timeZone: 'Europe/Paris', day: '2-digit', month: 'short' }), maxTicksLimit: 12, color: '#888', font: { size: 9 } }, grid: { color: '#16213e' }, title: { display: true, text: 'Date (Europe/Paris)', color: '#888', font: { size: 10 } } },
        y: { title: { display: true, text: stat, color: '#888', font: { size: 10 } }, ticks: { color: '#888', font: { size: 9 } }, grid: { color: '#16213e' } },
      },
    },
  });
}

function renderBollinger(ctx, canvas, data, activeMetrics, getFamParam, famId) {
  const metric = (getFamMetrics(famId, activeMetrics)[0] || activeMetrics[0]);
  const w = parseInt(getFamParam('bwindow')) || 20;
  const k = parseFloat(getFamParam('bk')) || 2;
  const vals = metricVals(data, metric);
  if (!vals.length) return;
  const n = vals.length;
  const mid = [], upper = [], lower = [];
  for (let i = w - 1; i < n; i++) {
    const window = vals.slice(i - w + 1, i + 1);
    const m = window.reduce((a, b) => a + b, 0) / w;
    const s = Math.sqrt(window.reduce((a, v) => a + (v - m) ** 2, 0) / w);
    const t = data.candles[i].t;
    mid.push({ x: t, y: m });
    upper.push({ x: t, y: m + k * s });
    lower.push({ x: t, y: m - k * s });
  }
  _chartInstances[famId] = _chart(ctx, {
    type: 'scatter',
    data: {
      datasets: [
        { label: 'Value', data: vals.map((v, i) => ({ x: data.candles[i].t, y: v })), showLine: true, borderColor: '#e94560', pointRadius: 0, borderWidth: 1, fill: false },
        { label: `Mid (${w})`, data: mid, showLine: true, borderColor: '#888', pointRadius: 0, borderWidth: 1.5, borderDash: [3, 3], fill: false },
        { label: `±${k}σ`, data: upper, showLine: true, borderColor: '#26a69a', pointRadius: 0, borderWidth: 1, fill: '-2', backgroundColor: 'rgba(38,166,154,0.1)' },
        { label: `−${k}σ`, data: lower, showLine: true, borderColor: '#ef5350', pointRadius: 0, borderWidth: 1, fill: false },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        title: { display: true, text: `Bollinger bands: ${metricLabel(metric)} (${w}, ${k}σ)`, color: '#888', font: { size: 11 } },
        legend: { labels: { color: '#888', font: { size: 9 } } },
      },
      scales: {
        x: { type: 'linear', ticks: { callback: v => new Date(v).toLocaleDateString('fr-FR', { timeZone: 'Europe/Paris', day: '2-digit', month: 'short' }), maxTicksLimit: 12, color: '#888', font: { size: 9 } }, grid: { color: '#16213e' }, title: { display: true, text: 'Date (Europe/Paris)', color: '#888', font: { size: 10 } } },
        y: { title: { display: true, text: metricLabel(metric), color: '#888', font: { size: 10 } }, ticks: { color: '#888', font: { size: 9 } }, grid: { color: '#16213e' } },
      },
    },
  });
}

function renderHourBB(ctx, canvas, data, activeMetrics) {
  const hourCounts = Array.from({length: 24}, () => ({ bull: 0, bear: 0 }));
  let totalBull = 0, totalBear = 0;
  for (const c of data.candles) {
    const h = new Date(c.t).getUTCHours();
    if (c.c >= c.o) { hourCounts[h].bull++; totalBull++; }
    else { hourCounts[h].bear++; totalBear++; }
  }
  const ratio = totalBear > 0 ? (totalBull / totalBear).toFixed(2) : '—';
  const labels = hourCounts.map((_, i) => `${i}h`);
  window._vizChart = _chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: 'Bull', data: hourCounts.map(h => h.bull), backgroundColor: '#26a69a' },
        { label: 'Bear', data: hourCounts.map(h => h.bear), backgroundColor: '#ef5350' },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        title: { display: true, text: `Bull/Bear by hour · ${totalBull}B / ${totalBear}B = ${ratio}:1`, color: '#888', font: { size: 11 } },
        legend: { labels: { color: '#888', font: { size: 9 } } },
      },
      scales: {
        x: { stacked: true, ticks: { color: '#888', font: { size: 8 } }, grid: { color: '#16213e' } },
        y: { stacked: true, ticks: { color: '#888', font: { size: 9 } }, grid: { color: '#16213e' } },
      },
    },
  });
}

function renderWeekPattern(ctx, canvas, data, activeMetrics, getFamParam, famId) {
  const metric = (getFamMetrics(famId, activeMetrics)[0] || activeMetrics[0]);
  const vals = data.candles.map(c => {
    const d = new Date(c.t);
    return { hour: d.getUTCHours(), dow: d.getUTCDay(), val: c.metrics[metric] };
  });
  const grid = Array.from({length: 7}, () => new Array(24).fill(0));
  const count = Array.from({length: 7}, () => new Array(24).fill(0));
  for (const v of vals) {
    grid[v.dow][v.hour] += v.val;
    count[v.dow][v.hour]++;
  }
  const avgGrid = grid.map((row, i) => row.map((s, j) => count[i][j] ? s / count[i][j] : 0));
  const allVals = avgGrid.flat();
  const cmin = Math.min(...allVals), cmax = Math.max(...allVals);
  const cRange = cmax - cmin || 1;
  const days = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
  const hours = Array.from({length: 24}, (_, i) => `${i}h`);
  const cellW = Math.min(35, Math.floor((canvas.width || 600) / 28));
  const cellH = cellW;
  const pad = 40;
  canvas.width = pad + 24 * cellW + 10;
  canvas.height = pad + 7 * cellH + 10;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = '#16213e';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = '#888';
  ctx.font = '9px sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  for (let h = 0; h < 24; h++) ctx.fillText(hours[h], pad + h * cellW + cellW / 2, pad / 2 - 2);
  for (let d = 0; d < 7; d++) ctx.fillText(days[d], pad / 2 - 2, pad + d * cellH + cellH / 2);
  for (let d = 0; d < 7; d++) {
    for (let h = 0; h < 24; h++) {
      const v = avgGrid[d][h];
      const t = (v - cmin) / cRange;
      ctx.fillStyle = `rgba(233,69,96,${0.1 + t * 0.8})`;
      ctx.fillRect(pad + h * cellW, pad + d * cellH, cellW - 1, cellH - 1);
      ctx.fillStyle = '#fff';
      ctx.font = '7px sans-serif';
      ctx.fillText(v.toFixed(1), pad + h * cellW + (cellW - 1) / 2, pad + d * cellH + (cellH - 1) / 2);
    }
  }
}

/* ─── Correlation charts ─── */
function renderScatter(ctx, canvas, data, activeMetrics, getFamParam, famId) {
  const xKey = getFamParam('sx') || activeMetrics[0];
  const yKey = getFamParam('sy') || (activeMetrics.length > 1 ? activeMetrics[1] : activeMetrics[0]);
  const points = data.candles.map(c => ({ x: c.metrics[xKey], y: c.metrics[yKey] }));
  if (!points.length) return;
  const n = points.length;
  const sx = points.reduce((a, p) => a + p.x, 0), sy = points.reduce((a, p) => a + p.y, 0);
  const sxx = points.reduce((a, p) => a + p.x * p.x, 0), sxy = points.reduce((a, p) => a + p.x * p.y, 0);
  const slope = (n * sxy - sx * sy) / (n * sxx - sx * sx);
  const intercept = (sy - slope * sx) / n;
  const xMin = Math.min(...points.map(p => p.x)), xMax = Math.max(...points.map(p => p.x));
  const syy = points.reduce((a, p) => a + p.y * p.y, 0);
  const r = (n * sxy - sx * sy) / Math.sqrt((n * sxx - sx * sx) * (n * syy - sy * sy));
  _chartInstances[famId] = _chart(ctx, {
    type: 'scatter',
    data: {
      datasets: [
        { label: 'Candles', data: points, backgroundColor: 'rgba(233,69,96,0.3)', borderColor: '#e94560', pointRadius: 1.5 },
        { label: `Regression (r=${r.toFixed(3)})`, data: [{ x: xMin, y: slope * xMin + intercept }, { x: xMax, y: slope * xMax + intercept }], type: 'line', borderColor: '#26a69a', borderWidth: 2, pointRadius: 0, fill: false },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: '#888', font: { size: 9 } } },
        title: { display: true, text: `${metricLabel(xKey)} vs ${metricLabel(yKey)}  (r=${r.toFixed(3)}, n=${n})`, color: '#888', font: { size: 11 } },
      },
      scales: {
        x: { title: { display: true, text: metricLabel(xKey), color: '#888', font: { size: 10 } }, ticks: { color: '#888', font: { size: 9 } }, grid: { color: '#16213e' } },
        y: { title: { display: true, text: metricLabel(yKey), color: '#888', font: { size: 10 } }, ticks: { color: '#888', font: { size: 9 } }, grid: { color: '#16213e' } },
      },
    },
  });
}

function renderHeatmap(ctx, canvas, data, activeMetrics, getFamParam, famId) {
  const m = activeMetrics;
  const n = m.length;
  if (n < 2) return;
  const corr = Array.from({length: n}, () => new Array(n).fill(0));
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      if (i === j) { corr[i][j] = 1; continue; }
      const xi = metricVals(data, m[i]), xj = metricVals(data, m[j]);
      const nk = xi.length;
      const sxi = xi.reduce((a, v) => a + v, 0), sxj = xj.reduce((a, v) => a + v, 0);
      const sxixi = xi.reduce((a, v) => a + v * v, 0), sxjxj = xj.reduce((a, v) => a + v * v, 0);
      const sxixj = xi.reduce((a, v, k) => a + v * xj[k], 0);
      const denom = Math.sqrt((nk * sxixi - sxi * sxi) * (nk * sxjxj - sxj * sxj));
      corr[i][j] = denom ? (nk * sxixj - sxi * sxj) / denom : 0;
    }
  }
  const labels = m.map(k => metricLabel(k));
  const dpr = window.devicePixelRatio || 1;
  const containerW = canvas.parentElement ? canvas.parentElement.clientWidth : 400;
  const cellSize = Math.max(24, Math.min(50, Math.floor((containerW - 40) / (n + 1.5))));
  const offset = cellSize * 1.5, dim = cellSize * n;
  const totalW = dim + offset + 10, totalH = dim + offset + 10;
  canvas.width = totalW * dpr; canvas.height = totalH * dpr;
  canvas.style.width = totalW + 'px'; canvas.style.height = totalH + 'px';
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, totalW, totalH);
  ctx.fillStyle = '#16213e'; ctx.fillRect(0, 0, totalW, totalH);
  ctx.fillStyle = '#888'; ctx.font = `${Math.max(9, cellSize * 0.35)}px sans-serif`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  for (let i = 0; i < n; i++) {
    ctx.fillText(labels[i], offset + i * cellSize + cellSize / 2, offset / 2 - 2);
    ctx.save(); ctx.translate(offset / 2 - 2, offset + i * cellSize + cellSize / 2); ctx.rotate(-Math.PI / 2); ctx.fillText(labels[i], 0, 0); ctx.restore();
  }
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      const v = corr[i][j], a = Math.abs(v);
      ctx.fillStyle = `rgba(${v >= 0 ? '38,166,154' : '239,83,80'},${0.3 + a * 0.7})`;
      ctx.fillRect(offset + j * cellSize, offset + i * cellSize, cellSize - 2, cellSize - 2);
      ctx.fillStyle = '#fff'; ctx.font = `${Math.max(8, cellSize * 0.3)}px sans-serif`;
      ctx.fillText(v.toFixed(2), offset + j * cellSize + (cellSize - 2) / 2, offset + i * cellSize + (cellSize - 2) / 2 + 1);
    }
  }
  // hover tooltip via overlay
  canvas.onmousemove = (e) => {
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    const col = Math.floor((mx - offset) / cellSize), row = Math.floor((my - offset) / cellSize);
    if (row >= 0 && row < n && col >= 0 && col < n) {
      canvas.title = `${labels[row]} × ${labels[col]}: r=${corr[row][col].toFixed(4)}`;
    } else {
      canvas.title = '';
    }
  };
}

function renderAutoCorr(ctx, canvas, data, activeMetrics, getFamParam, famId) {
  const metric = (getFamMetrics(famId, activeMetrics)[0] || activeMetrics[0]);
  const maxLag = parseInt(getFamParam('maxlag')) || 20;
  const vals = metricVals(data, metric);
  if (!vals.length || vals.length < maxLag + 2) return;
  const n = vals.length;
  const mean = vals.reduce((a, b) => a + b, 0) / n;
  const var_ = vals.reduce((a, v) => a + (v - mean) ** 2, 0);
  const ac = [];
  for (let lag = 1; lag <= maxLag; lag++) {
    let cov = 0;
    for (let i = lag; i < n; i++) cov += (vals[i] - mean) * (vals[i - lag] - mean);
    ac.push({ x: lag, y: cov / var_ });
  }
  _chartInstances[famId] = _chart(ctx, {
    type: 'bar',
    data: {
      labels: ac.map(a => a.x),
      datasets: [{
        label: metricLabel(metric), data: ac.map(a => a.y),
        backgroundColor: ac.map(a => Math.abs(a.y) > 0.2 ? '#e94560' : '#0f3460'),
        borderColor: '#1a1a2e', borderWidth: 1,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        title: { display: true, text: `Autocorrelation: ${metricLabel(metric)}`, color: '#888', font: { size: 11 } },
        legend: { display: false },
      },
      scales: {
        x: { title: { display: true, text: 'Lag', color: '#888', font: { size: 10 } }, ticks: { color: '#888', font: { size: 9 } }, grid: { color: '#16213e' } },
        y: { title: { display: true, text: 'r', color: '#888', font: { size: 10 } }, ticks: { color: '#888', font: { size: 9 } }, grid: { color: '#16213e' } },
      },
    },
  });
}

function renderXCorr(ctx, canvas, data, activeMetrics, getFamParam, famId) {
  const aKey = getFamParam('xca') || activeMetrics[0];
  const bKey = getFamParam('xcb') || (activeMetrics.length > 1 ? activeMetrics[1] : activeMetrics[0]);
  const maxLag = parseInt(getFamParam('xclag')) || 10;
  const va = metricVals(data, aKey), vb = metricVals(data, bKey);
  if (!va.length || va.length < maxLag + 2) return;
  const n = va.length;
  const ma = va.reduce((a, b) => a + b, 0) / n, mb = vb.reduce((a, b) => a + b, 0) / n;
  const vars = Math.sqrt(va.reduce((a, v) => a + (v - ma) ** 2, 0) * vb.reduce((a, v) => a + (v - mb) ** 2, 0)) || 1;
  const pts = [];
  for (let lag = -maxLag; lag <= maxLag; lag++) {
    let cov = 0, cnt = 0;
    for (let i = 0; i < n; i++) {
      const j = i + lag;
      if (j >= 0 && j < n) { cov += (va[i] - ma) * (vb[j] - mb); cnt++; }
    }
    pts.push({ x: lag, y: cov / (vars || 1) });
  }
  _chartInstances[famId] = _chart(ctx, {
    type: 'bar',
    data: {
      labels: pts.map(p => p.x),
      datasets: [{
        label: `${metricLabel(aKey)} vs ${metricLabel(bKey)}`, data: pts.map(p => p.y),
        backgroundColor: pts.map(p => Math.abs(p.y) > 0.2 ? '#26a69a' : '#0f3460'),
        borderColor: '#1a1a2e', borderWidth: 1,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        title: { display: true, text: `Cross-correlation: ${metricLabel(aKey)} vs ${metricLabel(bKey)}`, color: '#888', font: { size: 11 } },
        legend: { display: false },
      },
      scales: {
        x: { title: { display: true, text: 'Lag (+ = A leads)', color: '#888', font: { size: 10 } }, ticks: { color: '#888', font: { size: 9 } }, grid: { color: '#16213e' } },
        y: { title: { display: true, text: 'r', color: '#888', font: { size: 10 } }, ticks: { color: '#888', font: { size: 9 } }, grid: { color: '#16213e' } },
      },
    },
  });
}

function renderSPLOM(ctx, canvas, data, activeMetrics, getFamParam, famId) {
  if (activeMetrics.length < 2) return;
  const m = activeMetrics;
  const n = m.length;
  const size = Math.min(120, Math.floor((canvas.width || 600) / n));
  const pad = 30;
  canvas.width = pad + n * size;
  canvas.height = pad + n * size;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = '#16213e'; ctx.fillRect(0, 0, canvas.width, canvas.height);
  for (let r = 0; r < n; r++) {
    for (let c = 0; c < n; c++) {
      if (r === c) {
        ctx.fillStyle = '#0f3460'; ctx.fillRect(pad + c * size, pad + r * size, size - 1, size - 1);
        ctx.fillStyle = '#888'; ctx.font = '8px sans-serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillText(metricLabel(m[r]), pad + c * size + size / 2, pad + r * size + size / 2);
        continue;
      }
      const xi = metricVals(data, m[c]), yi = metricVals(data, m[r]);
      const xRange = Math.max(...xi) - Math.min(...xi) || 1, yRange = Math.max(...yi) - Math.min(...yi) || 1;
      const xMin = Math.min(...xi), yMin = Math.min(...yi);
      ctx.fillStyle = 'rgba(233,69,96,0.15)';
      for (let k = 0; k < xi.length; k++) {
        const px = pad + c * size + ((xi[k] - xMin) / xRange) * (size - 4) + 2;
        const py = pad + r * size + (1 - (yi[k] - yMin) / yRange) * (size - 4) + 2;
        ctx.fillRect(px, py, 1.5, 1.5);
      }
      ctx.strokeStyle = '#0f3460'; ctx.lineWidth = 1; ctx.strokeRect(pad + c * size, pad + r * size, size - 1, size - 1);
    }
  }
  // labels on axes
  ctx.fillStyle = '#888'; ctx.font = '9px sans-serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  for (let i = 0; i < n; i++) {
    ctx.save(); ctx.translate(pad + i * size + size / 2, pad / 2 - 2); ctx.fillText(metricLabel(m[i]), 0, 0); ctx.restore();
    ctx.save(); ctx.translate(pad / 2 - 2, pad + i * size + size / 2); ctx.rotate(-Math.PI / 2); ctx.fillText(metricLabel(m[i]), 0, 0); ctx.restore();
  }
}

/* ─── Percentile charts ─── */
function renderPctlCurve(ctx, canvas, data, activeMetrics, getFamParam, famId) {
  const metrics = getFamMetrics(famId, activeMetrics);
  if (!metrics.length) return;
  const COLORS = ['#e94560','#26a69a','#42a5f5','#ab47bc','#ffa726','#66bb6a','#ef5350'];
  const datasets = [];
  for (let mi = 0; mi < metrics.length; mi++) {
    const m = metrics[mi];
    const vals = metricVals(data, m);
    if (!vals.length) continue;
    const s = [...vals].sort((a, b) => a - b);
    const pts = s.map((v, i) => ({ x: v, y: (i + 1) / s.length * 100 }));
    const c = COLORS[mi % COLORS.length];
    datasets.push({
      label: metricLabel(m), data: pts, showLine: true,
      borderColor: c, pointRadius: 0, borderWidth: mi === 0 ? 2 : 1, fill: false,
    });
  }
  if (!datasets.length) return;
  const titleMetrics = metrics.map(m => metricLabel(m)).join(', ');
  _chartInstances[famId] = _chart(ctx, {
    type: 'scatter',
    data: { datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        title: { display: true, text: `Courbe percentile: ${titleMetrics}`, color: '#888', font: { size: 11 } },
        legend: { labels: { color: '#888', font: { size: 9 } } },
      },
      scales: {
        x: { title: { display: true, text: metrics.length === 1 ? metricLabel(metrics[0]) : 'Valeur', color: '#888', font: { size: 10 } }, ticks: { color: '#888', font: { size: 9 } }, grid: { color: '#16213e' } },
        y: { title: { display: true, text: 'Percentile rank (%)', color: '#888', font: { size: 10 } }, ticks: { color: '#888', font: { size: 9 }, callback: v => v + '%' }, grid: { color: '#16213e' } },
      },
    },
  });
}

function renderRankCorridor(ctx, canvas, data, activeMetrics, getFamParam, famId) {
  const metric = (getFamMetrics(famId, activeMetrics)[0] || activeMetrics[0]);
  const vals = metricVals(data, metric);
  const sorted = [...vals].sort((a, b) => a - b);
  const n = sorted.length;
  if (!n) return;
  const pts = vals.map((v, i) => {
    let cnt = 0;
    for (const s of sorted) if (s < v) cnt++;
    return { x: data.candles[i].t, y: cnt / n * 100 };
  });
  _chartInstances[famId] = _chart(ctx, {
    type: 'scatter',
    data: {
      datasets: [{
        label: 'Percentile', data: pts, showLine: true,
        borderColor: '#26a69a', backgroundColor: 'rgba(38,166,154,0.1)', fill: true,
        pointRadius: 0, borderWidth: 1.5,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        title: { display: true, text: `Rank corridor: ${metricLabel(metric)}`, color: '#888', font: { size: 11 } },
        legend: { display: false },
      },
      scales: {
        x: { type: 'linear', ticks: { callback: v => new Date(v).toLocaleDateString('fr-FR', { timeZone: 'Europe/Paris', day: '2-digit', month: 'short' }), maxTicksLimit: 12, color: '#888', font: { size: 9 } }, grid: { color: '#16213e' }, title: { display: true, text: 'Date (Europe/Paris)', color: '#888', font: { size: 10 } } },
        y: { title: { display: true, text: 'Percentile', color: '#888', font: { size: 10 } }, min: 0, max: 100, ticks: { color: '#888', font: { size: 9 }, callback: v => v + '%' }, grid: { color: '#16213e' } },
      },
    },
  });
}

function renderFanChart(ctx, canvas, data, activeMetrics, getFamParam, famId) {
  const metric = (getFamMetrics(famId, activeMetrics)[0] || activeMetrics[0]);
  const vals = metricVals(data, metric);
  const sorted = [...vals].sort((a, b) => a - b);
  const n = sorted.length;
  if (!n) return;
  const pctAtIdx = idx => {
    let cnt = 0;
    for (const s of sorted) if (s < vals[idx]) cnt++;
    return cnt / n;
  };
  const bands = [10, 25, 50, 75, 90];
  const datasets = bands.map(b => ({
    label: `${b}%`, data: vals.map((_, i) => ({ x: data.candles[i].t, y: pctAtIdx(i) * 100 })),
    showLine: true, borderColor: b === 50 ? '#e94560' : '#888',
    borderWidth: b === 50 ? 2 : 0.5, borderDash: b === 50 ? [] : [2, 2],
    pointRadius: 0, fill: b > 50 ? '+1' : false,
    backgroundColor: `rgba(233,69,96,${0.05 + Math.abs(b - 50) / 100})`,
  }));
  _chartInstances[famId] = _chart(ctx, {
    type: 'scatter',
    data: { datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        title: { display: true, text: `Fan chart: ${metricLabel(metric)}`, color: '#888', font: { size: 11 } },
        legend: { labels: { color: '#888', font: { size: 9 } } },
      },
      scales: {
        x: { type: 'linear', ticks: { callback: v => new Date(v).toLocaleDateString('fr-FR', { timeZone: 'Europe/Paris', day: '2-digit', month: 'short' }), maxTicksLimit: 12, color: '#888', font: { size: 9 } }, grid: { color: '#16213e' }, title: { display: true, text: 'Date (Europe/Paris)', color: '#888', font: { size: 10 } } },
        y: { title: { display: true, text: 'Percentile', color: '#888', font: { size: 10 } }, min: 0, max: 100, ticks: { color: '#888', font: { size: 9 }, callback: v => v + '%' }, grid: { color: '#16213e' } },
      },
    },
  });
}

function renderPctlTable(ctx, canvas, data, activeMetrics, getFamParam, famId) {
  const metric = (getFamMetrics(famId, activeMetrics)[0] || activeMetrics[0]);
  const vals = metricVals(data, metric);
  const s = [...vals].sort((a, b) => a - b);
  const n = s.length;
  const buckets = 10;
  const labels = [], counts = [], mins = [], maxs = [];
  for (let i = 0; i < buckets; i++) {
    const lo = Math.floor(i * n / buckets), hi = Math.floor((i + 1) * n / buckets) - 1;
    labels.push(`${i*10}-${(i+1)*10}%`);
    counts.push(hi - lo + 1);
    mins.push(s[lo]);
    maxs.push(s[hi]);
  }
  _chartInstances[famId] = _chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: 'Min', data: mins, backgroundColor: 'rgba(38,166,154,0.5)', borderColor: '#26a69a', borderWidth: 1 },
        { label: 'Max', data: maxs, backgroundColor: 'rgba(233,69,96,0.5)', borderColor: '#e94560', borderWidth: 1 },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        title: { display: true, text: `Percentile buckets: ${metricLabel(metric)}`, color: '#888', font: { size: 11 } },
        legend: { labels: { color: '#888', font: { size: 9 } } },
        tooltip: { callbacks: {
          afterBody: function(ctx) {
            const i = ctx[0].dataIndex;
            return `Count: ${counts[i]}\nRange: ${mins[i].toFixed(2)} – ${maxs[i].toFixed(2)}`;
          }
        }},
      },
      scales: {
        x: { ticks: { color: '#888', font: { size: 9 } }, grid: { color: '#16213e' } },
        y: { ticks: { color: '#888', font: { size: 9 } }, grid: { color: '#16213e' }, title: { display: true, text: 'Value', color: '#888', font: { size: 10 } } },
      },
    },
  });
}

/* ─── Pattern charts ─── */
function renderVolCluster(ctx, canvas, data, activeMetrics, getFamParam, famId) {
  const metrics = getFamMetrics(famId, activeMetrics);
  if (!metrics.length) return;
  const w = parseInt(getFamParam ? getFamParam('vw') : 20) || 20;
  const COLORS = ['#e94560','#26a69a','#42a5f5','#ab47bc','#ffa726','#66bb6a','#ef5350'];
  const datasets = [];
  for (let mi = 0; mi < metrics.length; mi++) {
    const m = metrics[mi];
    const vals = metricVals(data, m);
    if (!vals.length || vals.length < w) continue;
    const n = vals.length;
    const pts = [];
    for (let i = w - 1; i < n; i++) {
      const window = vals.slice(i - w + 1, i + 1);
      const mean = window.reduce((a, b) => a + b, 0) / w;
      const s = Math.sqrt(window.reduce((a, v) => a + (v - mean) ** 2, 0) / w);
      pts.push({ x: data.candles[i].t, y: s });
    }
    const sMax = Math.max(...pts.map(p => p.y));
    const avgS = pts.reduce((a, p) => a + p.y, 0) / pts.length;
    const c = COLORS[mi % COLORS.length];
    datasets.push({
      label: `σ(${metricLabel(m)}, ${w})`, data: pts, showLine: true,
      borderColor: c, backgroundColor: mi === 0 ? c + '22' : 'transparent',
      fill: mi === 0, pointRadius: 0, borderWidth: mi === 0 ? 2 : 1,
      segment: { borderColor: ctx => {
        const v = ctx.p1.parsed.y;
        const t = v / sMax;
        return t > 0.7 ? '#ef5350' : t > 0.4 ? '#f0a030' : '#26a69a';
      }},
    });
  }
  if (!datasets.length) return;
  const titleMetrics = metrics.map(m => metricLabel(m)).join(', ');
  _chartInstances[famId] = _chart(ctx, {
    type: 'scatter',
    data: { datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        title: { display: true, text: `Volatilité: ${titleMetrics} (w=${w})`, color: '#888', font: { size: 11 } },
        legend: { labels: { color: '#888', font: { size: 9 } } },
      },
      scales: {
        x: { type: 'linear', ticks: { callback: v => new Date(v).toLocaleDateString('fr-FR', { timeZone: 'Europe/Paris', day: '2-digit', month: 'short' }), maxTicksLimit: 12, color: '#888', font: { size: 9 } }, grid: { color: '#16213e' }, title: { display: true, text: 'Date (Europe/Paris)', color: '#888', font: { size: 10 } } },
        y: { title: { display: true, text: 'σ', color: '#888', font: { size: 10 } }, ticks: { color: '#888', font: { size: 9 } }, grid: { color: '#16213e' } },
      },
    },
  });
}

function renderRegimeHist(ctx, canvas, data, activeMetrics, getFamParam, famId) {
  const metric = (getFamMetrics(famId, activeMetrics)[0] || activeMetrics[0]);
  const vals = metricVals(data, metric);
  if (!vals.length) return;
  const bins = 20;
  const min = Math.min(...vals), max = Math.max(...vals), bw = (max - min) / bins || 1;
  const bullHist = new Array(bins).fill(0), bearHist = new Array(bins).fill(0);
  let bullCount = 0, bearCount = 0;
  for (const c of data.candles) {
    const v = c.metrics[metric];
    const idx = Math.min(Math.floor((v - min) / bw), bins - 1);
    if (c.c >= c.o) { bullHist[idx]++; bullCount++; }
    else { bearHist[idx]++; bearCount++; }
  }
  const n = bullCount + bearCount;
  const bullPct = n > 0 ? (bullCount / n * 100).toFixed(1) : '—';
  const bearPct = n > 0 ? (bearCount / n * 100).toFixed(1) : '—';
  const labels = Array.from({length: bins}, (_, i) => (min + i * bw).toFixed(2));
  _chartInstances[famId] = _chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: 'Bull', data: bullHist, backgroundColor: 'rgba(38,166,154,0.6)', borderColor: '#26a69a', borderWidth: 1 },
        { label: 'Bear', data: bearHist, backgroundColor: 'rgba(239,83,80,0.6)', borderColor: '#ef5350', borderWidth: 1 },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        title: { display: true, text: `Regime histogram: ${metricLabel(metric)} · Bull ${bullPct}% Bear ${bearPct}%`, color: '#888', font: { size: 11 } },
        legend: { labels: { color: '#888', font: { size: 9 } } },
      },
      scales: {
        x: { stacked: false, ticks: { color: '#888', font: { size: 9 }, maxTicksLimit: 15 }, grid: { color: '#16213e' }, title: { display: true, text: metricLabel(metric), color: '#888', font: { size: 10 } } },
        y: { ticks: { color: '#888', font: { size: 9 } }, grid: { color: '#16213e' }, title: { display: true, text: 'Count', color: '#888', font: { size: 10 } } },
      },
    },
  });
}

function renderClusterScatter(ctx, canvas, data, activeMetrics) {
  const xKey = getParam('cxa') || activeMetrics[0];
  const yKey = getParam('cyb') || (activeMetrics.length > 1 ? activeMetrics[1] : activeMetrics[0]);
  const k = parseInt(getParam('ck')) || 3;
  const points = data.candles.map((c, i) => ({ x: c.metrics[xKey], y: c.metrics[yKey], i }));
  if (!points.length) return;
  // simple k-means
  const dims = 2;
  const n = points.length;
  let centroids = Array.from({length: k}, (_, i) => ({ x: points[Math.floor(i * n / k)].x, y: points[Math.floor(i * n / k)].y }));
  let labels = new Array(n).fill(0);
  for (let iter = 0; iter < 20; iter++) {
    // assign
    for (let i = 0; i < n; i++) {
      let best = 0, bestD = Infinity;
      for (let j = 0; j < k; j++) {
        const d = (points[i].x - centroids[j].x) ** 2 + (points[i].y - centroids[j].y) ** 2;
        if (d < bestD) { bestD = d; best = j; }
      }
      labels[i] = best;
    }
    // update
    const sum = Array.from({length: k}, () => ({ x: 0, y: 0, cnt: 0 }));
    for (let i = 0; i < n; i++) { sum[labels[i]].x += points[i].x; sum[labels[i]].y += points[i].y; sum[labels[i]].cnt++; }
    for (let j = 0; j < k; j++) { if (sum[j].cnt) { centroids[j].x = sum[j].x / sum[j].cnt; centroids[j].y = sum[j].y / sum[j].cnt; } }
  }
  const colors = ['#e94560', '#26a69a', '#f0a030', '#888', '#0f3460', '#ef5350', '#26a69a', '#e94560'];
  const datasets = Array.from({length: k}, (_, j) => ({
    label: `Cluster ${j + 1}`,
    data: points.filter((_, i) => labels[i] === j),
    backgroundColor: colors[j % colors.length],
    pointRadius: 2,
  }));
  datasets.push({
    label: 'Centroids', data: centroids, type: 'scatter',
    backgroundColor: '#fff', borderColor: '#fff', pointRadius: 5, pointStyle: 'cross',
  });
  window._vizChart = _chart(ctx, {
    type: 'scatter',
    data: { datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        title: { display: true, text: `k-means clusters (k=${k}): ${metricLabel(xKey)} vs ${metricLabel(yKey)}`, color: '#888', font: { size: 11 } },
        legend: { labels: { color: '#888', font: { size: 9 } } },
      },
      scales: {
        x: { title: { display: true, text: metricLabel(xKey), color: '#888', font: { size: 10 } }, ticks: { color: '#888', font: { size: 9 } }, grid: { color: '#16213e' } },
        y: { title: { display: true, text: metricLabel(yKey), color: '#888', font: { size: 10 } }, ticks: { color: '#888', font: { size: 9 } }, grid: { color: '#16213e' } },
      },
    },
  });
}

/* ─── Sort ─── */
let sortCol = 0, sortDir = -1;
function sortTable(th, col) {
  if (sortCol === col) sortDir *= -1;
  else { sortCol = col; sortDir = 1; }
  loadAnalyze();
}
function sortRawTable(col) {
  if (sortCol === col) sortDir *= -1;
  else { sortCol = col; sortDir = 1; }
  if (_cachedCandles) renderRawTable(_cachedCandles);
}

/* ─── Event listeners (null-guarded — DOM may not exist for analyze/rawdata) ─── */
try {
  var mcEl = document.getElementById('mcontrols');
  if (mcEl) mcEl.addEventListener('change', function() {
    if (document.querySelector('#analyze-view.view.active')) loadAnalyze();
  });
  var mbEl = document.getElementById('maxBars');
  if (mbEl) mbEl.addEventListener('change', function() {
    if (document.querySelector('#analyze-view.view.active')) loadAnalyze();
  });
} catch(e) { console.error('Event listener setup failed:', e); }

exchangeEl.addEventListener('change', filterSymbols);
symbolEl.addEventListener('change', function() { var t = document.querySelector('.tab.active'); if (t) switchTab(t.dataset.tab); });
timeframeEl.addEventListener('change', function() { var t = document.querySelector('.tab.active'); if (t) switchTab(t.dataset.tab); });
startDateEl.addEventListener('change', function() { var t = document.querySelector('.tab.active'); if (t) switchTab(t.dataset.tab); });
endDateEl.addEventListener('change', function() { var t = document.querySelector('.tab.active'); if (t) switchTab(t.dataset.tab); });

/* ─── Bootstrap (defensive — any crash here should NOT kill loadPairs) ─── */
window.addEventListener('error', function(e) {
  var errEl = document.getElementById('init-error-msg');
  if (errEl) errEl.textContent = 'Script error: ' + (e.message || 'unknown error');
  document.getElementById('init-error').style.display = 'block';
});
try {
  initChart();
} catch (e) {
  console.error('initChart failed:', e);
  var errEl = document.getElementById('init-error-msg');
  if (errEl) errEl.textContent = 'Chart init failed: ' + (e.message || 'unknown error');
  document.getElementById('init-error').style.display = 'block';
}
try {
  var savedInds = loadIndicatorSettings();
  if (savedInds && savedInds.length > 0) {
    for (var si = 0; si < savedInds.length; si++) activeIndicators.push(savedInds[si]);
  } else {
    activeIndicators.push({ name: "ichimoku", label: "Ichimoku Cloud", params: { tenkan: 9, kijun: 26, senkou: 52, color: "#26a69a" }, paneMode: "main" });
    activeIndicators.push({ name: "rsi", label: "RSI(14)", params: { period: 14, color: "#ab47bc" }, paneMode: "shared" });
  }
  renderIndChips();
} catch(e) { console.error('indicator init failed:', e); }
loadPairs().then(function() { loadAllData(); }).catch(function(e) {
  console.error('loadPairs error:', e);
});
</script>
</body>
</html>"""


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    return HTML
