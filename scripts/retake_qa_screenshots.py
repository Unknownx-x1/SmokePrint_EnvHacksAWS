import os
from playwright.sync_api import sync_playwright

BASE_URL = "http://smokeprint-demo-k9f2a1.s3-website-us-east-1.amazonaws.com"
QA_DIR = "docs/qa"
os.makedirs(QA_DIR, exist_ok=True)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # 1. Desktop context (1280x800)
        ctx_desktop = browser.new_context(viewport={"width": 1280, "height": 800})
        page = ctx_desktop.new_page()

        # Regional smog case
        print("Capturing regional smog case (desktop)...")
        page.goto(f"{BASE_URL}/officer/?caseId=case_regional_smog_20251020", wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        page.screenshot(path=f"{QA_DIR}/officer_case_regional_smog.png")

        # Gurugram case
        print("Capturing Gurugram case (desktop)...")
        page.goto(f"{BASE_URL}/officer/?caseId=case_gurugram_20260630", wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        page.screenshot(path=f"{QA_DIR}/officer_case_gurugram.png")

        # CRRI case
        print("Capturing CRRI case (desktop)...")
        page.goto(f"{BASE_URL}/officer/?caseId=case_crri_20260515", wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        page.screenshot(path=f"{QA_DIR}/officer_case_crri.png")

        # November Anand Vihar case
        print("Capturing Anand Vihar Nov case (desktop)...")
        page.goto(f"{BASE_URL}/officer/?caseId=case_anand_vihar_20251102", wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        page.screenshot(path=f"{QA_DIR}/officer_anand_vihar_nov_desktop.png")

        # November RK Puram case
        print("Capturing RK Puram Nov case (desktop)...")
        page.goto(f"{BASE_URL}/officer/?caseId=case_rkpuram_20251112", wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        page.screenshot(path=f"{QA_DIR}/officer_rkpuram_nov_desktop.png")

        # April Anand Vihar case
        print("Capturing Anand Vihar April case (desktop)...")
        page.goto(f"{BASE_URL}/officer/?caseId=case_anand_vihar_20260405", wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        page.screenshot(path=f"{QA_DIR}/officer_anand_vihar_apr_desktop.png")

        ctx_desktop.close()

        # 2. Mobile context (390x844)
        ctx_mobile = browser.new_context(viewport={"width": 390, "height": 844})
        page_m = ctx_mobile.new_page()

        # Regional smog mobile
        print("Capturing regional smog case (mobile)...")
        page_m.goto(f"{BASE_URL}/field/case_regional_smog_20251020/", wait_until="domcontentloaded")
        page_m.wait_for_timeout(1500)
        page_m.screenshot(path=f"{QA_DIR}/field_case_regional_smog_mobile.png")

        # Gurugram mobile
        print("Capturing Gurugram case (mobile)...")
        page_m.goto(f"{BASE_URL}/field/case_gurugram_20260630/", wait_until="domcontentloaded")
        page_m.wait_for_timeout(1500)
        page_m.screenshot(path=f"{QA_DIR}/field_case_gurugram_mobile.png")

        # CRRI mobile
        print("Capturing CRRI case (mobile)...")
        page_m.goto(f"{BASE_URL}/field/case_crri_20260515/", wait_until="domcontentloaded")
        page_m.wait_for_timeout(1500)
        page_m.screenshot(path=f"{QA_DIR}/field_case_crri_mobile.png")

        # November Anand Vihar mobile
        print("Capturing Anand Vihar Nov case (mobile)...")
        page_m.goto(f"{BASE_URL}/field/case_anand_vihar_20251102/", wait_until="domcontentloaded")
        page_m.wait_for_timeout(1500)
        page_m.screenshot(path=f"{QA_DIR}/field_anand_vihar_nov_mobile.png")

        # November RK Puram mobile
        print("Capturing RK Puram Nov case (mobile)...")
        page_m.goto(f"{BASE_URL}/field/case_rkpuram_20251112/", wait_until="domcontentloaded")
        page_m.wait_for_timeout(1500)
        page_m.screenshot(path=f"{QA_DIR}/field_rkpuram_nov_mobile.png")

        ctx_mobile.close()
        browser.close()
        print("All QA screenshots retaken successfully.")

if __name__ == "__main__":
    main()
