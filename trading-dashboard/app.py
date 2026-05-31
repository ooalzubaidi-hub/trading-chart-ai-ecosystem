from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import data_source
import live_stream

import os

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
CORS(app)

# Start background websocket streams
# Start background websocket streams
live_stream.start_streams()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/symbols')
def symbols():
    return jsonify(data_source.get_symbol_list())

@app.route('/api/bars')
def bars():
    symbol = request.args.get('symbol')
    timeframe = request.args.get('timeframe')
    limit = request.args.get('limit', 500, type=int)
    
    if not symbol:
        return jsonify({"error": "symbol parameter is required"}), 400
        
    if not timeframe:
        return jsonify({"error": "timeframe parameter is required"}), 400
        
    bars_data = data_source.get_historical_bars(symbol, timeframe, limit)
    return jsonify(bars_data)

@app.route('/api/latest')
def latest():
    return jsonify(live_stream.get_latest_prices())

@app.route('/api/indicator-list')
def indicator_list():
    import indicators
    return jsonify(indicators.get_indicator_list())

@app.route('/api/indicator')
def indicator_route():
    symbol = request.args.get('symbol')
    timeframe = request.args.get('timeframe')
    indicator = request.args.get('indicator')
    
    if not all([symbol, timeframe, indicator]):
        return jsonify({"error": "missing parameters"}), 400
    
    # Collect all extra params beyond the core three
    extra_params = {}
    for k, v in request.args.items():
        if k not in ('symbol', 'timeframe', 'indicator'):
            extra_params[k] = v
        
    bars = data_source.get_historical_bars(symbol, timeframe, limit=500)
    import indicators
    result = indicators.calculate_indicator(bars, indicator, extra_params if extra_params else None)
    return jsonify(result)

# ── AI Command Center routes (new page, does NOT affect existing dashboard) ──

@app.route('/command')
def command_center():
    return render_template('command.html')

import threading
import time

LATEST_SNAPSHOT = {"error": "Initializing AI engine, please wait..."}

def update_snapshot_loop():
    global LATEST_SNAPSHOT
    import signal_engine
    while True:
        try:
            snapshot = signal_engine.get_command_snapshot()
            LATEST_SNAPSHOT = snapshot
        except Exception as e:
            print("Background snapshot update error:", e)
        time.sleep(60)

threading.Thread(target=update_snapshot_loop, daemon=True).start()

@app.route('/api/command/snapshot')
def command_snapshot():
    try:
        import json
        import numpy as np
        def _default(o):
            if isinstance(o, (np.integer,)):
                return int(o)
            if isinstance(o, (np.floating,)):
                return float(o)
            if isinstance(o, (np.bool_,)):
                return bool(o)
            if isinstance(o, np.ndarray):
                return o.tolist()
            return str(o)
        
        dumped = json.dumps(LATEST_SNAPSHOT, default=_default)
        return dumped, 200, {'Content-Type': 'application/json'}
    except Exception as e:
        print("ERROR IN SNAPSHOT:", repr(e))
        return '{"error": "Internal Error"}', 500, {'Content-Type': 'application/json'}

@app.route('/api/patterns')
def patterns_route():
    symbol = request.args.get('symbol', 'BTC/USD')
    timeframe = request.args.get('timeframe', '1m')
    limit = request.args.get('limit', 500, type=int)
    
    bars = data_source.get_historical_bars(symbol, timeframe, limit)
    if not bars or len(bars) < 50:
        return jsonify({"error": "Not enough data"}), 400
        
    try:
        import pandas as pd
        from pattern_detector import PatternDetector
        from enhanced_patterns import EnhancedPatternDetector
        
        df = pd.DataFrame(bars)
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        df['t'] = pd.to_datetime(df['time'], unit='s')
        df.rename(columns={'open':'o', 'high':'h', 'low':'l', 'close':'c', 'volume':'v'}, inplace=True)
        df.set_index('t', inplace=True)
        
        detector = PatternDetector(symbol=symbol, interval=timeframe)
        max_min = detector.get_max_min(df, smoothing=3, window_range=3)
        
        patterns_basic = detector.find_patterns(max_min)
        
        enhanced = EnhancedPatternDetector()
        patterns_enhanced = enhanced.detect_all_patterns(df, max_min)
        
        all_patterns = {}
        all_patterns.update(patterns_basic)
        all_patterns.update(patterns_enhanced)
        
        results = []
        for p_name, occurrences in all_patterns.items():
            # Determine bias
            bias = "neutral"
            if p_name in ['IHS', 'DB', 'BULL_FLAG', 'CUP_AND_HANDLE']: bias = "bullish"
            elif p_name in ['HS', 'DT', 'BEAR_FLAG']: bias = "bearish"
            elif 'ASCENDING' in p_name and 'TRIANGLE' in p_name: bias = "bullish"
            elif 'DESCENDING' in p_name and 'TRIANGLE' in p_name: bias = "bearish"
            elif 'RISING' in p_name and 'WEDGE' in p_name: bias = "bearish"
            elif 'FALLING' in p_name and 'WEDGE' in p_name: bias = "bullish"
            
            for (start_t, end_t) in occurrences:
                # Get the actual coordinates for drawing
                start_ts = int(pd.Timestamp(start_t).timestamp()) if hasattr(start_t, 'timestamp') else start_t
                end_ts = int(pd.Timestamp(end_t).timestamp()) if hasattr(end_t, 'timestamp') else end_t
                
                # In basic patterns, occurrences are tuples of (datetime, datetime)
                # In enhanced (e.g. flags), they might be index numbers. Let's handle both.
                if isinstance(start_t, (int, np.integer)):
                    start_ts = int(df.iloc[start_t]['time'])
                    end_ts = int(df.iloc[end_t]['time'])
                    
                results.append({
                    "name": p_name,
                    "bias": bias,
                    "start_time": start_ts,
                    "end_time": end_ts,
                    "strength": "High" if p_name in ['HS', 'IHS', 'DT', 'DB'] else "Medium"
                })
                
        return jsonify(results)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)
