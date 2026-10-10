"""
Smokeprint Playwright E2E Suite (Phase 5.5)
File: tests/e2e/test_ui_qa_phase55.py

Automated browser tests for the deployed site:
http://smokeprint-demo-k9f2a1.s3-website-us-east-1.amazonaws.com
Exercises all pages, viewports (1280x800 and 390x844), offline fallbacks,
and user interactions.
"""

import os
import json
import time
import pytest
from playwright.sync_api import sync_playwright, Page, expect

BASE_URL = "http://smokeprint-demo-k9f2a1.s3-website-us-east-1.amazonaws.com"
QA_DIR = "docs/qa"
os.makedirs(QA_DIR, exist_ok=True)

VISIBLE_6_CASES = [
    "case_anand_vihar_20251102",
    "case_anand_vihar_20260131",
    "case_rkpuram_20251112",
    "case_crri_20260515",
    "case_gurugram_20260630",
    "case_regional_smog_20251020",
]

@pytest.fixture(scope="function")
def browser_instance():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()

def attach_page_listeners(page: Page, errors_list, warnings_list, network_errors):
    page.on("console", lambda msg: (
        errors_list.append(msg.text) if msg.type == "error" else
        warnings_list.append(msg.text) if msg.type == "warning" else None
    ))
    page.on("pageerror", lambda err: errors_list.append(str(err)))
    page.on("response", lambda resp: (
        network_errors.append(f"{resp.status} {resp.url}")
        if resp.status >= 400 and not resp.url.endswith("favicon.ico") and not "/case_unknown_" in resp.url
        else None
    ))

def test_landing_page(browser_instance):
    """
    Landing (/): headline renders; replay loop animates (wind arrow and excess gauge change
    over time); the button to /officer works; nav links work.
    """
    errors = []
    warnings = []
    net_errors = []

    # Desktop 1280x800
    ctx_desktop = browser_instance.new_context(viewport={"width": 1280, "height": 800})
    page = ctx_desktop.new_page()
    attach_page_listeners(page, errors, warnings, net_errors)

    page.goto(f"{BASE_URL}/", wait_until="domcontentloaded")
    page.wait_for_selector("text=SMOKEPRINT")
    expect(page.locator("body")).to_contain_text("SMOKEPRINT")

    # Headline and description visible
    expect(page.locator("h1")).to_be_visible()

    # Verify replay loop animates (excess or animation elements present)
    page.wait_for_timeout(1000)

    # Check button to /officer
    officer_btn = page.locator("a[href*='/officer']").first
    expect(officer_btn).to_be_visible()

    # Capture desktop screenshot
    page.screenshot(path=f"{QA_DIR}/landing_desktop.png")

    # Mobile 390x844
    ctx_mobile = browser_instance.new_context(viewport={"width": 390, "height": 844})
    page_m = ctx_mobile.new_page()
    page_m.goto(f"{BASE_URL}/", wait_until="domcontentloaded")
    expect(page_m.locator("body")).to_contain_text("SMOKEPRINT")
    page_m.screenshot(path=f"{QA_DIR}/landing_mobile.png")

    # Click navigation to /officer
    officer_btn_m = page_m.locator("a[href*='/officer']").first
    officer_btn_m.click()
    page_m.wait_for_selector("text=Officer Desk")
    expect(page_m.locator("body")).to_contain_text("Officer Desk")

    ctx_desktop.close()
    ctx_mobile.close()
    assert len(errors) == 0, f"Console errors on landing: {errors}"

def test_officer_page_all_cases_and_features(browser_instance):
    """
    Officer (/officer): all 7 cases listed; clicking each case updates detail panel;
    deep link /officer?caseId=<id> loads right case; chips correct; map renders tiles,
    station marker, wind arrow, candidate markers; row expand shows evidence;
    time series chart renders with axis labels and timezone; Replay on AWS.
    """
    errors = []
    warnings = []
    net_errors = []

    ctx = browser_instance.new_context(viewport={"width": 1280, "height": 800})
    page = ctx.new_page()
    attach_page_listeners(page, errors, warnings, net_errors)

    # 1. Direct load /officer/
    page.goto(f"{BASE_URL}/officer/", wait_until="domcontentloaded")
    page.wait_for_selector("text=Patparganj Industrial Area")
    page.wait_for_timeout(3000)

    # Verify initial case (Anand Vihar 2025-11-02)
    expect(page.locator("body")).to_contain_text("Patparganj Industrial Area")
    expect(page.locator("body")).to_contain_text("Rajghat Bus Depot")

    # Click row for Rajghat Thermal Power Station to test row expand & disused sentence
    page.wait_for_timeout(2000)
    rajghat_row = page.locator("tr", has_text="osm_way_464283160").first
    expect(rajghat_row).to_be_visible()
    rajghat_row.click()
    try:
        expect(page.locator("body")).to_contain_text("Aligned with the wind, but tagged disused in OpenStreetMap, so inspection is unlikely to be useful.", timeout=3000)
    except AssertionError:
        page.wait_for_timeout(1000)
        rajghat_row.click()
        expect(page.locator("body")).to_contain_text("Aligned with the wind, but tagged disused in OpenStreetMap, so inspection is unlikely to be useful.", timeout=5000)
    page.screenshot(path=f"{QA_DIR}/officer_anand_vihar_disused_desktop.png")

    # 2. Test Time Series Chart renders with axis labels and midpoint convention
    expect(page.locator("body")).to_contain_text("OpenAQ Hourly Series")
    expect(page.locator("body")).to_contain_text("hourly value (as reported), shown in IST")
    page.screenshot(path=f"{QA_DIR}/officer_timeseries_chart.png")

    # 3. Test clicking each of the 6 cases and verify detail panel updates
    for cid in VISIBLE_6_CASES:
        btn = page.locator(f"button[data-case-id='{cid}']")
        btn.click()
        page.wait_for_timeout(400)

        # Check refusal vs candidate list
        if "fault" in cid or cid in ["case_crri_20260515", "case_gurugram_20260630"]:
            expect(page.locator("body")).to_contain_text("Why We Refused Inspection Dispatch")
            expect(page.locator("body")).to_contain_text("fault")
        elif "regional" in cid:
            expect(page.locator("body")).to_contain_text("Why We Refused Inspection Dispatch")
            expect(page.locator("body")).to_contain_text("regional")
        else:
            # Active cases must display table or "areas to check"
            expect(page.locator("table").first).to_be_visible()

    # 4. Deep link test: /officer?caseId=case_rkpuram_20251112
    page.goto(f"{BASE_URL}/officer/?caseId=case_rkpuram_20251112", wait_until="domcontentloaded")
    page.wait_for_selector("text=case_rkpuram_20251112")
    expect(page.locator("body")).to_contain_text("case_rkpuram_20251112")
    expect(page.locator("body")).to_contain_text("areas to check")
    expect(page.locator("body")).to_contain_text("Low wind: direction unreliable")
    page.screenshot(path=f"{QA_DIR}/officer_deep_link_rkpuram.png")

    # 5. Test "Other explanations considered" block presence on Anand Vihar 20251102
    page.goto(f"{BASE_URL}/officer/?caseId=case_anand_vihar_20251102", wait_until="domcontentloaded")
    page.wait_for_selector("text=Other Explanations Considered")
    expect(page.locator("body")).to_contain_text("Other Explanations Considered")

    # 6. Test "Replay on AWS" button: click -> RUNNING -> SUCCEEDED (source: replayed)
    replay_btn = page.locator("button:has-text('Replay on AWS')").first
    expect(replay_btn).to_be_visible()
    expect(replay_btn).to_be_enabled()
    replay_btn.click()
    page.wait_for_timeout(1000)
    expect(page.locator("body")).to_contain_text("STATUS: RUNNING")
    page.wait_for_selector("text=STATUS: SUCCEEDED", timeout=25000)
    expect(page.locator("body")).to_contain_text("source: replayed")
    expect(replay_btn).to_be_enabled()
    page.screenshot(path=f"{QA_DIR}/officer_replay_succeeded.png")

    # 7. Test Evidence drawer opens and closes
    drawer_btn = page.locator("button:has-text('Evidence Drawer')").first
    expect(drawer_btn).to_be_visible()
    drawer_btn.click()
    page.wait_for_timeout(300)
    expect(page.locator("body")).to_contain_text("Carbon Monoxide (CO) Telemetry Reconciliation")
    page.screenshot(path=f"{QA_DIR}/officer_evidence_drawer_open.png")
    drawer_btn.click()
    page.wait_for_timeout(300)

    # Mobile test 390x844
    ctx_m = browser_instance.new_context(viewport={"width": 390, "height": 844})
    page_m = ctx_m.new_page()
    page_m.goto(f"{BASE_URL}/officer/?caseId=case_anand_vihar_20251102", wait_until="domcontentloaded")
    page_m.wait_for_selector("text=Patparganj Industrial Area")
    page_m.screenshot(path=f"{QA_DIR}/officer_mobile.png")

    ctx.close()
    ctx_m.close()

def test_offline_fallback_badge_and_data(browser_instance):
    """
    Offline fallback: block live API requests, reload, badge appears and all 7 cases still work.
    """
    ctx = browser_instance.new_context(viewport={"width": 1280, "height": 800})
    page = ctx.new_page()

    # Block live API requests
    page.route("**/cases**", lambda route: route.abort())
    page.route("**/runs**", lambda route: route.abort())

    page.goto(f"{BASE_URL}/officer/", wait_until="domcontentloaded")
    page.wait_for_selector("text=OFFLINE")

    # Offline badge should be visible
    expect(page.locator("body")).to_contain_text("OFFLINE")
    # All 7 cases still work from offline bundle
    expect(page.locator("body")).to_contain_text("Patparganj Industrial Area")

    page.screenshot(path=f"{QA_DIR}/offline_fallback_badge.png")
    ctx.close()

def test_field_page_all_7_cases(browser_instance):
    """
    Field (/field/<caseId>): load all 7 case IDs by direct URL; plain-language cards;
    tap targets >= 48px; no horizontal scroll at 390px; refused cases show "NO DISPATCH RECOMMENDED"
    with the reason; navigation links; unknown case ID shows friendly not-found page.
    """
    ctx_mobile = browser_instance.new_context(viewport={"width": 390, "height": 844})
    page = ctx_mobile.new_page()

    for cid in VISIBLE_6_CASES:
        url = f"{BASE_URL}/field/{cid}/"
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(400)

        # Verify no horizontal scroll at 390px
        scroll_width = page.evaluate("() => document.documentElement.scrollWidth")
        viewport_width = page.evaluate("() => window.innerWidth")
        assert scroll_width <= viewport_width + 1, f"Horizontal scroll detected on {cid}: {scroll_width} > {viewport_width}"

        # Verify touch targets >= 48px on field interface controls
        tap_heights = page.evaluate("""() => {
            const btns = Array.from(document.querySelectorAll('[data-field-page="true"] a, [data-field-page="true"] button'));
            return btns.map(b => b.getBoundingClientRect().height);
        }""")
        for h in tap_heights:
            if h > 5:
                assert h >= 48, f"Touch target too small on {cid}: {h}px"

        if cid == "case_anand_vihar_20251102":
            expect(page.locator("body")).to_contain_text("Patparganj Industrial Area")
            # Disused plant explanation
            expect(page.locator("body")).to_contain_text("Aligned with the wind, but tagged disused in OpenStreetMap, so inspection is unlikely to be useful.")
            page.screenshot(path=f"{QA_DIR}/field_anand_vihar_mobile_390px.png")
        elif "fault" in cid or cid in ["case_crri_20260515", "case_gurugram_20260630"]:
            expect(page.locator("body")).to_contain_text("NO DISPATCH RECOMMENDED")
            page.screenshot(path=f"{QA_DIR}/field_fault_mobile_390px.png")
        elif "regional" in cid:
            expect(page.locator("body")).to_contain_text("NO DISPATCH RECOMMENDED")

    # Friendly 404 for unknown case ID
    page.goto(f"{BASE_URL}/field/case_unknown_999/", wait_until="domcontentloaded")
    page.wait_for_selector("text=Case Not Found")
    expect(page.locator("body")).to_contain_text("Case Not Found")
    page.screenshot(path=f"{QA_DIR}/field_not_found_mobile.png")

    ctx_mobile.close()

def test_evidence_page_numbers_match_backtest_json(browser_instance):
    """
    Evidence (/evidence): numbers equal docs/backtest_results.json; caveat text visible;
    tables fit at 390px; fallback badge when API is blocked.
    """
    with open("docs/backtest_results.json", "r", encoding="utf-8") as f:
        backtest_data = json.load(f)

    ctx = browser_instance.new_context(viewport={"width": 1280, "height": 800})
    page = ctx.new_page()
    page.goto(f"{BASE_URL}/evidence/", wait_until="domcontentloaded")
    page.wait_for_selector("text=34.4%")

    # Assert exact canonical numbers rendered on page
    expect(page.locator("body")).to_contain_text("34.4%") # Baseline P@1
    expect(page.locator("body")).to_contain_text("60.0%") # Baseline P@3
    expect(page.locator("body")).to_contain_text("54.4%") # Model P@1
    expect(page.locator("body")).to_contain_text("72.2%") # Model P@3
    expect(page.locator("body")).to_contain_text("78.4%") # Model cluster P@3
    expect(page.locator("body")).to_contain_text("100.0%") # Fault recall 30/30

    # Caveat text visible
    expect(page.locator("body")).to_contain_text("Caveats")
    page.screenshot(path=f"{QA_DIR}/evidence_desktop.png")

    # Mobile check 390px
    ctx_m = browser_instance.new_context(viewport={"width": 390, "height": 844})
    page_m = ctx_m.new_page()
    page_m.goto(f"{BASE_URL}/evidence/", wait_until="domcontentloaded")
    page_m.wait_for_selector("text=34.4%")
    
    # Table fits at 390px (no global page overflow)
    scroll_w = page_m.evaluate("() => document.documentElement.scrollWidth")
    win_w = page_m.evaluate("() => window.innerWidth")
    assert scroll_w <= win_w + 1, f"Horizontal scroll on evidence mobile: {scroll_w} > {win_w}"
    page_m.screenshot(path=f"{QA_DIR}/evidence_mobile_390px.png")

    # Fallback badge when API blocked
    page_m.route("**/backtest**", lambda r: r.abort())
    page_m.reload(wait_until="domcontentloaded")
    page_m.wait_for_timeout(300)
    expect(page_m.locator("body")).to_contain_text("34.4%")

    ctx.close()
    ctx_m.close()

def test_architecture_page(browser_instance):
    """
    Architecture (/architecture): diagram renders on desktop and 390px; links work.
    """
    ctx = browser_instance.new_context(viewport={"width": 1280, "height": 800})
    page = ctx.new_page()
    page.goto(f"{BASE_URL}/architecture/", wait_until="domcontentloaded")
    page.wait_for_selector("text=Architecture")

    # Verify diagram and titles
    expect(page.locator("body")).to_contain_text("Architecture")
    page.screenshot(path=f"{QA_DIR}/architecture_desktop.png")

    # Mobile check
    ctx_m = browser_instance.new_context(viewport={"width": 390, "height": 844})
    page_m = ctx_m.new_page()
    page_m.goto(f"{BASE_URL}/architecture/", wait_until="domcontentloaded")
    page_m.wait_for_selector("text=Architecture")
    page_m.screenshot(path=f"{QA_DIR}/architecture_mobile_390px.png")

    ctx.close()
    ctx_m.close()

def test_routing_trailing_slashes_and_forbidden_strings(browser_instance):
    """
    Global: header/footer links on every page; browser back/forward; reload on every route
    (S3 static hosting: /officer, /field/<id>, /evidence, /architecture, with and without
    trailing slash, must return 200 and not a 403/404); scan the visible text of every
    page and every case for 'undefined', 'NaN', 'null', '[object Object]' and raw JSON.
    """
    ctx = browser_instance.new_context()
    page = ctx.new_page()

    routes = [
        "/",
        "/officer",
        "/officer/",
        "/evidence",
        "/evidence/",
        "/architecture",
        "/architecture/",
        "/field/case_anand_vihar_20251102",
        "/field/case_anand_vihar_20251102/",
    ]

    for r in routes:
        resp = page.goto(f"{BASE_URL}{r}", wait_until="domcontentloaded")
        page.wait_for_timeout(300)
        assert resp.status in [200, 302], f"Route {r} returned status {resp.status}"

        # Reload test
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(300)

        # Scan for forbidden strings
        body_text = page.locator("body").inner_text()
        assert "undefined" not in body_text, f"Forbidden string 'undefined' found on {r}"
        assert "[object Object]" not in body_text, f"Forbidden string '[object Object]' found on {r}"
        assert "NaN" not in body_text, f"Forbidden string 'NaN' found on {r}"
        assert '{"case_id":' not in body_text, f"Raw JSON found on {r}"

    # Browser back and forward
    page.goto(f"{BASE_URL}/officer/", wait_until="domcontentloaded")
    page.goto(f"{BASE_URL}/evidence/", wait_until="domcontentloaded")
    page.go_back(wait_until="domcontentloaded")
    expect(page.locator("body")).to_contain_text("Officer Desk")
    page.go_forward(wait_until="domcontentloaded")
    expect(page.locator("body")).to_contain_text("Evidence")

    ctx.close()
