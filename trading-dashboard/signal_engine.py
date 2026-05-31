"""
signal_engine.py – BTC AI Command Center signal logic.
Computes signals, SMC zones, risk levels, multi-TF bias, AI projection.
"""

import math
import time
import pandas as pd
import pandas_ta as ta
import numpy as np
import data_source

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe(v):
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return None
    return float(v)

# ---------------------------------------------------------------------------
# Signal History (in-memory ring buffer)
# ---------------------------------------------------------------------------

_signal_log = []  # list of {time, signal, price, reason}
_MAX_LOG = 50
_last_signal = None

def _log_signal(signal, price, reason):
    global _last_signal
    entry = {
        "time": int(time.time()),
        "signal": signal,
        "price": round(price, 2),
        "reason": reason
    }
    if _last_signal is None or _last_signal["signal"] != signal:
        _signal_log.append(entry)
        if len(_signal_log) > _MAX_LOG:
            _signal_log.pop(0)
    _last_signal = entry

# ---------------------------------------------------------------------------
# Core Signal Logic
# ---------------------------------------------------------------------------

def compute_signal(bars):
    """
    BUY  when Supertrend up AND RSI>50 AND close>EMA50
    SELL when Supertrend down AND RSI<50 AND close<EMA50
    NEUTRAL otherwise

    Returns: signal, confidence_pct, factors_dict, reasoning_text
    """
    if not bars or len(bars) < 60:
        return "NEUTRAL", 0, {}, "Insufficient data"

    df = pd.DataFrame(bars)
    for col in ['open', 'high', 'low', 'close']:
        df[col] = df[col].astype(float)
    if 'volume' in df.columns:
        df['volume'] = df['volume'].astype(float)

    close = df['close']
    last_close = float(close.iloc[-1])

    # --- Supertrend ---
    st = ta.supertrend(df['high'], df['low'], df['close'], length=10, multiplier=3)
    if st is None or st.empty:
        return "NEUTRAL", 0, {}, "Supertrend computation failed"
    dir_col = [c for c in st.columns if c.startswith('SUPERTd_')][0]
    st_dir = float(st[dir_col].iloc[-1])
    supertrend_up = bool(st_dir == 1)

    # --- RSI ---
    rsi_s = ta.rsi(close, length=14)
    rsi_val = _safe(rsi_s.iloc[-1]) if rsi_s is not None else None
    rsi_above = bool(rsi_val is not None and rsi_val > 50)

    # --- EMA 50 ---
    ema50_s = ta.ema(close, length=50)
    ema50_val = _safe(ema50_s.iloc[-1]) if ema50_s is not None else None
    above_ema = bool(ema50_val is not None and last_close > ema50_val)

    # --- MACD for extra confluence ---
    macd_df = ta.macd(close, fast=12, slow=26, signal=9)
    macd_bullish = False  # Python native bool
    if macd_df is not None and not macd_df.empty:
        m_col = [c for c in macd_df.columns if c.startswith('MACD_')][0]
        s_col = [c for c in macd_df.columns if c.startswith('MACDs_')][0]
        mv = _safe(macd_df[m_col].iloc[-1])
        sv = _safe(macd_df[s_col].iloc[-1])
        if mv is not None and sv is not None:
            macd_bullish = bool(mv > sv)

    # --- Volume confirmation ---
    vol_confirm = False  # Python native bool
    if 'volume' in df.columns and len(df) >= 20:
        avg_vol = df['volume'].iloc[-20:].mean()
        last_vol = df['volume'].iloc[-1]
        vol_confirm = bool(last_vol > avg_vol * 1.0)

    # --- ATR ---
    atr_s = ta.atr(df['high'], df['low'], df['close'], length=14)
    atr_val = _safe(atr_s.iloc[-1]) if atr_s is not None else None

    # --- Build factors (ensure all values are JSON-safe native types) ---
    factors = {
        "supertrend_up": bool(supertrend_up),
        "rsi_above_50": bool(rsi_above),
        "rsi_value": round(float(rsi_val), 1) if rsi_val else None,
        "above_ema50": bool(above_ema),
        "ema50_value": round(float(ema50_val), 2) if ema50_val else None,
        "macd_bullish": bool(macd_bullish),
        "volume_confirm": bool(vol_confirm),
        "atr": round(float(atr_val), 2) if atr_val else None,
    }

    # --- Core conditions ---
    buy_conditions = [supertrend_up, rsi_above, above_ema]
    sell_conditions = [not supertrend_up, not rsi_above, not above_ema]

    buy_count = sum(buy_conditions)
    sell_count = sum(sell_conditions)

    # Extra confluence factors (bonus)
    all_factors = buy_conditions + [macd_bullish, vol_confirm]
    met = sum(all_factors)
    total = len(all_factors)
    confidence = int(round((met / total) * 100))

    if all(buy_conditions):
        signal = "BUY"
        reasons = []
        reasons.append(f"Supertrend bullish")
        reasons.append(f"RSI {rsi_val:.0f} > 50")
        reasons.append(f"Price above EMA50 ({ema50_val:.0f})")
        if macd_bullish:
            reasons.append("MACD bullish cross")
        if vol_confirm:
            reasons.append("Volume confirmed")
        reasoning = "Bullish confluence: " + ", ".join(reasons) + "."
    elif all(sell_conditions):
        signal = "SELL"
        reasons = []
        reasons.append(f"Supertrend bearish")
        reasons.append(f"RSI {rsi_val:.0f} < 50")
        reasons.append(f"Price below EMA50 ({ema50_val:.0f})")
        reasoning = "Bearish confluence: " + ", ".join(reasons) + "."
        # For sell, count sell conditions
        sell_factors = sell_conditions + [not macd_bullish, not vol_confirm]
        met_sell = sum(sell_factors)
        confidence = int(round((met_sell / total) * 100))
    else:
        signal = "NEUTRAL"
        reasoning = f"Mixed signals: Supertrend {'↑' if supertrend_up else '↓'}, RSI {rsi_val:.0f}, Price {'>' if above_ema else '<'} EMA50. No clear edge."
        confidence = int(round(50 - abs(buy_count - sell_count) * 10))
        if confidence < 0:
            confidence = 10

    _log_signal(signal, last_close, f"RSI {rsi_val:.0f}" if rsi_val else "N/A")

    return signal, confidence, factors, reasoning


# ---------------------------------------------------------------------------
# SMC Zones (Smart Money Concepts)
# ---------------------------------------------------------------------------

def compute_smc_zones(bars):
    """
    Compute Order Blocks, FVGs, BOS, CHoCH, and liquidity sweeps using smartmoneyconcepts.
    Returns dict with zones for chart overlay mapped to timestamp.
    """
    if not bars or len(bars) < 20:
        return {"order_blocks": [], "fvgs": [], "bos": [], "choch": [], "liquidity": [], "swing_highs": [], "swing_lows": []}

    df = pd.DataFrame(bars)
    for col in ['open', 'high', 'low', 'close']:
        df[col] = df[col].astype(float)
        
    times = [int(t) for t in df['time'].values]
    
    order_blocks = []
    fvgs = []
    bos_lines = []
    choch_lines = []
    liquidity = []
    swing_highs = []
    swing_lows = []
    
    try:
        from smartmoneyconcepts import smc
        
        # 1. Swings
        swing_df = smc.swing_highs_lows(df)
        
        # 2. BOS & CHOCH
        bos_df = smc.bos_choch(df, swing_df)
        
        # 3. OB
        ob_df = smc.ob(df, swing_df)
        
        # 4. FVG
        fvg_df = smc.fvg(df)
        
        # 5. Liquidity
        liq_df = smc.liquidity(df, swing_df)
        
        # Parse Swings
        for i in range(len(swing_df)):
            if pd.notna(swing_df['HighLow'].iloc[i]):
                val = swing_df['HighLow'].iloc[i]
                level = float(swing_df['Level'].iloc[i])
                if val == 1.0:
                    swing_highs.append({"index": i, "time": times[i], "price": level, "type": "high"})
                elif val == -1.0:
                    swing_lows.append({"index": i, "time": times[i], "price": level, "type": "low"})
                    
        # Parse FVG
        for i in range(len(fvg_df)):
            if pd.notna(fvg_df['FVG'].iloc[i]):
                val = fvg_df['FVG'].iloc[i]
                top = float(fvg_df['Top'].iloc[i])
                bottom = float(fvg_df['Bottom'].iloc[i])
                mitigated = fvg_df['MitigatedIndex'].iloc[i]
                end_time = times[int(mitigated)] if pd.notna(mitigated) and int(mitigated) < len(times) else None
                fvgs.append({
                    "time_start": times[i-2] if i-2 >= 0 else times[i],
                    "time_end": end_time,
                    "top": top,
                    "bottom": bottom,
                    "type": "bullish" if val == 1.0 else "bearish"
                })
                
        # Parse OB
        for i in range(len(ob_df)):
            if pd.notna(ob_df['OB'].iloc[i]):
                val = ob_df['OB'].iloc[i]
                top = float(ob_df['Top'].iloc[i])
                bottom = float(ob_df['Bottom'].iloc[i])
                mitigated = ob_df['MitigatedIndex'].iloc[i]
                end_time = times[int(mitigated)] if pd.notna(mitigated) and int(mitigated) < len(times) else None
                order_blocks.append({
                    "time_start": times[i],
                    "time_end": end_time,
                    "top": top,
                    "bottom": bottom,
                    "type": "bullish" if val == 1.0 else "bearish"
                })
                
        # Parse BOS / CHoCH
        for i in range(len(bos_df)):
            bos_val = bos_df['BOS'].iloc[i]
            choch_val = bos_df['CHOCH'].iloc[i]
            level = bos_df['Level'].iloc[i]
            if pd.notna(bos_val):
                bos_lines.append({
                    "time": times[i],
                    "price": float(level),
                    "type": "bullish" if bos_val == 1.0 else "bearish"
                })
            if pd.notna(choch_val):
                choch_lines.append({
                    "time": times[i],
                    "price": float(level),
                    "type": "bullish" if choch_val == 1.0 else "bearish"
                })
                
        # Parse Liquidity
        for i in range(len(liq_df)):
            if pd.notna(liq_df['Liquidity'].iloc[i]):
                val = liq_df['Liquidity'].iloc[i]
                level = float(liq_df['Level'].iloc[i])
                end_idx = liq_df['End'].iloc[i]
                swept_idx = liq_df['Swept'].iloc[i]
                if pd.notna(swept_idx) and int(swept_idx) < len(times):
                    liquidity.append({
                        "time": times[int(swept_idx)],
                        "price": level,
                        "type": "buy_side" if val == 1.0 else "sell_side"
                    })
                    
    except Exception as e:
        print("SMC Error:", e)

    # Return last N for frontend
    return {
        "order_blocks": order_blocks[-20:],
        "fvgs": fvgs[-20:],
        "bos": bos_lines[-10:],
        "choch": choch_lines[-5:],
        "liquidity": liquidity[-10:],
        "swing_highs": swing_highs[-10:],
        "swing_lows": swing_lows[-10:]
    }


# ---------------------------------------------------------------------------
# Risk Levels
# ---------------------------------------------------------------------------

_active_trade_setup = None

def compute_risk_levels(bars, signal, smc_zones):
    global _active_trade_setup

    if signal == "NEUTRAL":
        _active_trade_setup = None
        return {}

    # If we already have a locked-in setup for this exact signal direction, return it
    if _active_trade_setup and _active_trade_setup["signal"] == signal:
        return _active_trade_setup["risk_data"]

    # Generate a NEW real logic setup based on SMC structure
    df = pd.DataFrame(bars)
    for col in ['open', 'high', 'low', 'close']:
        df[col] = df[col].astype(float)

    import pandas_ta as ta
    atr_s = ta.atr(df['high'], df['low'], df['close'], length=14)
    atr_val = _safe(atr_s.iloc[-1]) if atr_s is not None else None
    if atr_val is None:
        atr_val = float(df['close'].iloc[-1]) * 0.01  # fallback

    entry = float(df['close'].iloc[-1])

    sl = entry
    tp = entry

    swing_highs = smc_zones.get("swing_highs", [])
    swing_lows = smc_zones.get("swing_lows", [])

    if signal == "BUY":
        # Stop loss at the most recent swing low (minus a tiny buffer)
        if swing_lows:
            recent_sl = swing_lows[-1]["price"]
            # Ensure it's actually below entry and not too far/close
            if recent_sl < entry:
                sl = recent_sl - (atr_val * 0.2)
            else:
                sl = entry - 1.5 * atr_val
        else:
            sl = entry - 1.5 * atr_val
        
        # Take profit targeting a 1:2 Risk/Reward ratio
        risk_dist = entry - sl
        if risk_dist <= 0: risk_dist = atr_val
        target_tp = entry + (risk_dist * 2.0)
        
        # Or at recent swing high if it's better
        if swing_highs:
            recent_sh = swing_highs[-1]["price"]
            if recent_sh > entry + risk_dist: 
                tp = recent_sh
            else:
                tp = target_tp
        else:
            tp = target_tp

    elif signal == "SELL":
        # Stop loss at the most recent swing high (plus a buffer)
        if swing_highs:
            recent_sh = swing_highs[-1]["price"]
            if recent_sh > entry:
                sl = recent_sh + (atr_val * 0.2)
            else:
                sl = entry + 1.5 * atr_val
        else:
            sl = entry + 1.5 * atr_val
            
        risk_dist = sl - entry
        if risk_dist <= 0: risk_dist = atr_val
        target_tp = entry - (risk_dist * 2.0)
        
        # Take profit targeting recent swing low if it's better
        if swing_lows:
            recent_sl = swing_lows[-1]["price"]
            if recent_sl < entry - risk_dist:
                tp = recent_sl
            else:
                tp = target_tp
        else:
            tp = target_tp

    risk = abs(entry - sl)
    reward = abs(tp - entry)
    rr = round(reward / risk, 2) if risk > 0 else 0

    risk_data = {
        "entry": round(entry, 2),
        "stop_loss": round(sl, 2),
        "take_profit": round(tp, 2),
        "risk_reward": rr,
        "atr": round(atr_val, 2),
        "position_size_pct": 1.0,  # 1% of account risk
    }

    _active_trade_setup = {
        "signal": signal,
        "risk_data": risk_data
    }

    return risk_data


# ---------------------------------------------------------------------------
# AI Projection (EMA slope extrapolation)
# ---------------------------------------------------------------------------

def compute_projection(bars, n_candles=5):
    """
    Simple EMA-slope extrapolation. Clearly a PROJECTION, not a prediction.
    Returns list of {time, value} for the forecast line.
    """
    if not bars or len(bars) < 30:
        return [], None

    df = pd.DataFrame(bars)
    df['close'] = df['close'].astype(float)

    ema20 = ta.ema(df['close'], length=20)
    if ema20 is None:
        return [], None

    # Slope from last 5 EMA points
    recent = ema20.dropna().tail(5).values
    if len(recent) < 2:
        return [], None

    slope = (recent[-1] - recent[0]) / len(recent)
    last_time = int(bars[-1]['time'])
    last_val = float(recent[-1])

    # Estimate candle interval
    if len(bars) >= 2:
        interval = int(bars[-1]['time']) - int(bars[-2]['time'])
    else:
        interval = 3600

    projection = []
    for i in range(1, n_candles + 1):
        proj_time = last_time + interval * i
        proj_val = last_val + slope * i
        projection.append({"time": proj_time, "value": round(proj_val, 2)})

    next_1h_val = round(last_val + slope * max(1, 3600 // max(interval, 1)), 2)

    return projection, next_1h_val


# ---------------------------------------------------------------------------
# Multi-Timeframe Bias
# ---------------------------------------------------------------------------

def compute_multi_tf_bias():
    """
    Run signal logic on 5M, 15M, 1H, 4H.
    Returns list of {tf, signal, confidence, sparkline[]}.
    """
    # Map 4h -> we use 1h with more bars since Alpaca doesn't have 4h directly
    tf_configs = [
        ("5m", "5m", 200),
        ("15m", "15m", 200),
        ("1h", "1h", 200),
        ("4h", "1h", 500),  # Use 1h bars, aggregate manually
    ]

    results = []
    for label, tf, limit in tf_configs:
        try:
            bars = data_source.get_historical_bars("BTC/USD", tf, limit=limit)

            if label == "4h" and bars:
                # Aggregate 1h into 4h
                bars = _aggregate_bars(bars, 4)

            signal, confidence, factors, reasoning = compute_signal(bars)

            # Sparkline: last 20 closes
            sparkline = []
            if bars and len(bars) > 20:
                for b in bars[-20:]:
                    sparkline.append(float(b['close']))

            results.append({
                "timeframe": label.upper(),
                "signal": signal,
                "confidence": confidence,
                "sparkline": sparkline
            })
        except Exception as e:
            print(f"Multi-TF error for {label}: {e}")
            results.append({
                "timeframe": label.upper(),
                "signal": "NEUTRAL",
                "confidence": 0,
                "sparkline": []
            })

    return results


def _aggregate_bars(bars, factor):
    """Aggregate bars by factor (e.g. 4 x 1h -> 4h)."""
    if not bars:
        return bars
    agg = []
    for i in range(0, len(bars) - factor + 1, factor):
        chunk = bars[i:i+factor]
        agg.append({
            "time": chunk[0]["time"],
            "open": chunk[0]["open"],
            "high": max(b["high"] for b in chunk),
            "low": min(b["low"] for b in chunk),
            "close": chunk[-1]["close"],
            "volume": sum(b.get("volume", 0) for b in chunk)
        })
    return agg


# ---------------------------------------------------------------------------
# Full Snapshot
# ---------------------------------------------------------------------------
_fng_cache = None
_fng_last_fetch = 0

def get_fear_and_greed():
    global _fng_cache, _fng_last_fetch
    import time, requests
    if _fng_cache and (time.time() - _fng_last_fetch < 3600):
        return _fng_cache
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=7", timeout=5)
        data = r.json()
        if data and "data" in data and len(data["data"]) > 0:
            val = int(data["data"][0]["value"])
            label = data["data"][0]["value_classification"]
            trend = [int(d["value"]) for d in data["data"]]
            _fng_cache = {"value": val, "label": label.upper(), "trend": trend}
            _fng_last_fetch = time.time()
            return _fng_cache
    except Exception as e:
        print("FNG error:", e)
    if not _fng_cache:
        _fng_cache = {"value": 50, "label": "NEUTRAL", "trend": [50]*7}
    return _fng_cache

_trades_cache = []
_trades_last_fetch = 0

def get_large_trades():
    global _trades_cache, _trades_last_fetch
    import time, requests
    if _trades_cache and (time.time() - _trades_last_fetch < 15):
        return _trades_cache
    try:
        r = requests.get("https://api.binance.com/api/v3/aggTrades?symbol=BTCUSDT&limit=500", timeout=5)
        data = r.json()
        large = []
        for t in data:
            qty = float(t['q'])
            price = float(t['p'])
            usd = qty * price
            if usd >= 100000:
                side = "SELL" if t['m'] else "BUY"
                large.append({"qty": round(qty, 4), "price": round(price, 2), "usd": round(usd, 2), "side": side, "time": t['T']})
        large.sort(key=lambda x: x['time'], reverse=True)
        _trades_cache = large[:20]
        _trades_last_fetch = time.time()
    except Exception as e:
        print("Binance trades error:", e)
    return _trades_cache

def get_command_snapshot():
    import data_source
    bars_1m = data_source.get_historical_bars("BTC/USD", "1m", limit=500)
    bars_1h = data_source.get_historical_bars("BTC/USD", "1h", limit=500)

    # Use 1m for signal
    primary_bars = bars_1m if bars_1m else bars_1h

    if not primary_bars:
        return {"error": "No data available"}

    last_bar = primary_bars[-1]
    price = float(last_bar['close'])

    # Compute today's change
    change_pct = 0
    if len(primary_bars) > 1440:  # ~24h of 1m bars
        open_24h = float(primary_bars[-1440]['open'])
        change_pct = round((price - open_24h) / open_24h * 100, 2)

    # Signal
    signal, confidence, factors, reasoning = compute_signal(primary_bars)

    # SMC zones (use 1h for cleaner zones)
    smc = compute_smc_zones(bars_1h if bars_1h else primary_bars)

    # Risk levels
    risk = compute_risk_levels(primary_bars, signal, smc)

    # AI Projection
    projection, next_1h = compute_projection(primary_bars)

    # Multi-TF
    try:
        mtf = compute_multi_tf_bias()
    except Exception as e:
        print(f"MTF error: {e}")
        mtf = []

    # SMC tags for reasoning
    smc_tags = []
    
    # Enhanced reasoning logic based on real SMC output
    latest_reasons = []
    if smc["liquidity"]:
        sweep = smc["liquidity"][-1]
        smc_tags.append(f"LIQ ({sweep['type']})")
        if sweep['type'] == 'sell_side':
            latest_reasons.append(f"Sell-side liquidity above {sweep['price']:.0f} was recently swept.")
        else:
            latest_reasons.append(f"Buy-side liquidity below {sweep['price']:.0f} was recently swept.")
            
    if smc["choch"]:
        ch = smc["choch"][-1]
        smc_tags.append(f"CHoCH ({ch['type']})")
        latest_reasons.append(f"{ch['type'].capitalize()} Change of Character (CHoCH) detected at {ch['price']:.0f}.")
        
    if smc["bos"]:
        bos = smc["bos"][-1]
        smc_tags.append(f"BOS ({bos['type']})")
        latest_reasons.append(f"Structural trend confirmed with {bos['type']} BOS at {bos['price']:.0f}.")
        
    if smc["order_blocks"]:
        ob = smc["order_blocks"][-1]
        smc_tags.append(f"OB ({ob['type']})")
        latest_reasons.append(f"Price action created a {ob['type']} order block as a potential reaction zone.")
        
    if smc["fvgs"]:
        fvg = smc["fvgs"][-1]
        smc_tags.append(f"FVG ({fvg['type']})")
        latest_reasons.append(f"{fvg['type'].capitalize()} Fair Value Gap (FVG) identified.")
        
    ai_reasoning_full = " ".join(latest_reasons) if latest_reasons else "Market structure is currently consolidating. Waiting for clear liquidity sweep or displacement."

    # Signal strength
    if confidence >= 80:
        strength = "VERY STRONG"
    elif confidence >= 60:
        strength = "STRONG"
    elif confidence >= 40:
        strength = "MODERATE"
    else:
        strength = "WEAK"

    return {
        "price": round(price, 2),
        "change_pct": change_pct,
        "signal": signal,
        "strength": strength,
        "confidence": confidence,
        "factors": factors,
        "reasoning": reasoning,
        "ai_reasoning_full": ai_reasoning_full,
        "smc_zones": smc,
        "smc_tags": smc_tags,
        "risk": risk,
        "projection": projection,
        "projection_1h": next_1h,
        "multi_tf": mtf,
        "signal_log": list(_signal_log[-20:]),
        "signal_time": int(time.time()),
        "timeframe": "1M",
        "bars_1h": bars_1h[-200:] if bars_1h else [],
        "bars_1m": bars_1m[-200:] if bars_1m else [],
        "fng": get_fear_and_greed(),
        "large_trades": get_large_trades(),
    }

