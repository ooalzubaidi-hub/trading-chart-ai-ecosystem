import data_source
import pandas as pd
import json
import numpy as np

def run_test():
    symbol = 'BTC/USD'
    timeframe = '15m'
    limit = 500
    
    print(f"Fetching data for {symbol} {timeframe}...")
    bars = data_source.get_historical_bars(symbol, timeframe, limit)
    if not bars:
        print("No bars fetched.")
        return
        
    print(f"Fetched {len(bars)} bars.")
    
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
    
    print("Finding basic patterns...")
    patterns_basic = detector.find_patterns(max_min)
    
    print("Finding enhanced patterns...")
    enhanced = EnhancedPatternDetector()
    patterns_enhanced = enhanced.detect_all_patterns(df, max_min)
    
    all_patterns = {}
    all_patterns.update(patterns_basic)
    all_patterns.update(patterns_enhanced)
    
    results = []
    for p_name, occurrences in all_patterns.items():
        bias = "neutral"
        if p_name in ['IHS', 'DB', 'BULL_FLAG', 'CUP_AND_HANDLE']: bias = "bullish"
        elif p_name in ['HS', 'DT', 'BEAR_FLAG']: bias = "bearish"
        elif 'ASCENDING' in p_name and 'TRIANGLE' in p_name: bias = "bullish"
        elif 'DESCENDING' in p_name and 'TRIANGLE' in p_name: bias = "bearish"
        elif 'RISING' in p_name and 'WEDGE' in p_name: bias = "bearish"
        elif 'FALLING' in p_name and 'WEDGE' in p_name: bias = "bullish"
        
        for (start_t, end_t) in occurrences:
            start_ts = int(pd.Timestamp(start_t).timestamp()) if hasattr(start_t, 'timestamp') else start_t
            end_ts = int(pd.Timestamp(end_t).timestamp()) if hasattr(end_t, 'timestamp') else end_t
            
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
            
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    run_test()
