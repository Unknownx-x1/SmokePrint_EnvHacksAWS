import os
import time
import subprocess
from playwright.sync_api import sync_playwright

def capture():
    server = subprocess.Popen(
        ["python", "-m", "http.server", "3008", "--directory", "web/out"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(1.5)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            # Mobile viewport 390x844 (iPhone 12/13/14)
            page = browser.new_page(viewport={"width": 390, "height": 844})
            page.goto("http://localhost:3008/field/case_anand_vihar_20251102/", wait_until="domcontentloaded")
            page.wait_for_timeout(1000)
            os.makedirs("docs/screenshots", exist_ok=True)
            page.screenshot(path="docs/screenshots/field_episode_switcher_fixed.png")
            print("Screenshot successfully saved to docs/screenshots/field_episode_switcher_fixed.png")
            browser.close()
    finally:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(server.pid)], capture_output=True)

if __name__ == "__main__":
    capture()
