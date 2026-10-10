'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { ShieldAlert, AlertTriangle, CheckCircle2, FileCode, CheckSquare, WifiOff } from 'lucide-react';
import { BACKTEST_SUMMARY } from '../../lib/backtestData';

export default function EvidencePage() {
  const [backtestData, setBacktestData] = useState<any>(BACKTEST_SUMMARY);
  const [isOfflineCopy, setIsOfflineCopy] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    async function loadData() {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      if (!apiUrl) {
        setIsOfflineCopy(true);
        setIsLoading(false);
        return;
      }
      try {
        const res = await fetch(`${apiUrl}/backtest`, {
          headers: { Accept: 'application/json' },
          cache: 'no-store'
        });
        if (res.ok) {
          const json = await res.json();
          // Use live data if ablation_mismatch_metrics is present
          if (json.ablation_mismatch_metrics) {
            setBacktestData(json);
            setIsOfflineCopy(false);
          } else {
            // Merge with local summary
            setBacktestData({ ...BACKTEST_SUMMARY, ...json });
            setIsOfflineCopy(false);
          }
        } else {
          setIsOfflineCopy(true);
        }
      } catch (err) {
        setIsOfflineCopy(true);
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, []);

  const ablation = backtestData?.ablation_mismatch_metrics || BACKTEST_SUMMARY.ablation_mismatch_metrics;
  const fault = backtestData?.fault_detector_validation || BACKTEST_SUMMARY.fault_detector_validation;

  return (
    <div className="flex-1 max-w-5xl mx-auto w-full px-4 py-8 sm:py-12 space-y-8">
      {/* Header with Offline Badge */}
      <div>
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono bg-stone-100 text-stone-700 border border-stone-200">
            <ShieldAlert className="w-3.5 h-3.5 text-stone-700" />
            <span>STATISTICAL AUDIT & REPRODUCIBILITY</span>
          </div>
          {isOfflineCopy && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono bg-amber-50 text-amber-800 border border-amber-300">
              <WifiOff className="w-3 h-3 text-amber-600" />
              OFFLINE COPY
            </span>
          )}
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold text-stone-900 tracking-tight">
          Evidence, Backtest CIs & Caveats
        </h1>
        <p className="mt-2 text-sm text-stone-600 max-w-3xl">
          Empirical verification metrics evaluated across 500 semi-synthetic plume injection trials in real Delhi-NCR meteorological background, held-out fault detector validations, and provenance transparency.
        </p>
      </div>

      {/* Mandatory Plain Caveat Alert Box */}
      <div className="p-4 rounded-lg bg-stone-50 border-2 border-stone-300 space-y-2">
        <div className="flex items-center gap-2 font-bold text-sm text-stone-900">
          <AlertTriangle className="w-4 h-4 text-stone-700" />
          <span>Mandatory Scientific Caveat</span>
        </div>
        <p className="text-xs text-stone-700 leading-relaxed font-sans">
          <strong>Simulated plume injections, so this shows consistency not real-world accuracy.</strong> Synthetic evaluations prove mathematical convergence, footprint gating, and stability against atmospheric dispersion perturbations; they do not replace physical field inspections or ground-truth facility stack monitors.
        </p>
      </div>

      {/* Backtest Results Table with 95% CIs */}
      <div className="bg-white rounded-lg border border-stone-200 shadow-sm p-5 space-y-4">
        <div>
          <h2 className="text-base font-bold text-stone-900">
            500-Trial Dispersion Mismatch Ablation (95% Bootstrap CIs)
          </h2>
          <div className="mt-1.5 flex items-center gap-2">
            <span className="text-xs font-mono text-amber-900 bg-amber-50 border border-amber-200 px-2.5 py-0.5 rounded font-medium">
              simulated plume injections; consistency not real-world accuracy
            </span>
          </div>
          <p className="text-xs text-stone-500 mt-1">
            Evaluated with forward plume kernel against independent simulation with perturbed stability classes, plume rise, and wind noise. Data loaded directly from canonical backtest JSON.
          </p>
        </div>

        <div className="overflow-x-auto border border-stone-200 rounded">
          <table className="w-full text-left text-xs font-sans">
            <thead className="bg-stone-50 border-b border-stone-200 font-mono text-[11px] text-stone-500">
              <tr>
                <th className="py-2.5 px-3">Ablation Variant</th>
                <th className="py-2.5 px-3">Precision @ 1 (95% CI)</th>
                <th className="py-2.5 px-3">Precision @ 3 (95% CI)</th>
                <th className="py-2.5 px-3">Cluster P @ 3 (95% CI)</th>
                <th className="py-2.5 px-3">Assessment</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100 font-mono tabular-nums">
              {/* Nearest Upwind */}
              <tr>
                <td className="py-2.5 px-3 font-sans font-medium text-stone-900">
                  {ablation.nearest_upwind.label}
                </td>
                <td className="py-2.5 px-3 text-stone-600">
                  {(ablation.nearest_upwind.p1.value * 100).toFixed(1)}% [{(ablation.nearest_upwind.p1.ci95[0] * 100).toFixed(1)}%, {(ablation.nearest_upwind.p1.ci95[1] * 100).toFixed(1)}%]
                </td>
                <td className="py-2.5 px-3 text-stone-600">
                  {(ablation.nearest_upwind.p3.value * 100).toFixed(1)}% [{(ablation.nearest_upwind.p3.ci95[0] * 100).toFixed(1)}%, {(ablation.nearest_upwind.p3.ci95[1] * 100).toFixed(1)}%]
                </td>
                <td className="py-2.5 px-3 text-stone-600">
                  {(ablation.nearest_upwind.cluster_p3.value * 100).toFixed(1)}% [{(ablation.nearest_upwind.cluster_p3.ci95[0] * 100).toFixed(1)}%, {(ablation.nearest_upwind.cluster_p3.ci95[1] * 100).toFixed(1)}%]
                </td>
                <td className="py-2.5 px-3 font-sans text-stone-600">
                  {ablation.nearest_upwind.assessment}
                </td>
              </tr>

              {/* Forward Plume Only */}
              <tr>
                <td className="py-2.5 px-3 font-sans font-medium text-stone-900">
                  {ablation.forward_plume_only.label}
                </td>
                <td className="py-2.5 px-3 text-stone-600">
                  {(ablation.forward_plume_only.p1.value * 100).toFixed(1)}% [{(ablation.forward_plume_only.p1.ci95[0] * 100).toFixed(1)}%, {(ablation.forward_plume_only.p1.ci95[1] * 100).toFixed(1)}%]
                </td>
                <td className="py-2.5 px-3 text-stone-600">
                  {(ablation.forward_plume_only.p3.value * 100).toFixed(1)}% [{(ablation.forward_plume_only.p3.ci95[0] * 100).toFixed(1)}%, {(ablation.forward_plume_only.p3.ci95[1] * 100).toFixed(1)}%]
                </td>
                <td className="py-2.5 px-3 text-stone-600">
                  {(ablation.forward_plume_only.cluster_p3.value * 100).toFixed(1)}% [{(ablation.forward_plume_only.cluster_p3.ci95[0] * 100).toFixed(1)}%, {(ablation.forward_plume_only.cluster_p3.ci95[1] * 100).toFixed(1)}%]
                </td>
                <td className="py-2.5 px-3 font-sans text-stone-600">
                  {ablation.forward_plume_only.assessment}
                </td>
              </tr>

              {/* Shortlist Score (Plume x Sig x Status) */}
              <tr className="bg-stone-50/80 font-bold">
                <td className="py-2.5 px-3 font-sans text-stone-900">
                  {ablation.shortlist_score.label}
                </td>
                <td className="py-2.5 px-3 text-stone-900">
                  {(ablation.shortlist_score.p1.value * 100).toFixed(1)}% [{(ablation.shortlist_score.p1.ci95[0] * 100).toFixed(1)}%, {(ablation.shortlist_score.p1.ci95[1] * 100).toFixed(1)}%]
                </td>
                <td className="py-2.5 px-3 text-stone-900">
                  {(ablation.shortlist_score.p3.value * 100).toFixed(1)}% [{(ablation.shortlist_score.p3.ci95[0] * 100).toFixed(1)}%, {(ablation.shortlist_score.p3.ci95[1] * 100).toFixed(1)}%]
                </td>
                <td className="py-2.5 px-3 text-stone-900">
                  {(ablation.shortlist_score.cluster_p3.value * 100).toFixed(1)}% [{(ablation.shortlist_score.cluster_p3.ci95[0] * 100).toFixed(1)}%, {(ablation.shortlist_score.cluster_p3.ci95[1] * 100).toFixed(1)}%]
                </td>
                <td className="py-2.5 px-3 font-sans text-stone-900">
                  {ablation.shortlist_score.assessment}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Fault Detector Validation Metrics */}
      <div className="bg-white rounded-lg border border-stone-200 shadow-sm p-5 space-y-4">
        <div>
          <h2 className="text-base font-bold text-stone-900">
            Instrument Fault Detector Validation
          </h2>
          <p className="text-xs text-stone-500 font-mono mt-0.5">
            Labelled: <strong>{fault.injected_fault_recall.label}</strong>
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="border border-stone-200 rounded p-3.5 bg-stone-50 space-y-1">
            <div className="text-[11px] font-mono text-stone-500 uppercase">Injected Fault Recall</div>
            <div className="text-2xl font-bold font-mono text-stone-900">
              {fault.injected_fault_recall.percentage.toFixed(1)}%
            </div>
            <div className="text-[11px] text-stone-500 font-sans">
              {fault.injected_fault_recall.detected} / {fault.injected_fault_recall.total} synthetic injection scenarios detected
            </div>
            <div className="text-[10px] font-mono text-stone-600 border-t border-stone-200 pt-1">
              injected-fault recall; real-world false-positive rate unknown
            </div>
          </div>

          <div className="border border-stone-200 rounded p-3.5 bg-stone-50 space-y-1">
            <div className="text-[11px] font-mono text-stone-500 uppercase">Untouched Clean Window FPR</div>
            <div className="text-2xl font-bold font-mono text-stone-900">
              {fault.clean_window_fpr.percentage.toFixed(1)}%
            </div>
            <div className="text-[11px] text-stone-500 font-sans">
              {fault.clean_window_fpr.false_positives} / {fault.clean_window_fpr.total_days} clean reference monitoring station days falsely flagged
            </div>
            <div className="text-[10px] font-mono text-stone-600 border-t border-stone-200 pt-1">
              untouched-window FPR measured on 10 pre-screened windows
            </div>
          </div>

          <div className="border border-stone-200 rounded p-3.5 bg-stone-50 space-y-1">
            <div className="text-[11px] font-mono text-stone-500 uppercase">Target Failure Modes</div>
            <div className="text-sm font-semibold font-mono text-stone-800">
              Ratio Lock, Collapse, Frozen Float
            </div>
            <div className="text-[11px] text-stone-500 font-sans">
              30 / 30 synthetic faults caught across 10 untuned stations
            </div>
          </div>
        </div>

        <div className="p-3 bg-stone-50 border border-stone-200 rounded text-xs text-stone-600 leading-relaxed">
          <strong>Testing limitation note:</strong> While synthetic fault injections (flatline zeros, PM2.5/PM10 ratio locks, and step collapse) yield {fault.injected_fault_recall.detected}/{fault.injected_fault_recall.total} ({fault.injected_fault_recall.percentage.toFixed(1)}%) recall in hold-out simulation, the actual real-world false-positive rate across all 33 Delhi-NCR monitors across all seasons is strictly unknown without continuous independent sensor recalibration audits.
        </div>
      </div>

      {/* Step Functions Replay Labelling Policy */}
      <div className="bg-white rounded-lg border border-stone-200 shadow-sm p-5 space-y-4">
        <div>
          <h2 className="text-base font-bold text-stone-900">
            AWS Step Functions Replay Provenance & Labelling
          </h2>
          <p className="text-xs text-stone-500 mt-0.5">
            Strict transparency standard: API responses never imply unexecuted cloud recomputation.
          </p>
        </div>

        <div className="p-4 bg-stone-900 text-stone-100 rounded font-mono text-xs overflow-x-auto space-y-1">
          <div className="text-stone-400">// Sample API /runs/:id and Step Functions execution output payload:</div>
          <div>{`{`}</div>
          <div className="pl-4"><span className="text-emerald-400">"status"</span>: <span className="text-amber-300">"SUCCEEDED"</span>,</div>
          <div className="pl-4"><span className="text-emerald-400">"source"</span>: <span className="text-amber-300">"replayed"</span>,</div>
          <div className="pl-4"><span className="text-emerald-400">"mode"</span>: <span className="text-amber-300">"replayed_from_canonical_output"</span>,</div>
          <div className="pl-4"><span className="text-emerald-400">"replayed_note"</span>: <span className="text-amber-300">"replayed from validated core output"</span>,</div>
          <div className="pl-4"><span className="text-emerald-400">"case_id"</span>: <span className="text-amber-300">"case_anand_vihar_20251102"</span>,</div>
          <div className="pl-4"><span className="text-emerald-400">"group"</span>: <span className="text-amber-300">"comparable candidates"</span>,</div>
          <div className="pl-4"><span className="text-emerald-400">"classification"</span>: <span className="text-amber-300">"Multiple Comparable Candidates"</span></div>
          <div>{`}`}</div>
        </div>

        <ul className="list-disc list-inside text-xs text-stone-700 space-y-1.5 pl-1">
          <li>
            <strong>Source honesty:</strong> Outputs always state <code>source: "replayed"</code> and <code>mode: "replayed_from_canonical_output"</code>.
          </li>
          <li>
            <strong>No misleading version strings:</strong> Any <code>code_version</code> suggesting live core execution in Lambda has been removed.
          </li>
          <li>
            <strong>Zero hallucinated AI claims:</strong> The web interface never claims live Bedrock invocation or live real-time core solving.
          </li>
        </ul>
      </div>
    </div>
  );
}
