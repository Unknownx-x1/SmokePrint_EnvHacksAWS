import os
from playwright.sync_api import sync_playwright

BASE_URL = "http://smokeprint-demo-k9f2a1.s3-website-us-east-1.amazonaws.com"
QA_DIR = "docs/qa"
os.makedirs(QA_DIR, exist_ok=True)

VISIBLE_CASES = [
    ("case_anand_vihar_20251102", "anand_vihar_nov"),
    ("case_anand_vihar_20260131", "anand_vihar_jan"),
    ("case_rkpuram_20251112", "rkpuram_nov"),
    ("case_crri_20260515", "crri_may"),
    ("case_gurugram_20260630", "gurugram_jun"),
    ("case_regional_smog_20251020", "regional_smog_oct"),
]

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # 1. Desktop context (1280x800)
        ctx_desktop = browser.new_context(viewport={"width": 1280, "height": 800})
        page = ctx_desktop.new_page()

        for cid, label in VISIBLE_CASES:
            print(f"Capturing {cid} (desktop)...")
            page.goto(f"{BASE_URL}/officer/?caseId={cid}", wait_until="domcontentloaded")
            page.wait_for_timeout(1500)
            page.screenshot(path=f"{QA_DIR}/officer_{label}_desktop.png")

        ctx_desktop.close()

        # 2. Mobile context (390x844)
        ctx_mobile = browser.new_context(viewport={"width": 390, "height": 844})
        page_m = ctx_mobile.new_page()

        for cid, label in VISIBLE_CASES:
            print(f"Capturing {cid} (mobile)...")
            page_m.goto(f"{BASE_URL}/field/{cid}/", wait_until="domcontentloaded")
            page_m.wait_for_timeout(1500)
            page_m.screenshot(path=f"{QA_DIR}/field_{label}_mobile.png")

        ctx_mobile.close()
        browser.close()
        print("\nAll 6 visible case QA screenshots retaken successfully.")

if __name__ == "__main__":
    main()
