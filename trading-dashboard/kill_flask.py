import psutil, time, sys

killed = False
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if proc.info['cmdline'] and 'python' in proc.info['name'].lower():
            if any('app.py' in cmd for cmd in proc.info['cmdline']):
                print(f"Killing old python process: {proc.info['pid']}")
                proc.kill()
                killed = True
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

if killed:
    print("Waiting 3 seconds for connections to release...")
    time.sleep(3)
else:
    print("No old app.py process found.")
