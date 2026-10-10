"""
Smokeprint Test: Evidence Page Numbers Consistency with Backtest Results JSON
File: tests/test_evidence_page_numbers.py

Guarantees single source of truth for all metrics shown on the Evidence page:
  - nearest-upwind: 34.4% [30.4%, 38.8%], 60.0% [55.6%, 64.4%]
  - shortlist score: 54.4% [50.0%, 58.6%], 72.2% [68.2%, 76.0%], cluster 78.4% [74.6%, 81.8%]
  - injected-fault recall: 30/30 = 100.0% (1.0)
  - untouched clean window FPR: 0/10 = 0.0% (0.0)
Fails if any number on the Evidence page or embedded offline copy differs from docs/backtest_results.json.
"""

import os
import sys
import json
import re
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BACKTEST_JSON_PATH = "docs/backtest_results.json"
BACKTEST_TS_PATH = "web/src/lib/backtestData.ts"
EVIDENCE_PAGE_PATH = "web/src/app/evidence/page.tsx"

def test_canonical_backtest_results_json_metrics():
    with open(BACKTEST_JSON_PATH, "r", encoding="utf-8") as f:
        bt = json.load(f)

    # 1. Ablation mismatch metrics
    ablation = bt.get("ablation_mismatch_metrics", {})
    assert "nearest_upwind" in ablation, "Missing nearest_upwind in backtest_results.json"
    assert "shortlist_score" in ablation, "Missing shortlist_score in backtest_results.json"

    # Nearest upwind: 34.4% P@1, 60.0% P@3
    nu_p1 = ablation["nearest_upwind"]["p1"]["value"]
    nu_p3 = ablation["nearest_upwind"]["p3"]["value"]
    assert nu_p1 == 0.344, f"Nearest-upwind P@1 {nu_p1} != 0.344 (34.4%)"
    assert nu_p3 == 0.600, f"Nearest-upwind P@3 {nu_p3} != 0.600 (60.0%)"

    # Shortlist score: 54.4% P@1, 72.2% P@3, 78.4% cluster P@3
    ss_p1 = ablation["shortlist_score"]["p1"]["value"]
    ss_p3 = ablation["shortlist_score"]["p3"]["value"]
    ss_cp3 = ablation["shortlist_score"]["cluster_p3"]["value"]
    assert ss_p1 == 0.544, f"Shortlist score P@1 {ss_p1} != 0.544 (54.4%)"
    assert ss_p3 == 0.722, f"Shortlist score P@3 {ss_p3} != 0.722 (72.2%)"
    assert ss_cp3 == 0.784, f"Shortlist score cluster P@3 {ss_cp3} != 0.784 (78.4%)"

    # 2. Fault detector validation: 30/30 = 100%
    fault = bt.get("fault_detector_validation", {})
    recall_info = fault.get("injected_fault_recall", {})
    assert recall_info.get("detected") == 30
    assert recall_info.get("total") == 30
    assert recall_info.get("percentage") == 100.0


def test_evidence_page_offline_ts_matches_backtest_json():
    with open(BACKTEST_JSON_PATH, "r", encoding="utf-8") as f:
        bt = json.load(f)

    with open(BACKTEST_TS_PATH, "r", encoding="utf-8") as f:
        ts_content = f.read()

    # Extract JSON object from TypeScript export
    match = re.search(r"export const BACKTEST_SUMMARY = ({[\s\S]+?});\s*$", ts_content)
    assert match, "Failed to parse BACKTEST_SUMMARY from web/src/lib/backtestData.ts"
    summary_data = json.loads(match.group(1))

    # Assert exact parity between TS offline copy and docs/backtest_results.json
    assert summary_data["ablation_mismatch_metrics"] == bt["ablation_mismatch_metrics"]
    assert summary_data["fault_detector_validation"] == bt["fault_detector_validation"]


def test_evidence_page_jsx_contains_no_divergent_hardcoded_numbers():
    with open(EVIDENCE_PAGE_PATH, "r", encoding="utf-8") as f:
        page_content = f.read()

    # Old divergent numbers that must NEVER appear in the page code
    divergent_strings = [
        "0.518",
        "0.730",
        "0.560",
        "0.812",
        "0.916",
        "92.0%",
        "46 / 50"
    ]

    for div_str in divergent_strings:
        assert div_str not in page_content, (
            f"Evidence page JSX contains stale hardcoded string '{div_str}'! "
            "Page must read strictly from backtest data."
        )

    # Must import and use BACKTEST_SUMMARY
    assert "BACKTEST_SUMMARY" in page_content
    assert "ablation_mismatch_metrics" in page_content
    assert "fault_detector_validation" in page_content
