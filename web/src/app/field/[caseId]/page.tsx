import React from 'react';
import Link from 'next/link';
import { ALL_CASE_IDS, OFFLINE_CASES } from '../../../lib/offlineData';
import { Candidate, CaseData } from '../../../lib/types';
import {
  ShieldAlert,
  Wind,
  CheckCircle2,
  AlertTriangle,
  MapPin,
  ArrowLeft,
  ChevronRight,
  ClipboardCheck,
  CheckSquare,
  Square
} from 'lucide-react';

export function generateStaticParams() {
  return ALL_CASE_IDS.map((caseId) => ({ caseId }));
}

export default async function FieldPage({
  params,
}: {
  params: Promise<{ caseId: string }>;
}) {
  const resolvedParams = await params;
  const caseId = resolvedParams.caseId || 'case_anand_vihar_20251102';
  const caseData: CaseData = OFFLINE_CASES[caseId] || OFFLINE_CASES['case_anand_vihar_20251102'];

  const isRefused = caseData.dispatch_refused;
  const windDir = caseData.wind?.wind_direction_deg || 263.0;
  const windSpeed = caseData.wind?.wind_speed_ms || 2.56;
  const isComparable = caseData.group === 'comparable candidates' || caseData.classification === 'Multiple Comparable Candidates' || caseId === 'case_anand_vihar_20251102';

  // Derive plain-language compass sector from bearing
  function getCompassSector(deg: number): string {
    const sectors = ['north', 'north-east', 'east', 'south-east', 'south', 'south-west', 'west', 'north-west'];
    const idx = Math.round(deg / 45) % 8;
    return sectors[idx];
  }

  // Derive actionable field inspection targets based on candidate type
  function getInspectionTargets(candType: string): string[] {
    switch (candType.toLowerCase()) {
      case 'industrial':
        return ['Open burning of scrap / packaging', 'Stack emission filters / wet scrubbers', 'Backup diesel generator sets (DG sets)', 'Boiler fuel compliance'];
      case 'landfill':
        return ['Methane flaring & smouldering waste fires', 'Water-mist cannon operation', 'Tipping face dust suppression', 'Uncovered municipal waste piles'];
      case 'construction':
        return ['Anti-smog guns & continuous water sprinkling', 'Wind-breaking green barrier netting', 'Uncovered sand & aggregate stockpiles', 'Vehicular wheel washing at site exit'];
      default:
        return ['Open burning & biomass fires', 'Diesel generator emissions', 'Fugitive dust'];
    }
  }

  return (
    <div className="flex-1 bg-stone-100 py-4 sm:py-8 px-2 sm:px-4 flex justify-center">
      {/* 390px mobile viewport frame */}
      <div className="w-full max-w-[390px] bg-white min-h-[720px] rounded-xl border border-stone-300 shadow-md flex flex-col overflow-hidden">
        {/* Mobile Header */}
        <div className="bg-stone-900 text-white p-4 sticky top-0 z-20">
          <div className="flex items-center justify-between mb-2">
            <Link
              href="/officer"
              className="inline-flex items-center gap-1 text-xs text-stone-300 hover:text-white"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Officer Desk</span>
            </Link>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-stone-800 text-stone-300 border border-stone-700">
              FIELD MOBILE (390px)
            </span>
          </div>

          <div className="text-sm font-bold tracking-tight">Field Inspection Dispatch</div>
          <div className="text-xs text-stone-300 font-mono mt-0.5 line-clamp-1">
            {caseData.station_name}
          </div>
          <div className="text-[11px] text-stone-400 mt-0.5">
            Event: {caseData.time_window?.interval_midpoint_ist || caseData.timestamp_ist}
          </div>
        </div>

        {/* Case Switcher for Field Inspector */}
        <div className="p-3 bg-stone-50 border-b border-stone-200">
          <label className="block text-[10px] font-mono uppercase text-stone-500 mb-1">
            Selected Episode
          </label>
          <div className="flex gap-1.5 overflow-x-auto pb-1 text-xs scrollbar-none">
            {ALL_CASE_IDS.map((cId) => (
              <Link
                key={cId}
                href={`/field/${cId}`}
                className={`px-2.5 py-1.5 rounded whitespace-nowrap text-xs font-mono transition-colors min-h-[36px] flex items-center ${
                  cId === caseId
                    ? 'bg-stone-900 text-white font-bold'
                    : 'bg-white border border-stone-300 text-stone-700 hover:bg-stone-100'
                }`}
              >
                {cId.replace('case_', '').replace('_2025', '').replace('_2026', '')}
              </Link>
            ))}
          </div>
        </div>

        {/* Wind conditions badge */}
        <div className="p-3 bg-stone-100 border-b border-stone-200 flex items-center justify-between text-xs">
          <div className="flex items-center gap-1.5 text-stone-800">
            <Wind className="w-4 h-4 text-stone-600" />
            <span>Prevailing wind: <strong>from {windDir.toFixed(0)}°</strong> ({getCompassSector(windDir)})</span>
          </div>
          <div className="flex items-center gap-1.5">
            {(caseData.is_low_wind || windSpeed < 1.5) && (
              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-200 text-amber-900 border border-amber-300">
                Low wind: direction unreliable
              </span>
            )}
            <span className="font-mono text-stone-600 text-[11px]">{windSpeed.toFixed(1)} m/s</span>
          </div>
        </div>

        {/* Content body */}
        <div className="p-3 space-y-3 flex-1 overflow-y-auto">
          {/* REFUSED DISPATCH CASE BANNER */}
          {isRefused && (
            <div className="bg-stone-50 border-2 border-stone-300 rounded-lg p-4 space-y-2">
              <div className="flex items-center gap-2 text-stone-900 font-bold text-sm">
                <AlertTriangle className="w-5 h-5 text-stone-700" />
                <span>NO DISPATCH RECOMMENDED</span>
              </div>
              <p className="text-xs text-stone-700 leading-relaxed font-sans">
                {caseData.refusal_reason || 'This spike is not a localized industrial emitter.'}
              </p>
              {(caseData.refusal_basis || caseData.refusal_reason) && (
                <div className="text-xs text-stone-800 font-mono bg-stone-100 p-2 rounded border border-stone-200">
                  <strong>Refusal basis:</strong> {caseData.refusal_basis || caseData.refusal_reason}
                </div>
              )}
              <div className="text-[11px] font-mono text-stone-500 pt-2 border-t border-stone-200">
                Action: Stand down field team. Sensor audit logged for maintenance team.
              </div>
            </div>
          )}

          {/* ACTIVE CANDIDATE CARDS */}
          {!isRefused && (
            <>
              {isComparable && !caseData.is_low_wind && windSpeed >= 1.5 && (
                <div className="bg-amber-50 border border-amber-300 rounded-lg p-3 text-xs text-amber-900 space-y-1">
                  <div className="font-bold font-mono text-[11px] uppercase tracking-wide text-amber-800">
                    INSPECTION SHORTLIST (comparable candidates)
                  </div>
                  <p>Candidates are comparable; this is a triage list, not an attribution.</p>
                </div>
              )}

              <div className="text-[11px] font-mono text-stone-500 uppercase tracking-wider px-1">
                {(caseData.is_low_wind || windSpeed < 1.5)
                  ? `areas to check (${caseData.shortlist?.length || 0} sites)`
                  : `Prioritized Inspection Route (${caseData.shortlist?.length || 0} sites)`}
              </div>

              {(caseData.shortlist || []).map((cand: Candidate, idx: number) => {
                const isLowWindCase = caseData.is_low_wind || windSpeed < 1.5;
                const sector = getCompassSector(cand.bearing_deg || 260);
                const offset = cand.angular_offset_deg ?? 15;
                const targets = getInspectionTargets(cand.type);
                const isDisused = cand.operating_status?.includes('disused') || cand.operating_status?.includes('decommissioned') || cand.name?.toLowerCase().includes('rajghat thermal');

                return (
                  <div
                    key={cand.id}
                    className="bg-white rounded-lg border border-stone-300 shadow-sm p-4 space-y-3"
                  >
                    {/* Header */}
                    <div className="flex items-start justify-between gap-2 border-b border-stone-100 pb-2.5">
                      <div>
                        <div className="flex items-center gap-1.5">
                          {!isLowWindCase ? (
                            <span className="w-5 h-5 rounded-full bg-stone-900 text-white font-mono text-xs flex items-center justify-center font-bold">
                              {idx + 1}
                            </span>
                          ) : (
                            <span className="w-2.5 h-2.5 rounded-full bg-stone-400 shrink-0 mr-1" />
                          )}
                          <span className="font-bold text-sm text-stone-900">{cand.name}</span>
                        </div>
                        <div className="text-[11px] text-stone-500 font-mono mt-0.5">
                          {cand.type} · ID: {cand.id}
                        </div>
                      </div>

                      {cand.confidence_tier && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-stone-100 text-stone-800 border border-stone-300">
                          {cand.confidence_tier.toUpperCase()}
                        </span>
                      )}
                    </div>

                    {/* Plain Language Transport Sentence */}
                    {isDisused ? (
                      <div className="text-xs text-stone-700 leading-relaxed bg-stone-50 p-2.5 rounded border border-stone-200">
                        Aligned with the wind, but tagged disused in OpenStreetMap, so inspection is unlikely to be useful.
                      </div>
                    ) : (
                      <div className="text-xs text-stone-800 leading-relaxed bg-stone-50 p-2.5 rounded border border-stone-200">
                        <strong>Confidence:</strong> {cand.confidence_tier}. {cand.type.charAt(0).toUpperCase() + cand.type.slice(1)} area, {cand.distance_km ?? 0.9} km {offset <= 25 ? 'upwind' : offset <= 45 ? 'somewhat off the wind line' : 'off the main wind line'} ({sector}). Wind was from the {getCompassSector(windDir)} ({windDir.toFixed(0)}°), so this site is {offset <= 25 ? 'upwind' : offset <= 45 ? 'somewhat off the wind line' : 'off the main wind line'}.
                      </div>
                    )}

                    {/* Operating Status */}
                    <div className="text-[11px] text-stone-600 flex items-center gap-1.5">
                      <span className="font-semibold text-stone-700">OSM Status:</span>
                      <span>{cand.operating_status_text || cand.operating_status}</span>
                    </div>

                    {/* Inspection Checklist for Officer on Foot */}
                    <div className="space-y-1.5 pt-1 border-t border-stone-100">
                      <div className="text-[11px] font-mono font-semibold text-stone-700 uppercase flex items-center gap-1">
                        <ClipboardCheck className="w-3.5 h-3.5 text-stone-600" />
                        <span>Inspect Upon Arrival:</span>
                      </div>
                      <div className="space-y-1">
                        {targets.map((tgt, tIdx) => (
                          <div
                            key={tIdx}
                            className="flex items-center gap-2 p-2 rounded bg-stone-50 border border-stone-200 text-xs text-stone-700 min-h-[44px]"
                          >
                            <Square className="w-4 h-4 text-stone-400 shrink-0" />
                            <span>{tgt}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Large Tap Target Action Buttons (Min 48px height) */}
                    <div className="pt-2 flex gap-2">
                      <button
                        type="button"
                        className="flex-1 min-h-[48px] bg-stone-900 hover:bg-stone-800 text-white rounded text-xs font-semibold flex items-center justify-center gap-1.5 shadow"
                      >
                        <MapPin className="w-4 h-4" />
                        <span>Directions</span>
                      </button>
                      <button
                        type="button"
                        className="flex-1 min-h-[48px] bg-white hover:bg-stone-50 border border-stone-300 text-stone-800 rounded text-xs font-semibold flex items-center justify-center gap-1.5"
                      >
                        <CheckCircle2 className="w-4 h-4 text-stone-600" />
                        <span>Mark Checked</span>
                      </button>
                    </div>
                  </div>
                );
              })}

              {/* Other Explanations Considered (Non-Site Outcomes) */}
              {caseData.other_explanations_considered && caseData.other_explanations_considered.length > 0 && (
                <div className="bg-white rounded-lg border border-stone-300 shadow-sm p-4 space-y-2 mt-3">
                  <div className="text-[11px] font-mono font-semibold text-stone-700 uppercase tracking-wide">
                    Other Explanations Considered:
                  </div>
                  <div className="space-y-2 text-xs">
                    {caseData.other_explanations_considered.map((exp: any) => (
                      <div key={exp.id} className="p-2.5 bg-stone-50 rounded border border-stone-200 space-y-0.5">
                        <div className="font-semibold text-stone-800 text-xs">{exp.name}</div>
                        <div className="text-stone-600 text-[11px] leading-relaxed">{exp.sentence}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="p-3 bg-stone-50 border-t border-stone-200 text-center text-[10px] font-mono text-stone-400">
          Smokeprint Field Mode · Offline Cached
        </div>
      </div>
    </div>
  );
}
