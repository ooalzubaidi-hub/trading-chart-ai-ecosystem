import pandas as pd
from smartmoneyconcepts import smc

# Create dummy OHLCV data
data = {
    'open': [100, 102, 101, 105, 104, 108, 107, 110, 109, 115, 114, 120, 118, 125, 124],
    'high': [103, 105, 104, 107, 106, 110, 109, 112, 111, 117, 116, 122, 120, 127, 126],
    'low': [98, 100, 99, 103, 102, 106, 105, 108, 107, 113, 112, 118, 116, 123, 122],
    'close': [102, 101, 105, 104, 108, 107, 110, 109, 115, 114, 120, 118, 125, 124, 130],
    'volume': [1000] * 15
}
df = pd.DataFrame(data)

# Test FVG
fvg = smc.fvg(df)
print("FVG:")
print(fvg.tail())

try:
    swing = smc.swing_highs_lows(df)
    print("\nSwing Highs/Lows:")
    print(swing.head(10))
    
    ob = smc.ob(df, swing)
    print("\nOB:")
    print(ob.head(10))
    
    bos = smc.bos_choch(df, swing)
    print("\nBOS/CHoCH:")
    print(bos.head(10))
    
    liq = smc.liquidity(df, swing)
    print("\nLiquidity:")
    print(liq.head(10))
except Exception as e:
    print("Error:", e)

try:
    swing = smc.swing_highs_lows(df)
    print("\nSwing Highs/Lows:")
    print(swing.tail())
except Exception as e:
    print("Swing error:", e)
