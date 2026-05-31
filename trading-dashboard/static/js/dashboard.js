/* ===================================================================
   Trading Dashboard – dashboard.js
   Full indicator system with ~35 indicators, collapsible categories,
   per-chart state, live crypto ticking.
   =================================================================== */

let symbolList = [];
let charts = [];

const DEFAULT_SLOTS = [
    { symbol: 'AAPL', tf: '1d' },
    { symbol: 'TSLA', tf: '1d' },
    { symbol: 'BTC/USD', tf: '1h' },
    { symbol: 'NVDA', tf: '1d' },
    { symbol: 'ETH/USD', tf: '1h' },
    { symbol: 'SPY', tf: '1d' },
    { symbol: 'MSFT', tf: '1d' },
    { symbol: 'SOL/USD', tf: '1h' }
];

/* ── Indicator list – fetched from backend on init ─────────────── */
let INDICATORS_LIST = [];

/* Color palette for indicators */
const IND_COLORS = [
    '#2962FF','#FF6D00','#00C853','#FFD600','#D50000',
    '#AA00FF','#00BFA5','#FF4081','#64DD17','#00B8D4',
    '#F50057','#6200EA','#1DE9B6','#FFAB00','#304FFE'
];

let activePopoverChart = null;
let colorCounter = 0;

function nextColor() {
    return IND_COLORS[colorCounter++ % IND_COLORS.length];
}

/* ── Category collapse state (persisted in session) ──────────── */
const collapsedCategories = new Set();

/* ── Popover rendering ──────────────────────────────────────────── */

function renderPopover(chart) {
    const listEl = document.getElementById('indicator-list');
    if (!listEl) return;
    listEl.innerHTML = '';
    const searchInput = document.getElementById('indicator-search');
    const searchVal = searchInput ? searchInput.value.toLowerCase() : '';

    // Group by category
    const groups = {};
    INDICATORS_LIST.forEach(ind => {
        if (!ind.name.toLowerCase().includes(searchVal) &&
            !ind.id.toLowerCase().includes(searchVal)) return;
        if (!groups[ind.category]) groups[ind.category] = [];
        groups[ind.category].push(ind);
    });

    const categoryOrder = ['Overlap', 'Momentum', 'Volatility', 'Volume', 'Trend'];
    const orderedKeys = categoryOrder.filter(c => groups[c]);
    // Append any remaining categories
    Object.keys(groups).forEach(c => { if (!orderedKeys.includes(c)) orderedKeys.push(c); });

    for (const groupName of orderedKeys) {
        const inds = groups[groupName];
        const isCollapsed = collapsedCategories.has(groupName);

        // Category header (clickable to collapse)
        const groupEl = document.createElement('div');
        groupEl.className = 'popover-group' + (isCollapsed ? ' collapsed' : '');
        groupEl.innerHTML = `<span class="collapse-arrow">${isCollapsed ? '▸' : '▾'}</span> ${groupName} <span class="group-count">${inds.length}</span>`;
        groupEl.addEventListener('click', () => {
            if (collapsedCategories.has(groupName)) {
                collapsedCategories.delete(groupName);
            } else {
                collapsedCategories.add(groupName);
            }
            renderPopover(chart);
        });
        listEl.appendChild(groupEl);

        if (isCollapsed) continue;

        inds.forEach(ind => {
            const itemEl = document.createElement('label');
            itemEl.className = 'popover-item';

            const cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.checked = chart.activeIndicators.has(ind.id);
            cb.addEventListener('change', (e) => {
                e.stopPropagation();
                if (e.target.checked) chart.addIndicator(ind.id);
                else chart.removeIndicator(ind.id);
            });

            const txt = document.createElement('span');
            txt.textContent = ind.name;

            const badge = document.createElement('span');
            badge.className = 'render-badge';
            badge.textContent = ind.render === 'line' ? 'overlay' :
                               (ind.render === 'lines' || ind.render === 'lines_markers' || ind.render === 'fts' || ind.render === 'delta_vp') ? 'overlay' :
                               ind.render === 'osc' ? 'sub' :
                               ind.render === 'lines_osc' ? 'sub' : '';

            itemEl.appendChild(cb);
            itemEl.appendChild(txt);
            itemEl.appendChild(badge);
            listEl.appendChild(itemEl);
        });
    }
}

/* ── Global event setup ─────────────────────────────────────────── */

document.addEventListener('DOMContentLoaded', () => {
    document.addEventListener('click', (e) => {
        const popover = document.getElementById('indicators-popover');
        if (popover && !popover.classList.contains('hidden')) {
            if (!popover.contains(e.target) && !e.target.closest('.indicators-btn')) {
                popover.classList.add('hidden');
                activePopoverChart = null;
            }
        }
    });

    const searchInput = document.getElementById('indicator-search');
    if (searchInput) {
        searchInput.addEventListener('input', () => {
            if (activePopoverChart) renderPopover(activePopoverChart);
        });
    }
});

/* ── Hyperliquid WebSocket Manager ─────────────────────────────── */

class HyperliquidManager {
    constructor() {
        this.ws = null;
        this.subscriptions = new Map();
        this.reconnectTimeout = 1000;
        this.connect();
    }

    connect() {
        this.ws = new WebSocket("wss://api.hyperliquid.xyz/ws");
        this.ws.onopen = () => {
            console.log("Hyperliquid WS connected");
            this.reconnectTimeout = 1000;
            for (let [keyStr, data] of this.subscriptions.entries()) {
                const key = JSON.parse(keyStr);
                this.sendSub(key.coin, key.interval, true);
            }
        };
        this.ws.onmessage = (e) => {
            const msg = JSON.parse(e.data);
            if (msg.channel === "candle" && msg.data) {
                const s = msg.data.s;
                const i = msg.data.i;
                const c = msg.data;

                const open = parseFloat(c.o);
                const high = parseFloat(c.h);
                const low = parseFloat(c.l);
                const close = parseFloat(c.c);
                const time = Math.floor(c.t / 1000);

                const candleData = { time, open, high, low, close };

                for (let [keyStr, data] of this.subscriptions.entries()) {
                    const key = JSON.parse(keyStr);
                    if (key.coin === s && key.interval === i) {
                        data.callback(candleData);
                    }
                }
            }
        };
        this.ws.onclose = () => {
            console.log("Hyperliquid WS disconnected, reconnecting in", this.reconnectTimeout, "ms");
            setTimeout(() => this.connect(), this.reconnectTimeout);
            this.reconnectTimeout = Math.min(this.reconnectTimeout * 2, 30000);
        };
        this.ws.onerror = (e) => {
            console.error("Hyperliquid WS error", e);
        };
    }

    sendSub(coin, interval, isSub) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                method: isSub ? "subscribe" : "unsubscribe",
                subscription: { type: "candle", coin, interval }
            }));
        }
    }

    subscribe(chartId, symbol, timeframe, callback) {
        const coinMap = { "BTC/USD": "BTC", "ETH/USD": "ETH", "SOL/USD": "SOL" };
        const coin = coinMap[symbol];
        if (!coin) return;

        const interval = timeframe;
        const key = JSON.stringify({ chartId, coin, interval });
        this.subscriptions.set(key, { callback });
        this.sendSub(coin, interval, true);
    }

    unsubscribe(chartId, symbol, timeframe) {
        const coinMap = { "BTC/USD": "BTC", "ETH/USD": "ETH", "SOL/USD": "SOL" };
        const coin = coinMap[symbol];
        if (!coin) return;

        const interval = timeframe;
        const key = JSON.stringify({ chartId, coin, interval });

        if (this.subscriptions.has(key)) {
            this.subscriptions.delete(key);

            let inUse = false;
            for (let kStr of this.subscriptions.keys()) {
                const k = JSON.parse(kStr);
                if (k.coin === coin && k.interval === interval) {
                    inUse = true;
                    break;
                }
            }
            if (!inUse) {
                this.sendSub(coin, interval, false);
            }
        }
    }
}

const hlManager = new HyperliquidManager();

/* ── Series color maps for multi-series indicators ─────────────── */

const SERIES_COLORS = {
    // Bollinger / Donchian / Keltner bands
    upper:    'rgba(41, 98, 255, 0.5)',
    middle:   'rgba(41, 98, 255, 1)',
    lower:    'rgba(41, 98, 255, 0.5)',
    // MACD
    macd:     '#2962FF',
    signal:   '#FF6D00',
    hist:     null,  // colored per bar
    // Stochastic / StochRSI
    k:        '#2962FF',
    d:        '#FF6D00',
    // ADX
    adx:      '#FFD600',
    plus_di:  '#00C853',
    minus_di: '#D50000',
    // Aroon
    up:       '#00C853',
    down:     '#D50000',
    // Vortex
    plus:     '#00C853',
    minus:    '#D50000',
    // Ichimoku
    tenkan:   '#2962FF',
    kijun:    '#D50000',
    spanA:    'rgba(0, 200, 83, 0.5)',
    spanB:    'rgba(239, 83, 80, 0.5)',
    chikou:   '#AA00FF',
    // PSAR
    long:     '#00C853',
    short:    '#D50000',
};

/* ── FTS Custom Primitive for Filled Bands ────────────────────── */

class FTSFillRenderer {
    constructor(data) {
        this.data = data;
    }
    draw(target) {
        target.useBitmapCoordinateSpace((scope) => {
            if (!this.data || this.data.length < 2) return;
            const ctx = scope.context;
            ctx.save();
            ctx.scale(scope.horizontalPixelRatio, scope.verticalPixelRatio);
            
            try {
                for(let i = 0; i < this.data.length - 1; i++) {
                    const b1 = this.data[i];
                    const b2 = this.data[i+1];
                    if (b1.x === null || b2.x === null) continue;
                    if (b1.yF1 === null || b2.yF1 === null) continue;
                    if (b1.yF2 === null || b2.yF2 === null) continue;
                    if (b1.yF3 === null || b2.yF3 === null) continue;
                    if (b1.yTrail === null || b2.yTrail === null) continue;
                    
                    if (b1.state !== b2.state) continue;
                    
                    let colorF1F2 = b1.state === 'long' ? 'rgba(0, 200, 83, 0.4)' : 'rgba(213, 0, 0, 0.4)';
                    let colorF2F3 = b1.state === 'long' ? 'rgba(0, 200, 83, 0.25)' : 'rgba(213, 0, 0, 0.25)';
                    let colorF3L100 = b1.state === 'long' ? 'rgba(0, 200, 83, 0.15)' : 'rgba(213, 0, 0, 0.15)';

                    // F1 to F2
                    ctx.fillStyle = colorF1F2;
                    ctx.beginPath();
                    ctx.moveTo(b1.x, b1.yF1);
                    ctx.lineTo(b2.x, b2.yF1);
                    ctx.lineTo(b2.x, b2.yF2);
                    ctx.lineTo(b1.x, b1.yF2);
                    ctx.fill();

                    // F2 to F3
                    ctx.fillStyle = colorF2F3;
                    ctx.beginPath();
                    ctx.moveTo(b1.x, b1.yF2);
                    ctx.lineTo(b2.x, b2.yF2);
                    ctx.lineTo(b2.x, b2.yF3);
                    ctx.lineTo(b1.x, b1.yF3);
                    ctx.fill();

                    // F3 to Trail
                    ctx.fillStyle = colorF3L100;
                    ctx.beginPath();
                    ctx.moveTo(b1.x, b1.yF3);
                    ctx.lineTo(b2.x, b2.yF3);
                    ctx.lineTo(b2.x, b2.yTrail);
                    ctx.lineTo(b1.x, b1.yTrail);
                    ctx.fill();
                }
            } catch (e) {
                console.error("FTS Fill Renderer error:", e);
            }
            ctx.restore();
        });
    }
}

class FTSFillPaneView {
    constructor(source) {
        this.source = source;
    }
    update() {
        if (!this.source.chart || !this.source.series) return;
        const timeScale = this.source.chart.timeScale();
        const s = this.source.series;
        this.rendererData = this.source.data.map(d => {
            return {
                x: timeScale.timeToCoordinate(d.time),
                yF1: s.priceToCoordinate(d.f1),
                yF2: s.priceToCoordinate(d.f2),
                yF3: s.priceToCoordinate(d.f3),
                yTrail: s.priceToCoordinate(d.trail),
                state: d.state
            };
        });
    }
    renderer() {
        return new FTSFillRenderer(this.rendererData || []);
    }
}

class FTSFillPrimitive {
    constructor(data) {
        this.data = data;
        this.paneView = new FTSFillPaneView(this);
    }
    attached(param) {
        this.chart = param.chart;
        this.series = param.series;
        this.requestUpdate = param.requestUpdate;
    }
    detached() {}
    updateAllViews() {
        this.paneView.update();
    }
    paneViews() {
        return [this.paneView];
    }
}

/* ── Delta Volume Profile Custom Primitive ─────────────────────── */

function formatVolume(val) {
    if (val >= 1e9) return (val / 1e9).toFixed(2) + 'B';
    if (val >= 1e6) return (val / 1e6).toFixed(3) + 'M';
    if (val >= 1e3) return (val / 1e3).toFixed(val >= 1e5 ? 0 : val >= 1e4 ? 1 : 2) + 'K';
    return val.toFixed(0);
}

class DeltaVPRenderer {
    constructor(data) {
        this.data = data;
    }
    draw(target) {
        target.useBitmapCoordinateSpace((scope) => {
            if (!this.data) return;
            const ctx = scope.context;
            const d = this.data;
            ctx.save();
            ctx.scale(scope.horizontalPixelRatio, scope.verticalPixelRatio);

            try {
                const bins = d.bins;
                if (!bins || bins.length === 0) { ctx.restore(); return; }

                // Colors matching the original Pine Script exactly
                const colorPlus = '#c9805c';   // Volume +
                const colorMinus = '#5c8bc9';  // Volume -
                const pocPlusColor = '#2962FF'; // POC+ (blue)
                const pocMinusColor = '#da8300'; // POC- (orange)

                // --- Draw background boxes (span from lookback start to last bar) ---
                for (let i = 0; i < bins.length; i++) {
                    const b = bins[i];
                    if (b.yLow === null || b.yHigh === null) continue;

                    const y1 = Math.min(b.yHigh, b.yLow);
                    const y2 = Math.max(b.yHigh, b.yLow);
                    const h = y2 - y1;

                    // Sum for gradient intensity
                    const sumWidth = b.widthPlus + b.widthMinus;
                    // Grey gradient based on combined volume (like Pine Script col_sum)
                    const alpha = Math.min(0.45, 0.05 + (sumWidth / 60) * 0.4);

                    // Border color: POC+ = blue, POC- = orange, else subtle bg border
                    if (b.isPocPlus) {
                        ctx.strokeStyle = pocPlusColor;
                        ctx.lineWidth = 1.5;
                    } else if (b.isPocMinus) {
                        ctx.strokeStyle = pocMinusColor;
                        ctx.lineWidth = 1.5;
                    } else {
                        ctx.strokeStyle = `rgba(50, 50, 60, 0.5)`;
                        ctx.lineWidth = 0.5;
                    }

                    ctx.fillStyle = `rgba(120, 123, 134, ${alpha})`;
                    ctx.fillRect(d.xStart, y1, d.xEnd - d.xStart, h);
                    ctx.strokeRect(d.xStart, y1, d.xEnd - d.xStart, h);
                }

                // --- Draw right-side volume profile bars ---
                const centerX = d.xProfileCenter;
                const maxBarWidth = d.profileBarMaxWidth || 120;

                for (let i = 0; i < bins.length; i++) {
                    const b = bins[i];
                    if (b.yLow === null || b.yHigh === null) continue;

                    const y1 = Math.min(b.yHigh, b.yLow);
                    const y2 = Math.max(b.yHigh, b.yLow);
                    const h = Math.max(y2 - y1 - 1, 1);
                    const yTop = y1 + 0.5;

                    // Width proportional to normalized volume (0-200 scale)
                    const wPlus = (b.widthPlus / 200) * maxBarWidth;
                    const wMinus = (b.widthMinus / 200) * maxBarWidth;

                    // ---- Positive volume bar (extends LEFT from center) ----
                    if (b.widthPlus > 0) {
                        if (b.isPocPlus) {
                            ctx.fillStyle = pocPlusColor;
                        } else {
                            // Gradient from faded to solid based on relative volume
                            const ratio = b.widthPlus / 200;
                            const a = 0.25 + ratio * 0.75;
                            ctx.fillStyle = `rgba(201, 128, 92, ${a})`;
                        }
                        ctx.fillRect(centerX - wPlus, yTop, wPlus, h);

                        // Volume text inside the bar
                        const volText = '+' + formatVolume(b.volPlus);
                        ctx.font = '10px sans-serif';
                        ctx.fillStyle = '#e0e0e0';
                        ctx.textAlign = 'right';
                        ctx.textBaseline = 'middle';
                        ctx.fillText(volText, centerX - 3, yTop + h / 2);
                    }

                    // ---- Negative volume bar (extends RIGHT from center) ----
                    if (b.widthMinus > 0) {
                        if (b.isPocMinus) {
                            ctx.fillStyle = pocMinusColor;
                        } else {
                            const ratio = b.widthMinus / 200;
                            const a = 0.25 + ratio * 0.75;
                            ctx.fillStyle = `rgba(92, 139, 201, ${a})`;
                        }
                        ctx.fillRect(centerX, yTop, wMinus, h);

                        // Volume text inside the bar
                        const volText = '-' + formatVolume(b.volMinus);
                        ctx.font = '10px sans-serif';
                        ctx.fillStyle = '#e0e0e0';
                        ctx.textAlign = 'left';
                        ctx.textBaseline = 'middle';
                        ctx.fillText(volText, centerX + 3, yTop + h / 2);
                    }
                }

                // --- Delta label at top ---
                const topY = d.yPriceMax;
                if (topY !== null) {
                    const deltaText = 'Delta: ' + d.delta.toFixed(2) + '%';
                    const labelW = ctx.measureText(deltaText).width + 16;
                    const labelH = 20;
                    const labelX = centerX - labelW / 2;
                    const labelY = topY - labelH - 8;

                    ctx.fillStyle = d.delta > 0 ? colorPlus : colorMinus;
                    // Rounded rect
                    const r = 4;
                    ctx.beginPath();
                    ctx.moveTo(labelX + r, labelY);
                    ctx.lineTo(labelX + labelW - r, labelY);
                    ctx.arcTo(labelX + labelW, labelY, labelX + labelW, labelY + r, r);
                    ctx.lineTo(labelX + labelW, labelY + labelH - r);
                    ctx.arcTo(labelX + labelW, labelY + labelH, labelX + labelW - r, labelY + labelH, r);
                    ctx.lineTo(labelX + r, labelY + labelH);
                    ctx.arcTo(labelX, labelY + labelH, labelX, labelY + labelH - r, r);
                    ctx.lineTo(labelX, labelY + r);
                    ctx.arcTo(labelX, labelY, labelX + r, labelY, r);
                    ctx.fill();

                    // Arrow/triangle pointing down
                    ctx.beginPath();
                    ctx.moveTo(centerX - 5, labelY + labelH);
                    ctx.lineTo(centerX + 5, labelY + labelH);
                    ctx.lineTo(centerX, labelY + labelH + 5);
                    ctx.fill();

                    ctx.font = 'bold 11px sans-serif';
                    ctx.fillStyle = '#e0e0e0';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText(deltaText, labelX + labelW / 2, labelY + labelH / 2);
                }

                // --- Total label at bottom ---
                const bottomY = d.yPriceMin;
                if (bottomY !== null) {
                    const totalText = 'Total: ' + formatVolume(d.totalVol);
                    const labelW = ctx.measureText(totalText).width + 16;
                    const labelH = 20;
                    const labelX = centerX - labelW / 2;
                    const labelY = bottomY + 8;

                    ctx.fillStyle = '#666';
                    const r = 4;
                    ctx.beginPath();
                    ctx.moveTo(labelX + r, labelY);
                    ctx.lineTo(labelX + labelW - r, labelY);
                    ctx.arcTo(labelX + labelW, labelY, labelX + labelW, labelY + r, r);
                    ctx.lineTo(labelX + labelW, labelY + labelH - r);
                    ctx.arcTo(labelX + labelW, labelY + labelH, labelX + labelW - r, labelY + labelH, r);
                    ctx.lineTo(labelX + r, labelY + labelH);
                    ctx.arcTo(labelX, labelY + labelH, labelX, labelY + labelH - r, r);
                    ctx.lineTo(labelX, labelY + r);
                    ctx.arcTo(labelX, labelY, labelX + r, labelY, r);
                    ctx.fill();

                    // Arrow/triangle pointing up
                    ctx.beginPath();
                    ctx.moveTo(centerX - 5, labelY);
                    ctx.lineTo(centerX + 5, labelY);
                    ctx.lineTo(centerX, labelY - 5);
                    ctx.fill();

                    ctx.font = 'bold 11px sans-serif';
                    ctx.fillStyle = '#e0e0e0';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText(totalText, labelX + labelW / 2, labelY + labelH / 2);
                }

            } catch (e) {
                console.error('DeltaVP Renderer error:', e);
            }
            ctx.restore();
        });
    }
}

class DeltaVPPaneView {
    constructor(source) {
        this.source = source;
    }
    update() {
        if (!this.source.chart || !this.source.series) return;
        const ts = this.source.chart.timeScale();
        const s = this.source.series;
        const profile = this.source.profileData;
        if (!profile || !profile.bins) return;

        // Ensure we have valid x-coordinates
        const chartWidth = ts.width();
        const xStart = ts.timeToCoordinate(profile.startTime) || 0;
        const xEnd = ts.timeToCoordinate(profile.endTime) || (chartWidth - 100);

        // Position the profile in the future space, just like Pine Script's `bar_index + 50`.
        // We use the exact bar spacing from the time scale.
        const barSpacing = ts.options().barSpacing || 6;
        const xProfileCenter = xEnd + (30 * barSpacing);
        const profileBarMaxWidth = Math.max(60, 25 * barSpacing);

        const bins = profile.bins.map(b => ({
            ...b,
            yLow: s.priceToCoordinate(b.low),
            yHigh: s.priceToCoordinate(b.high),
        }));

        this.rendererData = {
            xStart,
            xEnd,
            xProfileCenter,
            profileBarMaxWidth,
            bins,
            delta: profile.delta,
            totalVol: profile.totalVol,
            yPriceMax: s.priceToCoordinate(profile.priceMax),
            yPriceMin: s.priceToCoordinate(profile.priceMin),
        };
    }
    renderer() {
        return new DeltaVPRenderer(this.rendererData || null);
    }
}

class DeltaVPPrimitive {
    constructor(profileData) {
        this.profileData = profileData;
        this.paneView = new DeltaVPPaneView(this);
    }
    attached(param) {
        this.chart = param.chart;
        this.series = param.series;
        this.requestUpdate = param.requestUpdate;
    }
    detached() {}
    updateAllViews() {
        this.paneView.update();
    }
    paneViews() {
        return [this.paneView];
    }
}

/* ── TradingChart class ────────────────────────────────────────── */

class TradingChart {
    static nextId = 1;
    constructor(panelElement, symbol, timeframe) {
        this.id = TradingChart.nextId++;
        this.panel = panelElement;
        this.symbol = symbol;
        this.timeframe = timeframe;
        this.canvasContainer = this.panel.querySelector('.chart-canvas');
        this.currentCandle = null;
        this.badge = this.panel.querySelector('.live-price-badge');

        this.activeIndicators = new Map();  // id -> { config, series[], color }
        this.indicatorsBtn = this.panel.querySelector('.indicators-btn');
        this.activeIndContainer = this.panel.querySelector('.active-indicators');
        this.chipsContainer = this.panel.querySelector('.chips-container');
        this.clearAllBtn = this.panel.querySelector('.clear-all-indicators');

        this.chart = LightweightCharts.createChart(this.canvasContainer, {
            layout: {
                background: { type: 'solid', color: '#0d0d0f' },
                textColor: '#e0e0e0',
            },
            grid: {
                vertLines: { color: '#1a1a24' },
                horzLines: { color: '#1a1a24' },
            },
            crosshair: {
                mode: LightweightCharts.CrosshairMode.Normal,
            },
            rightPriceScale: {
                borderColor: '#262633',
            },
            timeScale: {
                borderColor: '#262633',
                timeVisible: true,
                secondsVisible: false,
                rightOffset: 45, // Provide empty space on the right for indicators like Delta VP
            },
        });

        this.candleSeries = this.chart.addCandlestickSeries({
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderVisible: false,
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350'
        });

        this.setupListeners();
        this.resizeObserver = new ResizeObserver(() => this.resize());
        this.resizeObserver.observe(this.canvasContainer);

        this.load();
    }

    setupListeners() {
        const select = this.panel.querySelector('.symbol-select');
        if (select) {
            select.value = this.symbol;
            select.addEventListener('change', (e) => {
                this.setSymbol(e.target.value);
            });
        }

        const tfButtons = this.panel.querySelectorAll('.timeframe-controls button');
        tfButtons.forEach(btn => {
            if (btn.dataset.tf === this.timeframe) btn.classList.add('active');
            btn.addEventListener('click', (e) => {
                this.setTimeframe(e.target.dataset.tf);
            });
        });

        if (this.indicatorsBtn) {
            this.indicatorsBtn.addEventListener('click', (e) => {
                const popover = document.getElementById('indicators-popover');
                if (activePopoverChart === this && !popover.classList.contains('hidden')) {
                    popover.classList.add('hidden');
                    activePopoverChart = null;
                    return;
                }
                activePopoverChart = this;
                const search = document.getElementById('indicator-search');
                if (search) search.value = '';
                renderPopover(this);

                const rect = this.indicatorsBtn.getBoundingClientRect();
                popover.style.left = rect.left + 'px';
                popover.style.top = (rect.bottom + window.scrollY + 4) + 'px';
                popover.classList.remove('hidden');
            });
        }

        if (this.clearAllBtn) {
            this.clearAllBtn.addEventListener('click', (e) => {
                e.preventDefault();
                const ids = Array.from(this.activeIndicators.keys());
                ids.forEach(id => this.removeIndicator(id));
            });
        }
    }

    renderChips() {
        if (!this.chipsContainer) return;
        this.chipsContainer.innerHTML = '';
        if (this.activeIndicators.size > 0) {
            if (this.activeIndContainer) this.activeIndContainer.style.display = 'flex';
        } else {
            if (this.activeIndContainer) this.activeIndContainer.style.display = 'none';
        }

        for (const [id, indData] of this.activeIndicators.entries()) {
            const chip = document.createElement('div');
            chip.className = 'chip';
            if (indData.color) {
                chip.style.borderLeft = `3px solid ${indData.color}`;
            }
            chip.innerHTML = `<span>${indData.config.name}</span><span class="chip-del">✕</span>`;
            chip.querySelector('.chip-del').addEventListener('click', () => {
                this.removeIndicator(id);
                if (activePopoverChart === this) renderPopover(this);
            });
            this.chipsContainer.appendChild(chip);
        }
    }

    /* ── Draw a single indicator ─────────────────────────────────── */

    async drawIndicator(id) {
        const config = INDICATORS_LIST.find(i => i.id === id);
        if (!config) return;

        try {
            let url = `/api/indicator?symbol=${encodeURIComponent(this.symbol)}&timeframe=${this.timeframe}&indicator=${config.id}`;
            // Add default params
            if (config.params) {
                for (const [k, v] of Object.entries(config.params)) {
                    url += `&${k}=${v}`;
                }
            }
            const res = await fetch(url);
            const result = await res.json();

            if (result.error || !result.data || !result.data.length) return;

            // Remove old series if re-drawing
            if (this.activeIndicators.has(id)) {
                const oldData = this.activeIndicators.get(id);
                oldData.chartSeries.forEach(s => {
                    try { this.chart.removeSeries(s); } catch (e) {}
                });
            }

            const render = result.render;
            const data = result.data;
            let chartSeries = [];
            const color = this.activeIndicators.has(id)
                ? this.activeIndicators.get(id).color
                : nextColor();

            // ── line: single overlay line ────────────────────────────
            if (render === 'line') {
                const line = this.chart.addLineSeries({ color: color, lineWidth: 2 });
                line.setData(data);
                chartSeries = [line];
            }

            // ── lines: multiple overlay lines (bands, channels, etc) ─
            else if (render === 'lines' || render === 'lines_markers' || render === 'fts') {
                if (config.id === 'supertrend') {
                    chartSeries = this._drawSupertrend(data, color);
                } else if (config.id === 'psar') {
                    chartSeries = this._drawPSAR(data);
                } else if (config.id === 'ichimoku') {
                    chartSeries = this._drawIchimoku(data);
                } else if (config.id === 'fts') {
                    chartSeries = this._drawFTS(data);
                } else {
                    // Generic band: upper, middle, lower
                    chartSeries = this._drawBands(data, config);
                }
            }

            // ── delta_vp: Delta Volume Profile overlay ─────────────
            else if (render === 'delta_vp') {
                chartSeries = this._drawDeltaVP(data, color);
            }

            // ── osc: single oscillator line in sub-pane ──────────────
            else if (render === 'osc') {
                chartSeries = this._drawOscillator(data, config, id, color);
            }

            // ── lines_osc: multi-line oscillator in sub-pane ─────────
            else if (render === 'lines_osc') {
                chartSeries = this._drawLinesOsc(data, config, id);
            }

            // Adjust main price scale to make room for sub-panes
            this._adjustScaleMargins();

            const entry = this.activeIndicators.get(id) || {};
            this.activeIndicators.set(id, {
                config: config,
                chartSeries: chartSeries,
                color: color,
                render: render,
            });
            this.renderChips();

        } catch (e) {
            console.error("Failed to load indicator", id, e);
        }
    }

    /* ── Specific drawing helpers ─────────────────────────────────── */

    _drawSupertrend(data, fallbackColor) {
        const upData = [];
        const downData = [];
        const markers = [];
        data.forEach(d => {
            if (d.direction === 1) {
                upData.push({ time: d.time, value: d.value });
                downData.push({ time: d.time, value: NaN });
            } else {
                downData.push({ time: d.time, value: d.value });
                upData.push({ time: d.time, value: NaN });
            }
            if (d.buySignal) {
                markers.push({ time: d.time, position: 'belowBar', color: '#00C853', shape: 'arrowUp', text: 'Buy', size: 1 });
            }
            if (d.sellSignal) {
                markers.push({ time: d.time, position: 'aboveBar', color: '#D50000', shape: 'arrowDown', text: 'Sell', size: 1 });
            }
        });
        const upLine = this.chart.addLineSeries({ color: '#00C853', lineWidth: 2, lastValueVisible: false, priceLineVisible: false });
        const downLine = this.chart.addLineSeries({ color: '#D50000', lineWidth: 2, lastValueVisible: false, priceLineVisible: false });
        upLine.setData(upData.filter(d => !isNaN(d.value)));
        downLine.setData(downData.filter(d => !isNaN(d.value)));
        
        if (markers.length > 0) {
            this.candleSeries.setMarkers(markers);
        }
        
        return [upLine, downLine];
    }

    _drawFTS(data) {
        const series = [];
        const markers = [];
        
        // Define lines for Green (Long) and Red (Short)
        const opts = { lineWidth: 1, lastValueVisible: false, priceLineVisible: false };
        const exOpts = { lineWidth: 2, lineStyle: 3, lastValueVisible: false, priceLineVisible: false };
        const trailOpts = { lineWidth: 2, lastValueVisible: false, priceLineVisible: false };

        const trailG = this.chart.addLineSeries({ color: '#00C853', ...trailOpts });
        const trailR = this.chart.addLineSeries({ color: '#D50000', ...trailOpts });
        const exG = this.chart.addLineSeries({ color: '#00E676', ...exOpts });
        const exR = this.chart.addLineSeries({ color: '#FF00FF', ...exOpts });
        const f1G = this.chart.addLineSeries({ color: '#00C853', ...opts });
        const f1R = this.chart.addLineSeries({ color: '#D50000', ...opts });
        const f2G = this.chart.addLineSeries({ color: '#00C853', ...opts });
        const f2R = this.chart.addLineSeries({ color: '#D50000', ...opts });
        const f3G = this.chart.addLineSeries({ color: '#00C853', ...opts });
        const f3R = this.chart.addLineSeries({ color: '#D50000', ...opts });

        const dTrailG = [], dTrailR = [];
        const dExG = [], dExR = [];
        const dF1G = [], dF1R = [];
        const dF2G = [], dF2R = [];
        const dF3G = [], dF3R = [];

        data.forEach(d => {
            if (d.trend === 1) {
                dTrailG.push({ time: d.time, value: d.trail }); dTrailR.push({ time: d.time });
                dExG.push({ time: d.time, value: d.ex });       dExR.push({ time: d.time });
                dF1G.push({ time: d.time, value: d.f1 });       dF1R.push({ time: d.time });
                dF2G.push({ time: d.time, value: d.f2 });       dF2R.push({ time: d.time });
                dF3G.push({ time: d.time, value: d.f3 });       dF3R.push({ time: d.time });
            } else {
                dTrailR.push({ time: d.time, value: d.trail }); dTrailG.push({ time: d.time });
                dExR.push({ time: d.time, value: d.ex });       dExG.push({ time: d.time });
                dF1R.push({ time: d.time, value: d.f1 });       dF1G.push({ time: d.time });
                dF2R.push({ time: d.time, value: d.f2 });       dF2G.push({ time: d.time });
                dF3R.push({ time: d.time, value: d.f3 });       dF3G.push({ time: d.time });
            }

            // Markers
            if (d.l1) markers.push({ time: d.time, position: 'belowBar', color: '#FFEB3B', shape: 'arrowUp', text: 'L1', size: 0 });
            if (d.l2) markers.push({ time: d.time, position: 'belowBar', color: '#FFEB3B', shape: 'arrowUp', text: 'L2', size: 0 });
            if (d.l3) markers.push({ time: d.time, position: 'belowBar', color: '#FFEB3B', shape: 'arrowUp', text: 'L3', size: 0 });
            
            if (d.s1) markers.push({ time: d.time, position: 'aboveBar', color: '#9C27B0', shape: 'arrowDown', text: 'S1', size: 0 });
            if (d.s2) markers.push({ time: d.time, position: 'aboveBar', color: '#9C27B0', shape: 'arrowDown', text: 'S2', size: 0 });
            if (d.s3) markers.push({ time: d.time, position: 'aboveBar', color: '#9C27B0', shape: 'arrowDown', text: 'S3', size: 0 });
        });

        trailG.setData(dTrailG); trailR.setData(dTrailR);
        exG.setData(dExG);       exR.setData(dExR);
        f1G.setData(dF1G);       f1R.setData(dF1R);
        f2G.setData(dF2G);       f2R.setData(dF2R);
        f3G.setData(dF3G);       f3R.setData(dF3R);

        if (markers.length > 0) {
            markers.sort((a, b) => a.time - b.time);
            this.candleSeries.setMarkers(markers);
        }

        // Attach custom fill primitive to one of the series so it draws underneath
        try {
            const fillPrimitive = new FTSFillPrimitive(data);
            trailG.attachPrimitive(fillPrimitive);
        } catch (e) {
            console.error("Failed to attach fill primitive:", e);
        }

        series.push(trailG, trailR, exG, exR, f1G, f1R, f2G, f2R, f3G, f3R);
        return series;
    }

    _drawDeltaVP(data, fallbackColor) {
        // data is a single-element array with the profile object
        if (!data || data.length === 0) return [];
        const profile = data[0];
        if (!profile || !profile.bins || profile.bins.length === 0) return [];

        try {
            const primitive = new DeltaVPPrimitive(profile);
            // Attach directly to candleSeries so it shares the exact time scale
            this.candleSeries.attachPrimitive(primitive);
            
            // Return a mock series object so removeIndicator can detach it safely
            return [{
                isPrimitive: true,
                primitive: primitive
            }];
        } catch (e) {
            console.error('Failed to attach DeltaVP primitive:', e);
        }

        return [];
    }

    _drawPSAR(data) {
        // Draw PSAR as dots using marker-like approach via two line series
        const longData = data.filter(d => d.long !== null).map(d => ({ time: d.time, value: d.long }));
        const shortData = data.filter(d => d.short !== null).map(d => ({ time: d.time, value: d.short }));

        const series = [];
        if (longData.length) {
            const ls = this.chart.addLineSeries({
                color: SERIES_COLORS.long, lineWidth: 1, lineStyle: 3,
                crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false
            });
            ls.setData(longData);
            series.push(ls);
        }
        if (shortData.length) {
            const ss = this.chart.addLineSeries({
                color: SERIES_COLORS.short, lineWidth: 1, lineStyle: 3,
                crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false
            });
            ss.setData(shortData);
            series.push(ss);
        }
        return series;
    }

    _drawIchimoku(data) {
        const series = [];
        const lineConfigs = [
            { key: 'tenkan', color: SERIES_COLORS.tenkan, width: 1 },
            { key: 'kijun',  color: SERIES_COLORS.kijun,  width: 1 },
            { key: 'spanA',  color: SERIES_COLORS.spanA,  width: 1 },
            { key: 'spanB',  color: SERIES_COLORS.spanB,  width: 1 },
            { key: 'chikou', color: SERIES_COLORS.chikou,  width: 1 },
        ];
        for (const lc of lineConfigs) {
            const lineData = data
                .filter(d => d[lc.key] !== null && d[lc.key] !== undefined)
                .map(d => ({ time: d.time, value: d[lc.key] }));
            if (lineData.length) {
                const ls = this.chart.addLineSeries({
                    color: lc.color, lineWidth: lc.width,
                    lastValueVisible: false, priceLineVisible: false
                });
                ls.setData(lineData);
                series.push(ls);
            }
        }
        return series;
    }

    _drawBands(data, config) {
        const seriesKeys = config.series || ['lower', 'middle', 'upper'];
        const bandColors = ['rgba(41, 98, 255, 0.4)', 'rgba(41, 98, 255, 1)', 'rgba(41, 98, 255, 0.4)'];
        const series = [];
        seriesKeys.forEach((key, idx) => {
            const lineData = data
                .filter(d => d[key] !== null && d[key] !== undefined)
                .map(d => ({ time: d.time, value: d[key] }));
            if (lineData.length) {
                const ls = this.chart.addLineSeries({
                    color: bandColors[idx % bandColors.length],
                    lineWidth: idx === 1 ? 2 : 1,
                    lastValueVisible: false, priceLineVisible: false
                });
                ls.setData(lineData);
                series.push(ls);
            }
        });
        return series;
    }

    _drawOscillator(data, config, id, color) {
        const line = this.chart.addLineSeries({
            color: color,
            lineWidth: 2,
            priceScaleId: id,
            lastValueVisible: false,
            priceLineVisible: false,
        });
        line.setData(data);

        const series = [line];

        // Draw guide lines
        if (config.guides) {
            config.guides.forEach(level => {
                const guideData = [
                    { time: data[0].time, value: level },
                    { time: data[data.length - 1].time, value: level }
                ];
                const guideLine = this.chart.addLineSeries({
                    color: 'rgba(255,255,255,0.15)',
                    lineWidth: 1,
                    lineStyle: 2,
                    priceScaleId: id,
                    lastValueVisible: false,
                    priceLineVisible: false,
                    crosshairMarkerVisible: false,
                });
                guideLine.setData(guideData);
                series.push(guideLine);
            });
        }

        return series;
    }

    _drawLinesOsc(data, config, id) {
        const seriesKeys = config.series || [];
        const series = [];

        seriesKeys.forEach(key => {
            if (key === 'hist') {
                // Draw histogram for MACD
                const histSeries = this.chart.addHistogramSeries({
                    priceScaleId: id,
                    lastValueVisible: false,
                    priceLineVisible: false,
                });
                histSeries.setData(data.map(d => ({
                    time: d.time,
                    value: d.hist,
                    color: (d.hist !== null && d.hist >= 0) ? 'rgba(38, 166, 154, 0.5)' : 'rgba(239, 83, 80, 0.5)'
                })).filter(d => d.value !== null));
                series.push(histSeries);
            } else {
                const lineColor = SERIES_COLORS[key] || nextColor();
                const lineSeries = this.chart.addLineSeries({
                    color: lineColor,
                    lineWidth: 2,
                    priceScaleId: id,
                    lastValueVisible: false,
                    priceLineVisible: false,
                });
                lineSeries.setData(
                    data.filter(d => d[key] !== null && d[key] !== undefined)
                        .map(d => ({ time: d.time, value: d[key] }))
                );
                series.push(lineSeries);
            }
        });

        // Draw guide lines
        if (config.guides && data.length > 1) {
            config.guides.forEach(level => {
                const guideData = [
                    { time: data[0].time, value: level },
                    { time: data[data.length - 1].time, value: level }
                ];
                const guideLine = this.chart.addLineSeries({
                    color: 'rgba(255,255,255,0.15)',
                    lineWidth: 1,
                    lineStyle: 2,
                    priceScaleId: id,
                    lastValueVisible: false,
                    priceLineVisible: false,
                    crosshairMarkerVisible: false,
                });
                guideLine.setData(guideData);
                series.push(guideLine);
            });
        }

        return series;
    }

    /* ── Scale margin management ──────────────────────────────────── */

    _adjustScaleMargins() {
        const oscIndicators = Array.from(this.activeIndicators.entries())
            .filter(([id, d]) => d.render === 'osc' || d.render === 'lines_osc');
            
        const numOsc = oscIndicators.length;
        
        if (numOsc === 0) {
            this.chart.priceScale('right').applyOptions({
                scaleMargins: { top: 0.1, bottom: 0.1 },
            });
            return;
        }

        // Allocate up to 25% height for each oscillator. Max combined space = 65% of chart height.
        const oscSpace = Math.min(0.65, numOsc * 0.25); 
        const paneHeight = oscSpace / numOsc;

        // Main chart margins
        this.chart.priceScale('right').applyOptions({
            scaleMargins: { top: 0.1, bottom: oscSpace + 0.05 },
        });

        // Set margins for each oscillator price scale to stack them vertically
        oscIndicators.forEach(([id, d], index) => {
            const topMargin = 1.0 - oscSpace + (index * paneHeight);
            // Leave a tiny gap between oscillators
            const bottomMargin = Math.max(0, oscSpace - ((index + 1) * paneHeight) + 0.02);

            try {
                this.chart.priceScale(id).applyOptions({
                    scaleMargins: { top: topMargin, bottom: bottomMargin },
                });
            } catch (e) {
                // Ignore if priceScale not yet initialized
            }
        });
    }

    /* ── Add / Remove ─────────────────────────────────────────────── */

    addIndicator(id) {
        if (!this.activeIndicators.has(id)) {
            const config = INDICATORS_LIST.find(i => i.id === id);
            if (!config) return;
            this.activeIndicators.set(id, {
                config: config,
                chartSeries: [],
                color: nextColor(),
                render: config.render,
            });
            this.renderChips();
            this.drawIndicator(id);
        }
    }

    removeIndicator(id) {
        if (this.activeIndicators.has(id)) {
            const indData = this.activeIndicators.get(id);
            if (indData.chartSeries) {
                indData.chartSeries.forEach(s => {
                    try { 
                        if (s.isPrimitive) {
                            this.candleSeries.detachPrimitive(s.primitive);
                        } else {
                            this.chart.removeSeries(s); 
                        }
                    } catch (e) {}
                });
            }
            this.activeIndicators.delete(id);
            this._adjustScaleMargins();
            this.renderChips();
        }
    }

    /* ── Timeframe / Symbol ───────────────────────────────────────── */

    updateActiveTimeframe() {
        const btns = this.panel.querySelectorAll('.timeframe-controls button');
        btns.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tf === this.timeframe);
        });
    }

    setSymbol(sym) {
        if (["BTC/USD", "ETH/USD", "SOL/USD"].includes(this.symbol)) {
            hlManager.unsubscribe(this.id, this.symbol, this.timeframe);
        }
        this.symbol = sym;
        this.load();
    }

    setTimeframe(tf) {
        if (["BTC/USD", "ETH/USD", "SOL/USD"].includes(this.symbol)) {
            hlManager.unsubscribe(this.id, this.symbol, this.timeframe);
        }
        this.timeframe = tf;
        this.updateActiveTimeframe();
        this.load();
    }

    /* ── Load candles + re-draw active indicators ────────────────── */

    async load() {
        try {
            const res = await fetch(`/api/bars?symbol=${encodeURIComponent(this.symbol)}&timeframe=${this.timeframe}&limit=500`);
            const data = await res.json();
            if (Array.isArray(data)) {
                this.candleSeries.setData(data);
                if (data.length > 0) {
                    this.currentCandle = { ...data[data.length - 1] };
                    this.updateBadge(this.currentCandle.close, this.currentCandle.close);
                } else {
                    this.currentCandle = null;
                }
                this.chart.timeScale().fitContent();

                if (["BTC/USD", "ETH/USD", "SOL/USD"].includes(this.symbol)) {
                    hlManager.subscribe(this.id, this.symbol, this.timeframe, (candleData) => {
                        this.applyHyperliquidCandle(candleData);
                    });
                }

                // Re-draw all active indicators
                for (const id of this.activeIndicators.keys()) {
                    this.drawIndicator(id);
                }
            } else {
                console.error("Failed to load data for", this.symbol, data);
            }
        } catch (e) {
            console.error("Error fetching data:", e);
        }
    }

    updateBadge(price, oldPrice) {
        if (!this.badge) return;
        this.badge.textContent = price.toFixed(2);
        this.badge.classList.remove('up', 'down');
        void this.badge.offsetWidth; // Force reflow
        if (price > oldPrice) {
            this.badge.classList.add('up');
        } else if (price < oldPrice) {
            this.badge.classList.add('down');
        }
    }

    applyTick(price, tickTime) {
        if (!this.currentCandle) return;

        const tfMap = {
            "1m": 60, "5m": 300, "15m": 900, "1h": 3600, "1d": 86400
        };
        const tfSeconds = tfMap[this.timeframe] || 86400;

        const candleStart = Math.floor(tickTime / tfSeconds) * tfSeconds;
        const oldPrice = this.currentCandle.close;

        if (candleStart === this.currentCandle.time) {
            this.currentCandle.close = price;
            this.currentCandle.high = Math.max(this.currentCandle.high, price);
            this.currentCandle.low = Math.min(this.currentCandle.low, price);
            this.candleSeries.update(this.currentCandle);
        } else if (candleStart > this.currentCandle.time) {
            const newCandle = {
                time: candleStart,
                open: price,
                high: price,
                low: price,
                close: price
            };
            this.candleSeries.update(newCandle);
            this.currentCandle = newCandle;

            for (const id of this.activeIndicators.keys()) {
                this.drawIndicator(id);
            }
        }

        this.updateBadge(price, oldPrice);
    }

    applyHyperliquidCandle(candleData) {
        const isNewCandle = this.currentCandle && candleData.time > this.currentCandle.time;
        this.candleSeries.update(candleData);
        const oldPrice = this.currentCandle ? this.currentCandle.close : candleData.open;
        this.currentCandle = candleData;
        this.updateBadge(candleData.close, oldPrice);

        if (isNewCandle) {
            for (const id of this.activeIndicators.keys()) {
                this.drawIndicator(id);
            }
        }
    }

    resize() {
        const rect = this.canvasContainer.getBoundingClientRect();
        this.chart.applyOptions({
            width: rect.width,
            height: rect.height
        });
    }

    destroy() {
        if (["BTC/USD", "ETH/USD", "SOL/USD"].includes(this.symbol)) {
            hlManager.unsubscribe(this.id, this.symbol, this.timeframe);
        }
        this.resizeObserver.disconnect();
        this.chart.remove();
    }
}

/* ── Symbol dropdowns ─────────────────────────────────────────── */

async function populateSymbolDropdowns() {
    try {
        const res = await fetch('/api/symbols');
        symbolList = await res.json();
    } catch (e) {
        console.error("Failed to fetch symbols", e);
    }
}

function createSelectOptions(selectElement) {
    selectElement.innerHTML = '';
    symbolList.forEach(sym => {
        const opt = document.createElement('option');
        opt.value = sym.id;
        opt.textContent = `${sym.id} - ${sym.name}`;
        selectElement.appendChild(opt);
    });
}

/* ── Fetch indicator list from backend ────────────────────────── */

async function fetchIndicatorList() {
    console.log("Fetching indicator list from /api/indicator-list ...");
    try {
        const res = await fetch('/api/indicator-list');
        if (!res.ok) {
            console.error(`Failed to fetch indicators: HTTP ${res.status} ${res.statusText}`);
        }
        INDICATORS_LIST = await res.json();
        console.log(`Loaded ${INDICATORS_LIST.length} indicators from backend:`, INDICATORS_LIST);
    } catch (e) {
        console.error("Network or parsing error fetching indicator list:", e);
    }
}

/* ── Layout ───────────────────────────────────────────────────── */

async function setLayout(n) {
    const grid = document.getElementById('chart-grid');
    grid.className = `layout-${n}`;

    charts.forEach(c => c.destroy());
    charts = [];
    grid.innerHTML = '';

    const template = document.getElementById('panel-template');

    for (let i = 0; i < n; i++) {
        const clone = template.content.cloneNode(true);
        const panel = clone.querySelector('.chart-panel');
        const select = clone.querySelector('.symbol-select');
        createSelectOptions(select);

        const config = DEFAULT_SLOTS[i] || DEFAULT_SLOTS[0];
        grid.appendChild(clone);

        const tc = new TradingChart(panel, config.symbol, config.tf);
        charts.push(tc);
    }
}

/* ── Init ─────────────────────────────────────────────────────── */

async function init() {
    await populateSymbolDropdowns();
    await fetchIndicatorList();
    setLayout(4);
}

document.addEventListener('DOMContentLoaded', init);

/* ── Stock price polling (non-crypto) ─────────────────────────── */

setInterval(async () => {
    if (charts.length === 0) return;
    try {
        const res = await fetch('/api/latest');
        const latestPrices = await res.json();

        charts.forEach(chart => {
            if (!["BTC/USD", "ETH/USD", "SOL/USD"].includes(chart.symbol)) {
                const data = latestPrices[chart.symbol];
                if (data) {
                    chart.applyTick(data.price, data.time);
                }
            }
        });
    } catch (e) {
        console.error("Error polling latest prices:", e);
    }
}, 1000);
