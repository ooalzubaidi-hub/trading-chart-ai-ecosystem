import urllib.request, json, sys
from urllib.error import HTTPError

try:
    r = urllib.request.urlopen('http://localhost:5000/api/indicator?symbol=AAPL&timeframe=1d&indicator=delta_vp&lookback=300')
    data = json.loads(r.read())
    print('Success!', data.keys())
except HTTPError as e:
    print('HTTP Error:', e.code)
    print('Reason:', e.read().decode('utf-8'))
    sys.exit(1)
except Exception as e:
    print('Error:', e)
    sys.exit(1)
