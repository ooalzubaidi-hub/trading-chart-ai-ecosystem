import data_source
import indicators
import traceback

print("Fetching data...")
bars = data_source.get_historical_bars('AAPL', '1d', limit=500)
print(f"Got {len(bars)} bars.")

try:
    print("Computing delta_vp...")
    res = indicators.calculate_indicator(bars, 'delta_vp', {'lookback': 300})
    if 'error' in res and res['error']:
        print("Indicator returned error:", res['error'])
    else:
        import json
        print(json.dumps(res))
except Exception as e:
    print("Exception occurred:")
    traceback.print_exc()
