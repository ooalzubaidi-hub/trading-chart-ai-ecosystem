import urllib.request, json
try:
    with urllib.request.urlopen('http://127.0.0.1:5000/api/indicator-list', timeout=10) as resp:
        data = json.loads(resp.read())
        print("Status: 200 OK")
        print("Length:", len(data))
except Exception as e:
    print("Error:", e)
