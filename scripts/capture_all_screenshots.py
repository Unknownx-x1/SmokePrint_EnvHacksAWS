import os
import time
import subprocess

BASE_URL = "http://smokeprint-web-391713637963-us-east-1.s3-website-us-east-1.amazonaws.com"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
OUT_DIR = os.path.abspath("docs/screenshots")

os.makedirs(OUT_DIR, exist_ok=True)

targets = [
    # 1. Landing
    ("landing_desktop.png", f"{BASE_URL}/", 1280, 800),
    ("landing_mobile_390px.png", f"{BASE_URL}/", 390, 844),
    
    # 2. Officer: Dispatch / Comparable case (Anand Vihar)
    ("officer_dispatch_desktop.png", f"{BASE_URL}/officer/?caseId=case_anand_vihar_20251102", 1280, 950),
    # Officer: Fault Refusal case (CRRI Mathura Rd)
    ("officer_fault_desktop.png", f"{BASE_URL}/officer/?caseId=case_crri_20260515", 1280, 950),
    # Officer: Regional Smog Refusal case (Delhi Smog)
    ("officer_regional_desktop.png", f"{BASE_URL}/officer/?caseId=case_regional_smog_20251020", 1280, 950),
    
    # 3. Field view (390px mobile)
    ("field_anand_vihar_mobile_390px.png", f"{BASE_URL}/field/case_anand_vihar_20251102/", 390, 844),
    ("field_fault_mobile_390px.png", f"{BASE_URL}/field/case_crri_20260515/", 390, 844),
    
    # 4. Evidence & Backtest
    ("evidence_desktop.png", f"{BASE_URL}/evidence/", 1280, 900),
    ("evidence_mobile_390px.png", f"{BASE_URL}/evidence/", 390, 844),
    
    # 5. Architecture
    ("architecture_desktop.png", f"{BASE_URL}/architecture/", 1280, 850),
    ("architecture_mobile_390px.png", f"{BASE_URL}/architecture/", 390, 844),
    
    # 6. Offline Fallback Badge Test (Blocking live API to assert offline badge appears)
    ("offline_fallback_badge.png", f"{BASE_URL}/officer/", 1280, 800, ["--host-resolver-rules=MAP *execute-api* 127.0.0.1"])
]

def capture_screenshots():
    print(f"Capturing screenshots to: {OUT_DIR}")
    for item in targets:
        filename, url, width, height = item[0], item[1], item[2], item[3]
        extra_flags = item[4] if len(item) > 4 else []
        out_path = os.path.join(OUT_DIR, filename)
        cmd = [
            CHROME_PATH,
            "--headless=new",
            "--disable-gpu",
            f"--window-size={width},{height}",
            f"--screenshot={out_path}",
        ] + extra_flags + [url]
        print(f"Capturing {filename} ({width}x{height}) from {url}...")
        res = subprocess.run(cmd, capture_output=True)
        if os.path.exists(out_path):
            size_kb = os.path.getsize(out_path) / 1024
            print(f"  -> Saved {filename} ({size_kb:.1f} KB)")
        else:
            print(f"  -> FAILED to capture {filename}: {res.stderr.decode('utf-8', errors='ignore')}")

if __name__ == "__main__":
    capture_screenshots()
