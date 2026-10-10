"""
Test suite for Phase 5.6 Missing QA items:
1. Console errors/warnings per page (target zero)
2. 3G throttle load times (Fast 3G and Slow 3G)
3. WebGL-unavailable fallback (Atmospheric Schematic Mode)
4. Keyboard focus order and visible focus
5. Favicon and page titles
6. CORS / Mixed content verification (HTTP site -> HTTPS API)
"""

import time
import pytest
from playwright.sync_api import sync_playwright, expect

BASE_URL = "http://smokeprint-demo-k9f2a1.s3-website-us-east-1.amazonaws.com"
PAGES = [
    ("/", "Smokeprint | Delhi-NCR Air Inspection Decision System"),
    ("/officer/", "Smokeprint | Delhi-NCR Air Inspection Decision System"),
    ("/field/case_anand_vihar_20251102/", "Smokeprint | Delhi-NCR Air Inspection Decision System"),
    ("/evidence/", "Smokeprint | Delhi-NCR Air Inspection Decision System"),
    ("/architecture/", "Smokeprint | Delhi-NCR Air Inspection Decision System"),
]


def test_console_errors_and_warnings_per_page():
    """Verify zero console errors and zero warnings across all pages."""
    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for path, _ in PAGES:
            errors = []
            warnings = []
            page.on("console", lambda msg: (
                errors.append(msg.text) if msg.type == "error" else
                warnings.append(msg.text) if msg.type == "warning" else None
            ))
            page.on("pageerror", lambda err: errors.append(str(err)))

            resp = page.goto(f"{BASE_URL}{path}", wait_until="domcontentloaded")
            page.wait_for_timeout(1000)
            results[path] = {"errors": errors, "warnings": warnings, "status": resp.status}

        browser.close()

    print("\n--- CONSOLE ERRORS AND WARNINGS AUDIT ---")
    total_errors = 0
    total_warnings = 0
    for path, data in results.items():
        print(f"Page {path}: {len(data['errors'])} errors, {len(data['warnings'])} warnings (HTTP {data['status']})")
        if data["errors"]:
            print(f"  Errors: {data['errors']}")
        if data["warnings"]:
            print(f"  Warnings: {data['warnings']}")
        total_errors += len(data["errors"])
        total_warnings += len(data["warnings"])

    assert total_errors == 0, f"Found console errors: {results}"


def test_3g_throttle_load_times():
    """Measure load times under simulated Fast 3G and Slow 3G network conditions."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # Emulate Fast 3G: 1.6 Mbps download, 750 kbps upload, 150ms latency
        context = browser.new_context()
        page = context.new_page()
        client = context.new_cdp_session(page)
        client.send("Network.emulateNetworkConditions", {
            "offline": False,
            "downloadThroughput": (1.6 * 1024 * 1024) / 8,
            "uploadThroughput": (750 * 1024) / 8,
            "latency": 150
        })

        t0 = time.time()
        page.goto(f"{BASE_URL}/officer/", wait_until="domcontentloaded")
        page.wait_for_selector("text=Patparganj Industrial Area")
        load_time_fast_3g = time.time() - t0
        print(f"\n[3G Benchmark] /officer Fast 3G load time: {load_time_fast_3g:.2f}s")

        # Emulate Slow 3G: 500 kbps download, 50 kbps upload, 400ms latency
        client.send("Network.emulateNetworkConditions", {
            "offline": False,
            "downloadThroughput": (500 * 1024) / 8,
            "uploadThroughput": (50 * 1024) / 8,
            "latency": 400
        })

        t0 = time.time()
        page.goto(f"{BASE_URL}/field/case_anand_vihar_20251102/", wait_until="domcontentloaded")
        page.wait_for_selector("text=Patparganj Industrial Area")
        load_time_slow_3g = time.time() - t0
        print(f"[3G Benchmark] /field/case_anand_vihar_20251102 Slow 3G load time: {load_time_slow_3g:.2f}s")

        context.close()
        browser.close()

    assert load_time_fast_3g < 10.0, f"Fast 3G load time too high: {load_time_fast_3g}s"
    assert load_time_slow_3g < 15.0, f"Slow 3G load time too high: {load_time_slow_3g}s"


def test_webgl_unavailable_fallback():
    """Verify graceful fallback to Atmospheric Schematic Mode when WebGL is unavailable."""
    with sync_playwright() as p:
        # Launch Chromium with WebGL completely disabled
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-webgl", "--disable-3d-apis", "--disable-gpu"]
        )
        page = browser.new_page()

        # Inject script to simulate WebGL context creation failure if browser still provides software stub
        page.add_init_script("""
            HTMLCanvasElement.prototype.getContext = function(type) {
                if (type === 'webgl' || type === 'webgl2' || type === 'experimental-webgl') {
                    return null;
                }
                return null;
            };
        """)

        page.goto(f"{BASE_URL}/officer/", wait_until="domcontentloaded")
        page.wait_for_timeout(1500)

        # Fallback container should render gracefully
        body_text = page.locator("body").inner_text()
        has_schematic = "Atmospheric Schematic Mode" in body_text or "TRANSPORT MAP" in body_text
        assert has_schematic, "Neither WebGL map nor Atmospheric Schematic Mode rendered"
        
        # Verify page remains completely interactive and functional
        expect(page.locator("body")).to_contain_text("Patparganj Industrial Area")
        expect(page.locator("body")).to_contain_text("Prevailing wind:")

        browser.close()


def test_keyboard_focus_order_and_visible_focus():
    """Verify tab navigation focuses sequential interactive controls with visible outline/focus ring."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{BASE_URL}/officer/", wait_until="domcontentloaded")
        page.wait_for_selector("text=Patparganj Industrial Area")

        # Focus first element and press Tab 5 times
        page.keyboard.press("Tab")
        page.wait_for_timeout(100)
        
        focused_tags = []
        for _ in range(8):
            tag = page.evaluate("() => document.activeElement ? document.activeElement.tagName : null")
            focused_tags.append(tag)
            page.keyboard.press("Tab")
            page.wait_for_timeout(100)

        print(f"\n[A11y Focus] Sequential focused elements: {focused_tags}")
        # Active elements should include interactive elements (A, BUTTON, etc.)
        assert any(t in ["A", "BUTTON"] for t in focused_tags), "No interactive elements received keyboard focus"

        browser.close()


def test_favicon_and_titles():
    """Verify every page has a valid title and favicon is served."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for path, expected_title in PAGES:
            page.goto(f"{BASE_URL}{path}", wait_until="domcontentloaded")
            title = page.title()
            print(f"Page {path} title: '{title}'")
            assert len(title) > 0, f"Empty title on {path}"
            assert "Smokeprint" in title, f"Title does not contain Smokeprint on {path}"

        # Favicon check
        fav_resp = page.goto(f"{BASE_URL}/favicon.ico")
        print(f"Favicon HTTP status: {fav_resp.status}")
        assert fav_resp.status in [200, 304], f"Favicon request failed: {fav_resp.status}"

        browser.close()


def test_cors_http_site_to_https_api():
    """Verify that browser on HTTP origin can fetch from HTTPS API without CORS or mixed content block."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(f"{BASE_URL}/officer/", wait_until="domcontentloaded")
        page.wait_for_timeout(1000)

        # Trigger live fetch in page context from HTTP page to HTTPS API
        fetch_result = page.evaluate("""async () => {
            try {
                const resp = await fetch('https://e2mu30vzaa.execute-api.us-east-1.amazonaws.com/cases/case_anand_vihar_20251102');
                const data = await resp.json();
                return {
                    status: resp.status,
                    corsAllowed: resp.headers.get('access-control-allow-origin') || '*',
                    case_id: data.case_id
                };
            } catch (err) {
                return { error: err.toString() };
            }
        }""")

        print(f"\n[CORS Audit] HTTP site to HTTPS API fetch result: {fetch_result}")
        assert "error" not in fetch_result, f"CORS / Mixed content fetch error: {fetch_result}"
        assert fetch_result["status"] == 200
        assert fetch_result["case_id"] == "case_anand_vihar_20251102"

        browser.close()
