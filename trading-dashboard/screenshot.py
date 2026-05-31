from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    
    page.on("console", lambda msg: print(f"Browser Console: {msg.text}"))
    page.on("pageerror", lambda err: print(f"Browser Error: {err.message}"))
    
    page.goto('http://localhost:5000/command')
    
    # Wait for the lightweight charts to initialize and load data
    time.sleep(5) 
    
    # Take a full page screenshot
    page.screenshot(path='screenshot_command.png')
    browser.close()
    print("Screenshot saved to screenshot_command.png")
