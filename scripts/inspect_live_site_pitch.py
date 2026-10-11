import os
import time
from playwright.sync_api import sync_playwright

BASE_URL = "http://smokeprint-demo-k9f2a1.s3-website-us-east-1.amazonaws.com"

def inspect_site():
    out_file = "scripts/live_site_text.txt"
    with open(out_file, "w", encoding="utf-8") as f:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
            
            # 1. /officer/ page
            f.write("--- INSPECTING /officer/ ---\n")
            page.goto(f"{BASE_URL}/officer/", wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            
            officer_text = page.inner_text("body")
            f.write("Officer Page Text:\n")
            f.write(officer_text)
            f.write("\n...\n")
            
            # 2. Case pages on officer & field
            cases = [
                "case_anand_vihar_20251102",
                "case_gurugram_20260630",
                "case_regional_smog_20251020"
            ]
            
            for case_id in cases:
                f.write(f"\n=======================================================\n")
                f.write(f"--- INSPECTING /officer/?case={case_id} ---\n")
                page.goto(f"{BASE_URL}/officer/?case={case_id}", wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
                f.write(f"Officer view ({case_id}):\n")
                f.write(page.inner_text("body"))
                
                f.write(f"\n--- INSPECTING /field/{case_id}/ ---\n")
                page.goto(f"{BASE_URL}/field/{case_id}/", wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
                field_text = page.inner_text("body")
                f.write(f"Field view ({case_id}):\n")
                f.write(field_text)
                
            # 3. /evidence/ page
            f.write(f"\n=======================================================\n")
            f.write(f"--- INSPECTING /evidence/ ---\n")
            page.goto(f"{BASE_URL}/evidence/", wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            f.write("Evidence page text:\n")
            f.write(page.inner_text("body"))
            
            # 4. Check main dashboard /
            f.write(f"\n=======================================================\n")
            f.write(f"--- INSPECTING / ---\n")
            page.goto(f"{BASE_URL}/", wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            f.write("Home page text:\n")
            f.write(page.inner_text("body"))
            
            # 5. Check architecture page /architecture/
            f.write(f"\n=======================================================\n")
            f.write(f"--- INSPECTING /architecture/ ---\n")
            page.goto(f"{BASE_URL}/architecture/", wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            f.write("Architecture page text:\n")
            f.write(page.inner_text("body"))
            
            browser.close()

if __name__ == "__main__":
    inspect_site()
