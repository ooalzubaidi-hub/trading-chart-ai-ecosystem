import pandas as pd
import pandas_ta as ta
import numpy as np
import math

# ---------------------------------------------------------------------------
# Indicator Registry
# Each entry:
#   key          – URL param value (lowercase)
#   name         – human-readable display name
#   category     – Overlap | Momentum | Volatility | Volume | Trend
#   render       – line | lines | osc | hist
#   params       – default params dict
#   compute(df, params) -> list[dict]   (time + value/sub-series)
# ---------------------------------------------------------------------------

def _safe(v):
    """Return None for NaN/Inf, else float."""
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return None
    return float(v)

def _ts(row):
    return int(row['time'])

# ── Overlap / line ─────────────────────────────────────────────────────────

def _compute_ema(df, p):
    length = int(p.get('length', 20))
    s = ta.ema(df['close'], length=length)
    out = []
    for i, v in enumerate(s):
        if _safe(v) is not None:
            out.append({"time": int(df.iloc[i]['time']), "value": _safe(v)})
    return out

def _compute_sma(df, p):
    length = int(p.get('length', 50))
    s = ta.sma(df['close'], length=length)
    out = []
    for i, v in enumerate(s):
        if _safe(v) is not None:
            out.append({"time": int(df.iloc[i]['time']), "value": _safe(v)})
    return out

def _compute_wma(df, p):
    length = int(p.get('length', 20))
    s = ta.wma(df['close'], length=length)
    out = []
    for i, v in enumerate(s):
        if _safe(v) is not None:
            out.append({"time": int(df.iloc[i]['time']), "value": _safe(v)})
    return out

def _compute_hma(df, p):
    length = int(p.get('length', 20))
    s = ta.hma(df['close'], length=length)
    out = []
    for i, v in enumerate(s):
        if _safe(v) is not None:
            out.append({"time": int(df.iloc[i]['time']), "value": _safe(v)})
    return out

def _compute_dema(df, p):
    length = int(p.get('length', 20))
    s = ta.dema(df['close'], length=length)
    out = []
    for i, v in enumerate(s):
        if _safe(v) is not None:
            out.append({"time": int(df.iloc[i]['time']), "value": _safe(v)})
    return out

def _compute_tema(df, p):
    length = int(p.get('length', 20))
    s = ta.tema(df['close'], length=length)
    out = []
    for i, v in enumerate(s):
        if _safe(v) is not None:
            out.append({"time": int(df.iloc[i]['time']), "value": _safe(v)})
    return out

def _compute_kama(df, p):
    length = int(p.get('length', 10))
    s = ta.kama(df['close'], length=length)
    out = []
    for i, v in enumerate(s):
        if _safe(v) is not None:
            out.append({"time": int(df.iloc[i]['time']), "value": _safe(v)})
    return out

def _compute_vwap(df, p):
    if 'volume' not in df.columns:
        return []
    df2 = df.copy()
    df2.index = pd.to_datetime(df2['time'], unit='s')
    s = ta.vwap(df2['high'], df2['low'], df2['close'], df2['volume'])
    out = []
    for i, v in enumerate(s):
        if _safe(v) is not None:
            out.append({"time": int(df.iloc[i]['time']), "value": _safe(v)})
    return out

# ── Overlap / lines ───────────────────────────────────────────────────────

def _compute_bbands(df, p):
    length = int(p.get('length', 20))
    bb = ta.bbands(df['close'], length=length, std=2)
    if bb is None or bb.empty:
        return []
    bbl = [c for c in bb.columns if c.startswith('BBL')][0]
    bbm = [c for c in bb.columns if c.startswith('BBM')][0]
    bbu = [c for c in bb.columns if c.startswith('BBU')][0]
    out = []
    for i in range(len(bb)):
        l, m, u = _safe(bb.iloc[i][bbl]), _safe(bb.iloc[i][bbm]), _safe(bb.iloc[i][bbu])
        if l is not None:
            out.append({"time": int(df.iloc[i]['time']), "lower": l, "middle": m, "upper": u})
    return out

def _compute_supertrend(df, p):
    length = int(p.get('length', 10))
    mult = float(p.get('multiplier', 3.0))
    st = ta.supertrend(df['high'], df['low'], df['close'], length=length, multiplier=mult)
    if st is None or st.empty:
        return []
    st_col = [c for c in st.columns if c.startswith('SUPERT_')][0]
    dir_col = [c for c in st.columns if c.startswith('SUPERTd_')][0]
    out = []
    
    prev_d = None
    for i in range(len(st)):
        val = _safe(st.iloc[i][st_col])
        d = _safe(st.iloc[i][dir_col])
        if val is not None:
            row = {"time": int(df.iloc[i]['time']), "value": val, "direction": d}
            if prev_d is not None and prev_d == -1 and d == 1:
                row["buySignal"] = True
            if prev_d is not None and prev_d == 1 and d == -1:
                row["sellSignal"] = True
            out.append(row)
        if d is not None:
            prev_d = d
    return out

def _compute_fts(df, p):
    trailType = p.get('trailType', 'modified')
    ATRPeriod = int(p.get('ATRPeriod', 28))
    ATRFactor = float(p.get('ATRFactor', 5))
    show_fib_entries = p.get('show_fib_entries', True)
    
    if len(df) == 0:
        return []
        
    out = []
    
    # Pre-calculate arrays
    h = df['high'].values
    l = df['low'].values
    c = df['close'].values
    
    # SMA of (h-l)
    hl_diff = h - l
    sma_hl = pd.Series(hl_diff).rolling(window=ATRPeriod, min_periods=1).mean().values
    
    # Calculate trueRange
    trueRange = np.zeros(len(df))
    for i in range(len(df)):
        if i == 0:
            trueRange[i] = hl_diff[i]
            continue
            
        if trailType == 'modified':
            HiLo = min(hl_diff[i], 1.5 * sma_hl[i])
            HRef = (h[i] - c[i-1]) if l[i] <= h[i-1] else (h[i] - c[i-1]) - 0.5 * (l[i] - h[i-1])
            LRef = (c[i-1] - l[i]) if h[i] >= l[i-1] else (c[i-1] - l[i]) - 0.5 * (l[i-1] - h[i])
            trueRange[i] = max(HiLo, HRef, LRef)
        else:
            trueRange[i] = max(hl_diff[i], abs(h[i] - c[i-1]), abs(l[i] - c[i-1]))
            
    # Wilder's MA of trueRange
    wild_ma = np.zeros(len(df))
    wild_val = 0.0
    for i in range(len(df)):
        wild_val = wild_val + (trueRange[i] - wild_val) / ATRPeriod
        wild_ma[i] = wild_val
        
    loss = ATRFactor * wild_ma
    
    Up = c - loss
    Dn = c + loss
    
    TrendUp = np.zeros(len(df))
    TrendDown = np.zeros(len(df))
    Trend = np.zeros(len(df), dtype=int)
    trail = np.zeros(len(df))
    ex = np.zeros(len(df))
    state = np.full(len(df), "long", dtype=object)
    
    f1 = np.zeros(len(df))
    f2 = np.zeros(len(df))
    f3 = np.zeros(len(df))
    
    for i in range(len(df)):
        if i == 0:
            TrendUp[i] = Up[i]
            TrendDown[i] = Dn[i]
            Trend[i] = 1
            trail[i] = TrendUp[i]
            ex[i] = h[i]
            state[i] = "long"
            f1[i] = f2[i] = f3[i] = trail[i]
            continue
            
        TrendUp[i] = max(Up[i], TrendUp[i-1]) if c[i-1] > TrendUp[i-1] else Up[i]
        TrendDown[i] = min(Dn[i], TrendDown[i-1]) if c[i-1] < TrendDown[i-1] else Dn[i]
        
        if c[i] > TrendDown[i-1]:
            Trend[i] = 1
        elif c[i] < TrendUp[i-1]:
            Trend[i] = -1
        else:
            Trend[i] = Trend[i-1] if Trend[i-1] != 0 else 1
            
        trail[i] = TrendUp[i] if Trend[i] == 1 else TrendDown[i]
        
        if Trend[i] == 1 and Trend[i-1] == -1:
            ex[i] = h[i]
        elif Trend[i] == -1 and Trend[i-1] == 1:
            ex[i] = l[i]
        elif Trend[i] == 1:
            ex[i] = max(ex[i-1], h[i])
        elif Trend[i] == -1:
            ex[i] = min(ex[i-1], l[i])
        else:
            ex[i] = ex[i-1]
            
        state[i] = "long" if Trend[i] == 1 else "short"
        
        f1[i] = ex[i] + (trail[i] - ex[i]) * 0.618
        f2[i] = ex[i] + (trail[i] - ex[i]) * 0.786
        f3[i] = ex[i] + (trail[i] - ex[i]) * 0.886
        
    atr = pd.Series(trueRange).rolling(window=14, min_periods=1).mean().values
        
    for i in range(1, len(df)):
        row = {
            "time": int(df.iloc[i]['time']),
            "trail": float(trail[i]),
            "ex": float(ex[i]),
            "f1": float(f1[i]),
            "f2": float(f2[i]),
            "f3": float(f3[i]),
            "l100": float(trail[i]),
            "trend": int(Trend[i]),
            "state": str(state[i])
        }
        
        if show_fib_entries:
            if state[i-1] == "long":
                if c[i-1] >= f1[i-1] and c[i] < f1[i-1]: row["l1"] = float(l[i] - atr[i])
                if c[i-1] >= f2[i-1] and c[i] < f2[i-1]: row["l2"] = float(l[i] - 1.5 * atr[i])
                if c[i-1] >= f3[i-1] and c[i] < f3[i-1]: row["l3"] = float(l[i] - 2 * atr[i])
            elif state[i-1] == "short":
                if c[i-1] <= f1[i-1] and c[i] > f1[i-1]: row["s1"] = float(h[i] + atr[i])
                if c[i-1] <= f2[i-1] and c[i] > f2[i-1]: row["s2"] = float(h[i] + 1.5 * atr[i])
                if c[i-1] <= f3[i-1] and c[i] > f3[i-1]: row["s3"] = float(h[i] + 2 * atr[i])
                
        out.append(row)
        
    return out

def _compute_ichimoku(df, p):
    ichi, _ = ta.ichimoku(df['high'], df['low'], df['close'],
                          tenkan=int(p.get('tenkan', 9)),
                          kijun=int(p.get('kijun', 26)),
                          senkou=int(p.get('senkou', 52)))
    if ichi is None or ichi.empty:
        return []
    cols = ichi.columns.tolist()
    tenkan_col = [c for c in cols if 'ISA' not in c and 'ISB' not in c and 'ICS' not in c and 'IKS' not in c and 'ITS' in c]
    kijun_col  = [c for c in cols if 'IKS' in c]
    span_a_col = [c for c in cols if 'ISA' in c]
    span_b_col = [c for c in cols if 'ISB' in c]
    chikou_col = [c for c in cols if 'ICS' in c]

    tk = tenkan_col[0] if tenkan_col else None
    kj = kijun_col[0] if kijun_col else None
    sa = span_a_col[0] if span_a_col else None
    sb = span_b_col[0] if span_b_col else None
    cs = chikou_col[0] if chikou_col else None

    out = []
    for i in range(len(ichi)):
        t = int(df.iloc[i]['time']) if i < len(df) else None
        if t is None:
            continue
        row = {}
        row['time'] = t
        if tk: row['tenkan'] = _safe(ichi.iloc[i][tk])
        if kj: row['kijun'] = _safe(ichi.iloc[i][kj])
        if sa: row['spanA'] = _safe(ichi.iloc[i][sa])
        if sb: row['spanB'] = _safe(ichi.iloc[i][sb])
        if cs: row['chikou'] = _safe(ichi.iloc[i][cs])
        # Only include rows that have at least one non-null value
        vals = [v for k, v in row.items() if k != 'time']
        if any(v is not None for v in vals):
            out.append(row)
    return out

def _compute_donchian(df, p):
    length = int(p.get('length', 20))
    dc = ta.donchian(df['high'], df['low'], lower_length=length, upper_length=length)
    if dc is None or dc.empty:
        return []
    dcl = [c for c in dc.columns if c.startswith('DCL')][0]
    dcm = [c for c in dc.columns if c.startswith('DCM')][0]
    dcu = [c for c in dc.columns if c.startswith('DCU')][0]
    out = []
    for i in range(len(dc)):
        l, m, u = _safe(dc.iloc[i][dcl]), _safe(dc.iloc[i][dcm]), _safe(dc.iloc[i][dcu])
        if l is not None:
            out.append({"time": int(df.iloc[i]['time']), "lower": l, "middle": m, "upper": u})
    return out

def _compute_kc(df, p):
    length = int(p.get('length', 20))
    kc = ta.kc(df['high'], df['low'], df['close'], length=length)
    if kc is None or kc.empty:
        return []
    kcl = [c for c in kc.columns if c.startswith('KCL')][0]
    kcb = [c for c in kc.columns if c.startswith('KCB')][0]
    kcu = [c for c in kc.columns if c.startswith('KCU')][0]
    out = []
    for i in range(len(kc)):
        l, m, u = _safe(kc.iloc[i][kcl]), _safe(kc.iloc[i][kcb]), _safe(kc.iloc[i][kcu])
        if l is not None:
            out.append({"time": int(df.iloc[i]['time']), "lower": l, "middle": m, "upper": u})
    return out

def _compute_psar(df, p):
    af = float(p.get('af', 0.02))
    max_af = float(p.get('max_af', 0.2))
    psar = ta.psar(df['high'], df['low'], df['close'], af0=af, af=af, max_af=max_af)
    if psar is None or psar.empty:
        return []
    long_col = [c for c in psar.columns if 'PSARl' in c]
    short_col = [c for c in psar.columns if 'PSARs' in c]
    lc = long_col[0] if long_col else None
    sc = short_col[0] if short_col else None
    out = []
    for i in range(len(psar)):
        t = int(df.iloc[i]['time'])
        lv = _safe(psar.iloc[i][lc]) if lc else None
        sv = _safe(psar.iloc[i][sc]) if sc else None
        if lv is not None or sv is not None:
            out.append({"time": t, "long": lv, "short": sv})
    return out

# ── Oscillator / osc ──────────────────────────────────────────────────────

def _compute_rsi(df, p):
    length = int(p.get('length', 14))
    s = ta.rsi(df['close'], length=length)
    out = []
    for i, v in enumerate(s):
        if _safe(v) is not None:
            out.append({"time": int(df.iloc[i]['time']), "value": _safe(v)})
    return out

def _compute_cci(df, p):
    length = int(p.get('length', 20))
    s = ta.cci(df['high'], df['low'], df['close'], length=length)
    out = []
    for i, v in enumerate(s):
        if _safe(v) is not None:
            out.append({"time": int(df.iloc[i]['time']), "value": _safe(v)})
    return out

def _compute_willr(df, p):
    length = int(p.get('length', 14))
    s = ta.willr(df['high'], df['low'], df['close'], length=length)
    out = []
    for i, v in enumerate(s):
        if _safe(v) is not None:
            out.append({"time": int(df.iloc[i]['time']), "value": _safe(v)})
    return out

def _compute_roc(df, p):
    length = int(p.get('length', 10))
    s = ta.roc(df['close'], length=length)
    out = []
    for i, v in enumerate(s):
        if _safe(v) is not None:
            out.append({"time": int(df.iloc[i]['time']), "value": _safe(v)})
    return out

def _compute_mfi(df, p):
    length = int(p.get('length', 14))
    if 'volume' not in df.columns:
        return []
    s = ta.mfi(df['high'], df['low'], df['close'], df['volume'], length=length)
    out = []
    for i, v in enumerate(s):
        if _safe(v) is not None:
            out.append({"time": int(df.iloc[i]['time']), "value": _safe(v)})
    return out

def _compute_cmo(df, p):
    length = int(p.get('length', 14))
    s = ta.cmo(df['close'], length=length)
    out = []
    for i, v in enumerate(s):
        if _safe(v) is not None:
            out.append({"time": int(df.iloc[i]['time']), "value": _safe(v)})
    return out

def _compute_tsi(df, p):
    fast = int(p.get('fast', 13))
    slow = int(p.get('slow', 25))
    s = ta.tsi(df['close'], fast=fast, slow=slow)
    if s is None:
        return []
    # tsi returns a DataFrame with TSI and Signal columns
    if isinstance(s, pd.DataFrame):
        tsi_col = [c for c in s.columns if c.startswith('TSI')][0]
        out = []
        for i in range(len(s)):
            v = _safe(s.iloc[i][tsi_col])
            if v is not None:
                out.append({"time": int(df.iloc[i]['time']), "value": v})
        return out
    else:
        out = []
        for i, v in enumerate(s):
            if _safe(v) is not None:
                out.append({"time": int(df.iloc[i]['time']), "value": _safe(v)})
        return out

def _compute_ao(df, p):
    fast = int(p.get('fast', 5))
    slow = int(p.get('slow', 34))
    s = ta.ao(df['high'], df['low'], fast=fast, slow=slow)
    out = []
    for i, v in enumerate(s):
        if _safe(v) is not None:
            out.append({"time": int(df.iloc[i]['time']), "value": _safe(v)})
    return out

# ── Oscillator / lines ────────────────────────────────────────────────────

def _compute_macd(df, p):
    fast = int(p.get('fast', 12))
    slow = int(p.get('slow', 26))
    signal = int(p.get('signal', 9))
    macd = ta.macd(df['close'], fast=fast, slow=slow, signal=signal)
    if macd is None or macd.empty:
        return []
    m_col = [c for c in macd.columns if c.startswith('MACD_')][0]
    h_col = [c for c in macd.columns if c.startswith('MACDh_')][0]
    s_col = [c for c in macd.columns if c.startswith('MACDs_')][0]
    out = []
    for i in range(len(macd)):
        mv = _safe(macd.iloc[i][m_col])
        if mv is not None:
            out.append({
                "time": int(df.iloc[i]['time']),
                "macd": mv,
                "signal": _safe(macd.iloc[i][s_col]),
                "hist": _safe(macd.iloc[i][h_col])
            })
    return out

def _compute_stoch(df, p):
    k = int(p.get('k', 14))
    d = int(p.get('d', 3))
    smooth_k = int(p.get('smooth_k', 3))
    stoch = ta.stoch(df['high'], df['low'], df['close'], k=k, d=d, smooth_k=smooth_k)
    if stoch is None or stoch.empty:
        return []
    k_col = [c for c in stoch.columns if c.startswith('STOCHk')][0]
    d_col = [c for c in stoch.columns if c.startswith('STOCHd')][0]
    out = []
    for i in range(len(stoch)):
        kv = _safe(stoch.iloc[i][k_col])
        if kv is not None:
            out.append({
                "time": int(df.iloc[i]['time']),
                "k": kv,
                "d": _safe(stoch.iloc[i][d_col])
            })
    return out

def _compute_stochrsi(df, p):
    length = int(p.get('length', 14))
    rsi_length = int(p.get('rsi_length', 14))
    k = int(p.get('k', 3))
    d = int(p.get('d', 3))
    sr = ta.stochrsi(df['close'], length=length, rsi_length=rsi_length, k=k, d=d)
    if sr is None or sr.empty:
        return []
    k_col = [c for c in sr.columns if c.startswith('STOCHRSIk')][0]
    d_col = [c for c in sr.columns if c.startswith('STOCHRSId')][0]
    out = []
    for i in range(len(sr)):
        kv = _safe(sr.iloc[i][k_col])
        if kv is not None:
            out.append({
                "time": int(df.iloc[i]['time']),
                "k": kv,
                "d": _safe(sr.iloc[i][d_col])
            })
    return out

# ── Trend / osc ───────────────────────────────────────────────────────────

def _compute_adx(df, p):
    length = int(p.get('length', 14))
    adx = ta.adx(df['high'], df['low'], df['close'], length=length)
    if adx is None or adx.empty:
        return []
    adx_col = [c for c in adx.columns if c.startswith('ADX_')][0]
    dmp_col = [c for c in adx.columns if c.startswith('DMP_')][0]
    dmn_col = [c for c in adx.columns if c.startswith('DMN_')][0]
    out = []
    for i in range(len(adx)):
        av = _safe(adx.iloc[i][adx_col])
        if av is not None:
            out.append({
                "time": int(df.iloc[i]['time']),
                "adx": av,
                "plus_di": _safe(adx.iloc[i][dmp_col]),
                "minus_di": _safe(adx.iloc[i][dmn_col])
            })
    return out

def _compute_aroon(df, p):
    length = int(p.get('length', 25))
    ar = ta.aroon(df['high'], df['low'], length=length)
    if ar is None or ar.empty:
        return []
    up_col = [c for c in ar.columns if 'AROONU' in c][0]
    dn_col = [c for c in ar.columns if 'AROOND' in c][0]
    osc_col = [c for c in ar.columns if 'AROONOSC' in c]
    out = []
    for i in range(len(ar)):
        uv = _safe(ar.iloc[i][up_col])
        if uv is not None:
            row = {
                "time": int(df.iloc[i]['time']),
                "up": uv,
                "down": _safe(ar.iloc[i][dn_col])
            }
            if osc_col:
                row['osc'] = _safe(ar.iloc[i][osc_col[0]])
            out.append(row)
    return out

def _compute_vortex(df, p):
    length = int(p.get('length', 14))
    vx = ta.vortex(df['high'], df['low'], df['close'], length=length)
    if vx is None or vx.empty:
        return []
    vip_col = [c for c in vx.columns if 'VTXP' in c][0]
    vim_col = [c for c in vx.columns if 'VTXM' in c][0]
    out = []
    for i in range(len(vx)):
        pv = _safe(vx.iloc[i][vip_col])
        if pv is not None:
            out.append({
                "time": int(df.iloc[i]['time']),
                "plus": pv,
                "minus": _safe(vx.iloc[i][vim_col])
            })
    return out

def _compute_srchannel(df, p):
    prd = int(p.get('prd', 10))
    loopback = int(p.get('loopback', 290))
    out = []
    
    highs = df['high'].values
    lows = df['low'].values
    
    ph = [False] * len(df)
    pl = [False] * len(df)
    
    for i in range(prd, len(df) - prd):
        if highs[i] == max(highs[i-prd : i+prd+1]): ph[i] = True
        if lows[i] == min(lows[i-prd : i+prd+1]): pl[i] = True
        
    for i in range(len(df)):
        if i < loopback:
            out.append({"time": int(df['time'].iloc[i])})
            continue
            
        lb_start = i - loopback
        recent_ph = [highs[j] for j in range(lb_start, i - prd) if ph[j]]
        recent_pl = [lows[j] for j in range(lb_start, i - prd) if pl[j]]
        
        res = max(recent_ph) if recent_ph else None
        sup = min(recent_pl) if recent_pl else None
        
        row = {"time": int(df['time'].iloc[i])}
        if res is not None: row["resistance"] = float(res)
        if sup is not None: row["support"] = float(sup)
        out.append(row)
        
    return out

# ── Volume / osc ──────────────────────────────────────────────────────────

def _compute_vppa(df, p):
    pvt_len = int(p.get('pvtLength', 20))
    va_pct = float(p.get('isValueArea', 68)) / 100.0
    levels = int(p.get('profileLevels', 25))
    
    if 'volume' not in df.columns:
        return []
        
    out = []
    last_pivot_idx = 0
    
    for i in range(len(df)):
        if i >= 2 * pvt_len:
            window_high = df['high'].iloc[i - 2 * pvt_len : i + 1]
            if df['high'].iloc[i - pvt_len] == window_high.max():
                last_pivot_idx = i - pvt_len
            window_low = df['low'].iloc[i - 2 * pvt_len : i + 1]
            if df['low'].iloc[i - pvt_len] == window_low.min():
                last_pivot_idx = i - pvt_len
                
        start_idx = last_pivot_idx if last_pivot_idx > 0 else 0
        chunk = df.iloc[start_idx : i + 1]
        
        if len(chunk) < 2:
            out.append({"time": int(df['time'].iloc[i])})
            continue
            
        high_price = chunk['high'].max()
        low_price = chunk['low'].min()
        if high_price == low_price:
            out.append({"time": int(df['time'].iloc[i]), "poc": float(high_price), "vah": float(high_price), "val": float(low_price)})
            continue
            
        step = (high_price - low_price) / levels
        if step == 0: step = 1
        vol_profile = [0.0] * levels
        
        for j in range(len(chunk)):
            h = float(chunk['high'].iloc[j])
            l = float(chunk['low'].iloc[j])
            v = float(chunk['volume'].iloc[j])
            
            for lvl in range(levels):
                lvl_price_low = low_price + lvl * step
                lvl_price_high = low_price + (lvl + 1) * step
                if h >= lvl_price_low and l <= lvl_price_high:
                    overlap = min(h, lvl_price_high) - max(l, lvl_price_low)
                    tot = h - l
                    if tot > 0:
                        vol_profile[lvl] += v * (overlap / tot)
                    else:
                        vol_profile[lvl] += v
                        
        poc_idx = vol_profile.index(max(vol_profile))
        poc = low_price + (poc_idx + 0.5) * step
        
        total_vol = sum(vol_profile)
        va_vol_target = total_vol * va_pct
        va_vol = vol_profile[poc_idx]
        up_idx = poc_idx
        dn_idx = poc_idx
        
        while va_vol < va_vol_target:
            if dn_idx == 0 and up_idx == levels - 1: break
            vol_up = vol_profile[up_idx + 1] if up_idx < levels - 1 else 0
            vol_dn = vol_profile[dn_idx - 1] if dn_idx > 0 else 0
            if vol_up == 0 and vol_dn == 0: break
            if vol_up >= vol_dn:
                va_vol += vol_up
                up_idx += 1
            else:
                va_vol += vol_dn
                dn_idx -= 1
                
        vah = low_price + (up_idx + 1) * step
        val = low_price + dn_idx * step
        
        out.append({
            "time": int(df['time'].iloc[i]),
            "poc": float(poc),
            "vah": float(vah),
            "val": float(val)
        })
        
    return out


def _compute_vp(df, p):
    lookback = int(p.get('lookback_depth', 200))
    va_pct = float(p.get('va_percent', 68)) / 100.0
    levels = int(p.get('num_bars', 200))
    
    if 'volume' not in df.columns:
        return []
        
    out = []
    
    for i in range(len(df)):
        if i < 2:
            out.append({"time": int(df['time'].iloc[i])})
            continue
            
        start_idx = max(0, i - lookback + 1)
        chunk = df.iloc[start_idx : i + 1]
        
        high_price = chunk['high'].max()
        low_price = chunk['low'].min()
        if high_price == low_price:
            out.append({"time": int(df['time'].iloc[i]), "poc": float(high_price), "vah": float(high_price), "val": float(low_price)})
            continue
            
        step = (high_price - low_price) / levels
        if step == 0: step = 1
        vol_profile = [0.0] * levels
        
        chunk_high = chunk['high'].values
        chunk_low = chunk['low'].values
        chunk_vol = chunk['volume'].values
        
        for j in range(len(chunk)):
            h = float(chunk_high[j])
            l = float(chunk_low[j])
            v = float(chunk_vol[j])
            
            for lvl in range(levels):
                lvl_price_low = low_price + lvl * step
                lvl_price_high = low_price + (lvl + 1) * step
                if h >= lvl_price_low and l <= lvl_price_high:
                    overlap = min(h, lvl_price_high) - max(l, lvl_price_low)
                    tot = h - l
                    if tot > 0:
                        vol_profile[lvl] += v * (overlap / tot)
                    else:
                        vol_profile[lvl] += v
                        
        poc_idx = vol_profile.index(max(vol_profile))
        poc = low_price + (poc_idx + 0.5) * step
        
        total_vol = sum(vol_profile)
        va_vol_target = total_vol * va_pct
        va_vol = vol_profile[poc_idx]
        up_idx = poc_idx
        dn_idx = poc_idx
        
        while va_vol < va_vol_target:
            if dn_idx == 0 and up_idx == levels - 1: break
            vol_up = vol_profile[up_idx + 1] if up_idx < levels - 1 else 0
            vol_dn = vol_profile[dn_idx - 1] if dn_idx > 0 else 0
            if vol_up == 0 and vol_dn == 0: break
            if vol_up >= vol_dn:
                va_vol += vol_up
                up_idx += 1
            else:
                va_vol += vol_dn
                dn_idx -= 1
                
        vah = low_price + (up_idx + 1) * step
        val = low_price + dn_idx * step
        
        out.append({
            "time": int(df['time'].iloc[i]),
            "poc": float(poc),
            "vah": float(vah),
            "val": float(val)
        })
        
    return out

def _compute_vpfr(df, p):
    # Mapping for VP Fixed Range defaults
    # bbars=150, cnum=24, percent=70.0
    p2 = {
        'lookback_depth': p.get('bbars', 150),
        'va_percent': p.get('percent', 70.0),
        'num_bars': p.get('cnum', 24)
    }
    return _compute_vp(df, p2)

def _compute_obv(df, p):
    if 'volume' not in df.columns:
        return []
    s = ta.obv(df['close'], df['volume'])
    out = []
    for i, v in enumerate(s):
        if _safe(v) is not None:
            out.append({"time": int(df.iloc[i]['time']), "value": _safe(v)})
    return out

def _compute_cmf(df, p):
    length = int(p.get('length', 20))
    if 'volume' not in df.columns:
        return []
    s = ta.cmf(df['high'], df['low'], df['close'], df['volume'], length=length)
    out = []
    for i, v in enumerate(s):
        if _safe(v) is not None:
            out.append({"time": int(df.iloc[i]['time']), "value": _safe(v)})
    return out

def _compute_ad(df, p):
    if 'volume' not in df.columns:
        return []
    s = ta.ad(df['high'], df['low'], df['close'], df['volume'])
    out = []
    for i, v in enumerate(s):
        if _safe(v) is not None:
            out.append({"time": int(df.iloc[i]['time']), "value": _safe(v)})
    return out


def _compute_delta_vp(df, p):
    """
    Delta Volume Profile [BigBeluga] — exact port of Pine Script v6.
    Computes on the last bar only (like the original barstate.islast logic).
    Returns a single dict with all profile data for the frontend to render.
    """
    lookback = int(p.get('lookback', 300))

    if 'volume' not in df.columns or len(df) < 2:
        return []

    h = df['high'].values
    l = df['low'].values
    c = df['close'].values
    o = df['open'].values
    vol = df['volume'].values
    times = df['time'].values

    # Clamp lookback to available data
    actual_lb = min(lookback, len(df))

    # --- ATR(200) at last bar ---
    tr = np.zeros(len(df))
    for i in range(len(df)):
        if i == 0:
            tr[i] = h[i] - l[i]
        else:
            tr[i] = max(h[i] - l[i], abs(h[i] - c[i-1]), abs(l[i] - c[i-1]))
    atr_period = min(200, len(df))
    atr = float(np.mean(tr[-atr_period:]))
    if atr <= 0:
        return []

    # --- Find max/min over lookback ---
    slice_h = h[-actual_lb:]
    slice_l = l[-actual_lb:]
    price_max = float(np.max(slice_h))
    price_min = float(np.min(slice_l))

    if price_max == price_min:
        return []

    bins = int((price_max - price_min) / atr)
    if bins < 1:
        bins = 1
    if bins > 200:
        bins = 200  # safety cap

    step = (price_max - price_min) / bins

    # --- Accumulate volume per bin ---
    vol_plus = [0.0] * bins
    vol_minus = [0.0] * bins

    start_idx = len(df) - actual_lb
    for i in range(start_idx, len(df)):
        bar_h = h[i]
        bar_l = l[i]
        bar_c = c[i]
        bar_o = o[i]
        bar_v = vol[i]

        for k in range(bins):
            loww = price_min + step * k
            mid = loww + step / 2.0

            if bar_h > mid and bar_l < mid:
                if bar_c > bar_o:
                    vol_plus[k] += bar_v
                else:
                    vol_minus[k] += bar_v

    # --- Compute totals ---
    sum_plus = sum(vol_plus)
    sum_minus = sum(vol_minus)
    total_vol = sum_plus + sum_minus

    if sum_plus == 0 and sum_minus == 0:
        return []

    max_vol_plus = max(vol_plus) if sum_plus > 0 else 0
    min_vol_plus = min(v for v in vol_plus if v > 0) if any(v > 0 for v in vol_plus) else 0
    max_vol_minus = max(vol_minus) if sum_minus > 0 else 0
    min_vol_minus = min(v for v in vol_minus if v > 0) if any(v > 0 for v in vol_minus) else 0

    # Delta = ((sum_plus - sum_minus) / sum_minus) * 100
    delta_pct = ((sum_plus - sum_minus) / sum_minus * 100) if sum_minus > 0 else (100.0 if sum_plus > 0 else 0.0)

    # --- Build bins data ---
    bins_data = []
    for k in range(bins):
        loww = price_min + step * k
        highh = loww + step

        # Normalized width (0-200 scale, like Pine Script)
        vp = int(vol_plus[k] / sum_plus * 200) if sum_plus > 0 else 0
        vm = int(vol_minus[k] / sum_minus * 200) if sum_minus > 0 else 0

        is_poc_plus = bool(vol_plus[k] == max_vol_plus and max_vol_plus > 0)
        is_poc_minus = bool(vol_minus[k] == max_vol_minus and max_vol_minus > 0)

        bins_data.append({
            "low": float(loww),
            "high": float(highh),
            "volPlus": float(vol_plus[k]),
            "volMinus": float(vol_minus[k]),
            "widthPlus": int(vp),
            "widthMinus": int(vm),
            "isPocPlus": is_poc_plus,
            "isPocMinus": is_poc_minus,
        })

    # Return a single-element list with profile data
    return [{
        "lookback": actual_lb,
        "startTime": int(times[-actual_lb]),
        "endTime": int(times[-1]),
        "priceMax": float(price_max),
        "priceMin": float(price_min),
        "bins": bins_data,
        "delta": float(delta_pct),
        "totalVol": float(total_vol),
        "sumPlus": float(sum_plus),
        "sumMinus": float(sum_minus),
    }]


# ---------------------------------------------------------------------------
# REGISTRY
# ---------------------------------------------------------------------------

INDICATORS = {
    # ── Overlap / line ────────────────────────────────────────────────────
    "ema":   {"name": "EMA",   "category": "Overlap", "render": "line",  "params": {"length": 20},  "compute": _compute_ema},
    "sma":   {"name": "SMA",   "category": "Overlap", "render": "line",  "params": {"length": 50},  "compute": _compute_sma},
    "wma":   {"name": "WMA",   "category": "Overlap", "render": "line",  "params": {"length": 20},  "compute": _compute_wma},
    "hma":   {"name": "HMA",   "category": "Overlap", "render": "line",  "params": {"length": 20},  "compute": _compute_hma},
    "dema":  {"name": "DEMA",  "category": "Overlap", "render": "line",  "params": {"length": 20},  "compute": _compute_dema},
    "tema":  {"name": "TEMA",  "category": "Overlap", "render": "line",  "params": {"length": 20},  "compute": _compute_tema},
    "kama":  {"name": "KAMA",  "category": "Overlap", "render": "line",  "params": {"length": 10},  "compute": _compute_kama},
    "vwap":  {"name": "VWAP",  "category": "Overlap", "render": "line",  "params": {},              "compute": _compute_vwap},

    # ── Overlap / lines ───────────────────────────────────────────────────
    "bbands":     {"name": "Bollinger Bands", "category": "Volatility", "render": "lines", "params": {"length": 20},
                   "series": ["lower", "middle", "upper"], "compute": _compute_bbands},
    "supertrend": {"name": "Supertrend",      "category": "Overlap",    "render": "lines_markers", "params": {"length": 10, "multiplier": 3},
                   "series": ["value", "direction"], "compute": _compute_supertrend},
    "ichimoku":   {"name": "Ichimoku Cloud",  "category": "Overlap",    "render": "lines", "params": {"tenkan": 9, "kijun": 26, "senkou": 52},
                   "series": ["tenkan", "kijun", "spanA", "spanB", "chikou"], "compute": _compute_ichimoku},
    "donchian":   {"name": "Donchian Channel","category": "Volatility", "render": "lines", "params": {"length": 20},
                   "series": ["lower", "middle", "upper"], "compute": _compute_donchian},
    "kc":         {"name": "Keltner Channel", "category": "Volatility", "render": "lines", "params": {"length": 20},
                   "series": ["lower", "middle", "upper"], "compute": _compute_kc},
    "psar":       {"name": "Parabolic SAR",   "category": "Overlap",    "render": "lines", "params": {"af": 0.02, "max_af": 0.2},
                   "series": ["long", "short"], "compute": _compute_psar},
    "srchannel":  {"name": "Support Resistance", "category": "Overlap", "render": "lines", "params": {"prd": 10, "loopback": 290},
                   "series": ["resistance", "support"], "compute": _compute_srchannel},
    "fts":        {"name": "Blackflag FTS",   "category": "Overlap", "render": "fts", "params": {"trailType": "modified", "ATRPeriod": 28, "ATRFactor": 5, "show_fib_entries": True},
                   "series": ["trail", "ex", "f1", "f2", "f3", "l100"], "compute": _compute_fts},

    # ── Momentum / osc ────────────────────────────────────────────────────
    "rsi":    {"name": "RSI",            "category": "Momentum", "render": "osc",   "params": {"length": 14},           "compute": _compute_rsi,
               "guides": [30, 70]},
    "cci":    {"name": "CCI",            "category": "Momentum", "render": "osc",   "params": {"length": 20},           "compute": _compute_cci,
               "guides": [-100, 100]},
    "willr":  {"name": "Williams %R",    "category": "Momentum", "render": "osc",   "params": {"length": 14},           "compute": _compute_willr,
               "guides": [-80, -20]},
    "roc":    {"name": "ROC",            "category": "Momentum", "render": "osc",   "params": {"length": 10},           "compute": _compute_roc,
               "guides": [0]},
    "mfi":    {"name": "MFI",            "category": "Momentum", "render": "osc",   "params": {"length": 14},           "compute": _compute_mfi,
               "guides": [20, 80]},
    "cmo":    {"name": "CMO",            "category": "Momentum", "render": "osc",   "params": {"length": 14},           "compute": _compute_cmo,
               "guides": [-50, 50]},
    "tsi":    {"name": "TSI",            "category": "Momentum", "render": "osc",   "params": {"fast": 13, "slow": 25}, "compute": _compute_tsi,
               "guides": [0]},
    "ao":     {"name": "Awesome Osc",    "category": "Momentum", "render": "osc",   "params": {"fast": 5, "slow": 34},  "compute": _compute_ao,
               "guides": [0]},

    # ── Momentum / lines (oscillator pane) ────────────────────────────────
    "macd":     {"name": "MACD",         "category": "Momentum", "render": "lines_osc", "params": {"fast": 12, "slow": 26, "signal": 9},
                 "series": ["macd", "signal", "hist"], "compute": _compute_macd},
    "stoch":    {"name": "Stochastic",   "category": "Momentum", "render": "lines_osc", "params": {"k": 14, "d": 3, "smooth_k": 3},
                 "series": ["k", "d"], "guides": [20, 80], "compute": _compute_stoch},
    "stochrsi": {"name": "Stoch RSI",    "category": "Momentum", "render": "lines_osc", "params": {"length": 14, "rsi_length": 14, "k": 3, "d": 3},
                 "series": ["k", "d"], "guides": [20, 80], "compute": _compute_stochrsi},

    # ── Trend / osc ───────────────────────────────────────────────────────
    "adx":    {"name": "ADX",            "category": "Trend", "render": "lines_osc", "params": {"length": 14},
               "series": ["adx", "plus_di", "minus_di"], "guides": [25], "compute": _compute_adx},
    "aroon":  {"name": "Aroon",          "category": "Trend", "render": "lines_osc", "params": {"length": 25},
               "series": ["up", "down"], "guides": [50], "compute": _compute_aroon},
    "vortex": {"name": "Vortex",         "category": "Trend", "render": "lines_osc", "params": {"length": 14},
               "series": ["plus", "minus"], "guides": [1], "compute": _compute_vortex},

    # ── Volume / osc ─────────────────────────────────────────────────────
    "vppa":     {"name": "VP Pivot Anchored", "category": "Volume", "render": "lines", "params": {"pvtLength": 20, "isValueArea": 68, "profileLevels": 25},
                 "series": ["poc", "vah", "val"], "compute": _compute_vppa},
    "vp":       {"name": "Volume Profile", "category": "Volume", "render": "lines", "params": {"lookback_depth": 200, "va_percent": 68, "num_bars": 200},
                 "series": ["poc", "vah", "val"], "compute": _compute_vp},
    "vpfr":     {"name": "VP Fixed Range", "category": "Volume", "render": "lines", "params": {"bbars": 150, "percent": 70, "cnum": 24},
                 "series": ["poc", "vah", "val"], "compute": _compute_vpfr},
    "obv": {"name": "OBV",              "category": "Volume", "render": "osc", "params": {},           "compute": _compute_obv},
    "cmf": {"name": "CMF",              "category": "Volume", "render": "osc", "params": {"length": 20}, "compute": _compute_cmf,
            "guides": [0]},
    "ad":  {"name": "A/D Line",         "category": "Volume", "render": "osc", "params": {},           "compute": _compute_ad},
    "delta_vp": {"name": "Delta Volume Profile", "category": "Volume", "render": "delta_vp", "params": {"lookback": 300},
                 "compute": _compute_delta_vp},
}


def get_indicator_list():
    """Return the list of available indicators for the frontend popover."""
    result = []
    for key, meta in INDICATORS.items():
        entry = {
            "id": key,
            "name": meta["name"],
            "category": meta["category"],
            "render": meta["render"],
            "params": meta["params"],
        }
        if "series" in meta:
            entry["series"] = meta["series"]
        if "guides" in meta:
            entry["guides"] = meta["guides"]
        result.append(entry)
    return result


def calculate_indicator(bars, indicator_name, extra_params=None):
    """
    Calculate a single indicator and return:
    {
        "render": "<render_type>",
        "series": [...series names...],   # for multi-series
        "guides": [30, 70],               # guide lines (optional)
        "data": [ ... ]
    }
    """
    if not bars:
        return {"error": "no bars data", "data": []}

    indicator_name = indicator_name.lower()
    if indicator_name not in INDICATORS:
        return {"error": f"unknown indicator: {indicator_name}", "data": []}

    meta = INDICATORS[indicator_name]

    df = pd.DataFrame(bars)
    for col in ['open', 'high', 'low', 'close']:
        df[col] = df[col].astype(float)
    if 'volume' in df.columns:
        df['volume'] = df['volume'].astype(float)

    # Merge default params with any overrides
    params = dict(meta["params"])
    if extra_params:
        params.update(extra_params)

    try:
        data = meta["compute"](df, params)
    except Exception as e:
        print(f"Error computing {indicator_name}: {e}")
        return {"error": str(e), "data": []}

    result = {
        "render": meta["render"],
        "data": data,
    }
    if "series" in meta:
        result["series"] = meta["series"]
    if "guides" in meta:
        result["guides"] = meta["guides"]

    return result
