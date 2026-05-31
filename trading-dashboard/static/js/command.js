/**
 * NEXUS BTC AI COMMAND CENTER — Exact Screenshot Match
 * Live data polling, chart rendering, dynamic UI updates
 */

document.addEventListener('DOMContentLoaded', () => {

    // ══════════════════════════════
    // 1. CLOCK
    // ══════════════════════════════
    const updateClock = () => {
        const now = new Date();
        const hdrTime = document.getElementById('hdr-time');
        const hdrDate = document.getElementById('hdr-date');
        if (hdrTime) hdrTime.textContent = now.toLocaleTimeString('en-US', { hour12: false });
        if (hdrDate) hdrDate.textContent = now.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    };
    updateClock();
    setInterval(updateClock, 1000);

    // ══════════════════════════════
    // 2. CHART INITIALIZATION
    // ══════════════════════════════
    let chart1, candleSeries1, projectionLine1;
    let chart2, candleSeries2;

    const initChart1 = () => {
        const container = document.getElementById('tv-chart-container');
        if (!container) return;
        chart1 = LightweightCharts.createChart(container, {
            layout: { background: { type: 'solid', color: 'transparent' }, textColor: '#607080' },
            grid: { vertLines: { color: 'rgba(0,200,255,0.04)' }, horzLines: { color: 'rgba(0,200,255,0.04)' } },
            crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
            rightPriceScale: { borderColor: 'rgba(0,200,255,0.1)' },
            timeScale: { borderColor: 'rgba(0,200,255,0.1)', timeVisible: true },
            handleScroll: true,
            handleScale: true,
        });
        candleSeries1 = chart1.addCandlestickSeries({
            upColor: '#00e676', downColor: '#ff3b5c',
            borderUpColor: '#00e676', borderDownColor: '#ff3b5c',
            wickUpColor: '#00e676', wickDownColor: '#ff3b5c',
        });
        projectionLine1 = chart1.addLineSeries({
            color: '#00d4ff', lineWidth: 2, lineStyle: 2,
            crosshairMarkerVisible: false,
        });
        new ResizeObserver(entries => {
            if (entries[0]) {
                const r = entries[0].contentRect;
                chart1.applyOptions({ width: r.width, height: r.height });
            }
        }).observe(container);
    };

    const initChart2 = () => {
        const container = document.getElementById('tv-chart2-container');
        if (!container) return;
        chart2 = LightweightCharts.createChart(container, {
            layout: { background: { type: 'solid', color: 'transparent' }, textColor: '#607080' },
            grid: { vertLines: { color: 'rgba(0,200,255,0.04)' }, horzLines: { color: 'rgba(0,200,255,0.04)' } },
            crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
            rightPriceScale: { borderColor: 'rgba(0,200,255,0.1)' },
            timeScale: { borderColor: 'rgba(0,200,255,0.1)', timeVisible: true },
        });
        candleSeries2 = chart2.addCandlestickSeries({
            upColor: '#00e676', downColor: '#ff3b5c',
            borderUpColor: '#00e676', borderDownColor: '#ff3b5c',
            wickUpColor: '#00e676', wickDownColor: '#ff3b5c',
        });
        new ResizeObserver(entries => {
            if (entries[0]) {
                const r = entries[0].contentRect;
                chart2.applyOptions({ width: r.width, height: r.height });
            }
        }).observe(container);
    };

    initChart1();
    initChart2();

    // ══════════════════════════════
    // 3. HELPER FUNCTIONS
    // ══════════════════════════════

    const fmt = (v) => {
        if (v === null || v === undefined) return '--';
        return '$' + Number(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    };

    const fmtK = (v) => {
        if (v >= 1000000) return '$' + (v / 1000000).toFixed(1) + 'M';
        if (v >= 1000) return '$' + (v / 1000).toFixed(0) + 'K';
        return '$' + v.toFixed(0);
    };

    const timeAgo = (ts) => {
        const now = Date.now();
        const diff = Math.floor((now - ts) / 1000);
        if (diff < 60) return diff + 's ago';
        if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
        return Math.floor(diff / 3600) + 'h ago';
    };

    const formatTime = (ts) => {
        const d = new Date(ts * 1000);
        return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' });
    };

    // Signal age tracking
    let signalTimestamp = Date.now();
    let lastSignal = null;

    setInterval(() => {
        const ageEl = document.getElementById('sig-age');
        if (ageEl) {
            const age = Math.floor((Date.now() - signalTimestamp) / 1000);
            if (age < 60) ageEl.textContent = age + 'S';
            else ageEl.textContent = Math.floor(age / 60) + 'M';
        }
    }, 1000);

    // ══════════════════════════════
    // 4. DRAW SPARKLINE ON CANVAS
    // ══════════════════════════════
    const drawSparkline = (canvas, data, color) => {
        if (!canvas || !data || data.length < 2) return;
        const ctx = canvas.getContext('2d');
        const w = canvas.width = canvas.offsetWidth * 2;
        const h = canvas.height = canvas.offsetHeight * 2;
        ctx.scale(2, 2);
        const rw = canvas.offsetWidth;
        const rh = canvas.offsetHeight;

        const min = Math.min(...data);
        const max = Math.max(...data);
        const range = max - min || 1;

        ctx.clearRect(0, 0, rw, rh);
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5;
        ctx.beginPath();

        data.forEach((v, i) => {
            const x = (i / (data.length - 1)) * rw;
            const y = rh - ((v - min) / range) * (rh - 4) - 2;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });

        ctx.stroke();

        // Gradient fill
        ctx.lineTo(rw, rh);
        ctx.lineTo(0, rh);
        ctx.closePath();
        const grad = ctx.createLinearGradient(0, 0, 0, rh);
        grad.addColorStop(0, color.replace(')', ',0.15)').replace('rgb', 'rgba'));
        grad.addColorStop(1, 'transparent');
        ctx.fillStyle = grad;
        ctx.fill();
    };

    // ══════════════════════════════
    // 5. RENDER LIQUIDATION BARS
    // ══════════════════════════════
    const renderLiquidations = (price) => {
        const container = document.getElementById('liq-bars');
        if (!container) return;

        // Generate estimated liquidation levels
        const levels = [];
        const atr = 250;
        for (let i = 5; i >= -5; i--) {
            if (i === 0) continue;
            const lvl = Math.round((price + i * atr) / 250) * 250;
            const dist = Math.abs(i);
            const intensity = Math.max(10, 100 - dist * 15 + Math.random() * 20);
            const type = i > 0 ? 'long' : 'short';
            levels.push({ price: lvl, intensity, type });
        }

        // Check if current price level
        const currentLvl = Math.round(price / 250) * 250;

        container.innerHTML = levels.map(l => {
            const isCurrent = Math.abs(l.price - currentLvl) < 250;
            const barClass = isCurrent ? 'current' : l.type;
            return `<div class="liq-row">
                <span class="liq-price">$${(l.price).toLocaleString()}</span>
                <div class="liq-bar-bg">
                    <div class="liq-bar-fill ${barClass}" style="width:${l.intensity}%"></div>
                </div>
            </div>`;
        }).join('');
    };

    // ══════════════════════════════
    // 6. MAIN DATA UPDATE
    // ══════════════════════════════
    const updateDashboard = async () => {
        try {
            const res = await fetch('/api/command/snapshot');
            const data = await res.json();
            if (data.error) {
                console.warn('Snapshot error:', data.error);
                return;
            }

            const price = data.price || 0;
            const signal = data.signal || 'NEUTRAL';
            const confidence = data.confidence || 0;
            const factors = data.factors || {};
            const reasoning = data.reasoning || '';
            const aiReasoning = data.ai_reasoning_full || reasoning;
            const risk = data.risk || {};
            const projection = data.projection || [];
            const proj1h = data.projection_1h;
            const mtf = data.multi_tf || [];
            const signalLog = data.signal_log || [];
            const smcTags = data.smc_tags || [];
            const bars1m = data.bars_1m || [];
            const fng = data.fng || {};
            const largeTrades = data.large_trades || [];

            // ── Header price ──
            const hdrPrice = document.getElementById('hdr-price');
            if (hdrPrice) hdrPrice.textContent = fmt(price);

            // ── BTC Price Panel ──
            const btcPrice = document.getElementById('btc-price');
            if (btcPrice) btcPrice.textContent = fmt(price);

            const btcChange = document.getElementById('btc-change');
            if (btcChange && data.change_pct !== undefined) {
                btcChange.textContent = (data.change_pct > 0 ? '+' : '') + data.change_pct + '%';
                btcChange.className = 'price-change ' + (data.change_pct >= 0 ? 'up' : 'down');
            }

            // AI Prediction
            const aiPred = document.getElementById('ai-pred');
            if (aiPred && proj1h) aiPred.textContent = fmt(proj1h);

            // ATR
            const atrEl = document.getElementById('atr-val');
            if (atrEl && factors.atr) atrEl.textContent = fmt(factors.atr);

            // ── Signal Core ──
            const sigText = document.getElementById('signal-text');
            const sigOrb = document.getElementById('signal-orb');
            if (sigText) {
                sigText.textContent = signal;
                const sigColor = signal === 'BUY' ? '#00e676' : signal === 'SELL' ? '#ff3b5c' : '#ffaa00';
                sigText.style.color = sigColor;
                sigText.style.textShadow = `0 0 20px ${sigColor}`;

                // Update orb rings
                if (sigOrb) {
                    sigOrb.querySelectorAll('.orb-ring').forEach(r => {
                        r.style.borderColor = sigColor.replace(')', ',0.25)');
                    });
                    sigOrb.style.background = `radial-gradient(circle, ${sigColor}11 0%, transparent 70%)`;
                }
            }

            // Track signal age
            if (signal !== lastSignal) {
                signalTimestamp = Date.now();
                lastSignal = signal;
            }

            const sigStrength = document.getElementById('sig-strength');
            if (sigStrength) sigStrength.textContent = data.strength || 'MODERATE';

            const sigConfSub = document.getElementById('sig-conf-sub');
            if (sigConfSub) sigConfSub.textContent = confidence + '%';

            // ── Confidence Panel ──
            const confPct = document.getElementById('conf-pct');
            if (confPct) confPct.textContent = confidence + '%';

            const confBar = document.getElementById('conf-bar');
            if (confBar) confBar.style.width = confidence + '%';

            // Update checklist
            const checklist = document.getElementById('conf-checklist');
            if (checklist) {
                checklist.innerHTML = `
                    <li class="${factors.supertrend_up ? 'pass' : 'fail'}"><span class="chk">${factors.supertrend_up ? '✓' : '✗'}</span> Supertrend Bullish</li>
                    <li class="${factors.rsi_above_50 ? 'pass' : 'fail'}"><span class="chk">${factors.rsi_above_50 ? '✓' : '✗'}</span> RSI > 50 (${factors.rsi_value || '--'})</li>
                    <li class="${factors.above_ema50 ? 'pass' : 'fail'}"><span class="chk">${factors.above_ema50 ? '✓' : '✗'}</span> Price > EMA50</li>
                    <li class="${factors.macd_bullish ? 'pass' : 'fail'}"><span class="chk">${factors.macd_bullish ? '✓' : '✗'}</span> MACD Bullish</li>
                    <li class="${factors.volume_confirm ? 'pass' : 'fail'}"><span class="chk">${factors.volume_confirm ? '✓' : '✗'}</span> Volume Confirm</li>
                `;
            }

            // ── Chart 1 ──
            if (bars1m && bars1m.length > 0 && candleSeries1) {
                const formatted = bars1m.map(b => ({
                    time: b.time,
                    open: parseFloat(b.open),
                    high: parseFloat(b.high),
                    low: parseFloat(b.low),
                    close: parseFloat(b.close),
                }));
                candleSeries1.setData(formatted);

                // Projection line
                if (projection && projection.length > 0 && projectionLine1) {
                    const lastBar = formatted[formatted.length - 1];
                    const projData = [{ time: lastBar.time, value: lastBar.close }];
                    projection.forEach(p => {
                        projData.push({ time: p.time, value: p.value });
                    });
                    projectionLine1.setData(projData);
                }

                // Forecast label
                const forecastPrice = document.getElementById('forecast-price');
                if (forecastPrice && projection.length > 0) {
                    forecastPrice.textContent = fmt(projection[projection.length - 1].value);
                }
            }

            // ── Chart 2 (same data, different chart instance) ──
            if (bars1m && bars1m.length > 0 && candleSeries2) {
                const formatted2 = bars1m.map(b => ({
                    time: b.time,
                    open: parseFloat(b.open),
                    high: parseFloat(b.high),
                    low: parseFloat(b.low),
                    close: parseFloat(b.close),
                }));
                candleSeries2.setData(formatted2);
            }

            // ── AI Reasoning ──
            const reasoningEl = document.getElementById('reasoning-text');
            if (reasoningEl) {
                const now = new Date();
                const timeStr = now.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
                const fullText = `[${timeStr}] BTC at ${fmt(price)} — Primary bias: ${signal} (${signal === 'NEUTRAL' ? 'consolidation' : signal === 'BUY' ? 'bullish' : 'bearish'}). ` +
                    `Supertrend is aligned ${factors.supertrend_up ? 'upward' : 'downward'}, price trading ${factors.above_ema50 ? 'above' : 'below'} EMA-50. ` +
                    `RSI shows ${factors.rsi_value > 50 ? 'strength' : 'weakness'} at ${factors.rsi_value || '--'}. ` +
                    `MACD histogram is ${factors.macd_bullish ? 'bullish' : 'bearish'}. ` +
                    `Volume is ${factors.volume_confirm ? 'confirming' : 'unconvincing'}. ` +
                    (smcTags.length > 0 ? `Active structure: ${smcTags.join(', ')}. ` : '') +
                    `Confidence: ${confidence}%.`;
                reasoningEl.textContent = fullText;
            }

            // ── SMC Tags ──
            const smcTagsEl = document.getElementById('smc-tags');
            if (smcTagsEl && smcTags.length > 0) {
                smcTagsEl.innerHTML = smcTags.map(tag => {
                    const isBearish = tag.toLowerCase().includes('bearish') || tag.toLowerCase().includes('sell');
                    return `<span class="smc-tag ${isBearish ? 'bearish' : 'bullish'}">${tag}</span>`;
                }).join('');
            }

            // ── Liquidations ──
            renderLiquidations(price);

            // ── Risk Management ──
            document.getElementById('risk-entry').textContent = risk.entry ? fmt(risk.entry) : '$--';
            document.getElementById('risk-sl').textContent = risk.stop_loss ? fmt(risk.stop_loss) : '$--';
            document.getElementById('risk-tp').textContent = risk.take_profit ? fmt(risk.take_profit) : '$--';
            document.getElementById('risk-rr').textContent = risk.risk_reward ? `1 : ${risk.risk_reward}` : '1 : --';
            document.getElementById('risk-atr').textContent = risk.atr ? fmt(risk.atr) : '$--';

            // ── Signal Log ──
            const siglogBody = document.getElementById('siglog-body');
            if (siglogBody && signalLog.length > 0) {
                siglogBody.innerHTML = signalLog.slice().reverse().map(entry => {
                    const t = formatTime(entry.time);
                    return `<div class="siglog-row">
                        <span class="siglog-badge ${entry.signal}">${entry.signal}</span>
                        <span class="siglog-price">${fmt(entry.price)}</span>
                        <span class="siglog-reason">${entry.reason || ''}</span>
                        <span class="siglog-time">${t}</span>
                    </div>`;
                }).join('');
            }

            // ── Multi-Timeframe Bias ──
            const mtfBody = document.getElementById('mtf-body');
            if (mtfBody && mtf.length > 0) {
                mtfBody.innerHTML = mtf.map((tf, idx) => {
                    const color = tf.signal === 'BUY' ? '#00e676' : tf.signal === 'SELL' ? '#ff3b5c' : '#ffaa00';
                    return `<div class="mtf-row">
                        <span class="mtf-tf">${tf.timeframe}</span>
                        <div class="mtf-spark"><canvas id="mtf-canvas-${idx}"></canvas></div>
                        <span class="mtf-signal-badge ${tf.signal}">${tf.signal}</span>
                    </div>`;
                }).join('');

                // Draw sparklines after DOM update
                requestAnimationFrame(() => {
                    mtf.forEach((tf, idx) => {
                        const canvas = document.getElementById(`mtf-canvas-${idx}`);
                        const color = tf.signal === 'BUY' ? '#00e676' : tf.signal === 'SELL' ? '#ff3b5c' : '#ffaa00';
                        drawSparkline(canvas, tf.sparkline, color);
                    });
                });
            }

            // ── Whale Tracker ──
            const whaleBody = document.getElementById('whale-body');
            if (whaleBody) {
                if (largeTrades.length > 0) {
                    let totalBuy = 0, totalSell = 0;
                    largeTrades.forEach(t => {
                        if (t.side === 'BUY') totalBuy += t.usd;
                        else totalSell += t.usd;
                    });
                    const total = totalBuy + totalSell || 1;
                    const buyPct = (totalBuy / total * 100).toFixed(0);
                    const sellPct = (totalSell / total * 100).toFixed(0);

                    document.getElementById('wp-bar-buy').style.width = buyPct + '%';
                    document.getElementById('wp-bar-sell').style.width = sellPct + '%';
                    document.getElementById('wp-buy-val').textContent = fmtK(totalBuy);
                    document.getElementById('wp-sell-val').textContent = fmtK(totalSell);

                    whaleBody.innerHTML = largeTrades.slice(0, 8).map(t => {
                        const d = new Date(t.time);
                        const ts = d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
                        return `<div class="wt-row">
                            <span>${ts}</span>
                            <span class="side-${t.side.toLowerCase()}">${t.side}</span>
                            <span>${t.qty.toFixed(4)}</span>
                            <span>${fmtK(t.usd)}</span>
                        </div>`;
                    }).join('');
                } else {
                    whaleBody.innerHTML = '<div class="wt-empty">Waiting for large prints (> $100k)...</div>';
                }
            }

            // ── Market Sentiment (Fear & Greed) ──
            if (fng && fng.value !== undefined) {
                const fngValue = document.getElementById('fng-value');
                const fngLabel = document.getElementById('fng-label');
                const fngFill = document.getElementById('fng-fill');

                if (fngValue) fngValue.textContent = fng.value;
                if (fngLabel) {
                    fngLabel.textContent = fng.label;
                    // Color based on value
                    if (fng.value <= 25) fngLabel.style.color = '#ff3b5c';
                    else if (fng.value <= 45) fngLabel.style.color = '#ff8800';
                    else if (fng.value <= 55) fngLabel.style.color = '#ffaa00';
                    else if (fng.value <= 75) fngLabel.style.color = '#00e676';
                    else fngLabel.style.color = '#00ff88';
                }
                if (fngFill) fngFill.style.left = fng.value + '%';

                // 7 day trend
                const trendEl = document.getElementById('fng-trend');
                if (trendEl && fng.trend) {
                    trendEl.innerHTML = fng.trend.map(v => {
                        let bg;
                        if (v <= 25) bg = '#ff3b5c';
                        else if (v <= 45) bg = '#ff8800';
                        else if (v <= 55) bg = '#ffaa00';
                        else if (v <= 75) bg = '#00e676';
                        else bg = '#00ff88';
                        return `<div class="trend-block" style="background:${bg}; opacity:0.7;"></div>`;
                    }).join('');
                }
            }

        } catch (err) {
            console.error('Dashboard update error:', err);
        }
    };

    // ══════════════════════════════
    // 7. START
    // ══════════════════════════════
    updateDashboard();
    setInterval(updateDashboard, 15000);
});