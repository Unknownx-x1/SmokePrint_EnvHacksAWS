'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { ArrowRight, Play, Pause, RotateCcw, Wind, ShieldAlert, MapPin } from 'lucide-react';

interface Frame {
  timeUTC: string;
  timeIST: string;
  pm25: number;
  excess: number;
  regionalMedian: number;
  windSpeed: number;
  windFromDeg: number;
  phase: string;
}

const REPLAY_FRAMES: Frame[] = [
  {
    timeUTC: '19:00 UTC',
    timeIST: '00:30 IST',
    pm25: 164,
    excess: 16,
    regionalMedian: 148,
    windSpeed: 2.1,
    windFromDeg: 260,
    phase: 'Background baseline'
  },
  {
    timeUTC: '20:00 UTC',
    timeIST: '01:30 IST',
    pm25: 235,
    excess: 87,
    regionalMedian: 148,
    windSpeed: 2.3,
    windFromDeg: 262,
    phase: 'Plume onset'
  },
  {
    timeUTC: '21:00 UTC',
    timeIST: '02:30 IST',
    pm25: 369,
    excess: 221,
    regionalMedian: 148,
    windSpeed: 2.56,
    windFromDeg: 263,
    phase: 'Peak local excess (+221 µg/m³)'
  },
  {
    timeUTC: '22:00 UTC',
    timeIST: '03:30 IST',
    pm25: 290,
    excess: 142,
    regionalMedian: 148,
    windSpeed: 2.4,
    windFromDeg: 265,
    phase: 'Plume advection downstream'
  },
  {
    timeUTC: '23:00 UTC',
    timeIST: '04:30 IST',
    pm25: 210,
    excess: 62,
    regionalMedian: 148,
    windSpeed: 2.2,
    windFromDeg: 268,
    phase: 'Diffusion & regional mixing'
  }
];

export default function LandingPage() {
  const [frameIdx, setFrameIdx] = useState(2); // start at peak
  const [isPlaying, setIsPlaying] = useState(true);

  useEffect(() => {
    if (!isPlaying) return;
    const interval = setInterval(() => {
      setFrameIdx((prev) => (prev + 1) % REPLAY_FRAMES.length);
    }, 2200);
    return () => clearInterval(interval);
  }, [isPlaying]);

  const frame = REPLAY_FRAMES[frameIdx];

  // Wind direction in meteorological convention is "wind from X deg"
  // The arrow shows where the air is moving (wind direction + 180 deg)
  const arrowRotation = frame.windFromDeg;

  return (
    <div className="flex-1 flex flex-col justify-center items-center px-4 py-8 sm:py-16 max-w-5xl mx-auto w-full">
      {/* Required single headline sentence */}
      <div className="text-center max-w-3xl mb-10">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono bg-stone-100 text-stone-700 border border-stone-200 mb-6">
          <ShieldAlert className="w-3.5 h-3.5 text-risk-600" />
          <span>DECISION SUPPORT PROTOTYPE · DELHI-NCR</span>
        </div>
        <h1 className="text-2xl sm:text-4xl font-semibold tracking-tight text-stone-900 leading-snug">
          A spike at a monitor is not a culprit. Smokeprint tells you whether to send an inspector, and where first.
        </h1>
        <p className="mt-4 text-sm text-stone-600 max-w-2xl mx-auto">
          Built for air quality inspection officers and field teams. Replaces raw monitor panic with physics-gated candidate shortlists, instrument fault rejection, and downwind corroboration.
        </p>
      </div>

      {/* Looping Replay of Anand Vihar Spike */}
      <div className="w-full bg-white rounded-lg border border-stone-200 shadow-sm overflow-hidden mb-10">
        <div className="bg-stone-50 border-b border-stone-200 px-4 py-3 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-risk-600 animate-pulse"></span>
            <span className="font-mono font-medium text-stone-900">LOOPING REPLAY: Anand Vihar Spike Event</span>
            <span className="text-stone-400">·</span>
            <span className="text-stone-600">Station 235 (DPCC)</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              className="inline-flex items-center gap-1 px-2.5 py-1 bg-white border border-stone-200 rounded text-stone-700 hover:bg-stone-50"
            >
              {isPlaying ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
              <span>{isPlaying ? 'Pause' : 'Play'}</span>
            </button>
            <button
              onClick={() => setFrameIdx(2)}
              className="inline-flex items-center gap-1 px-2.5 py-1 bg-white border border-stone-200 rounded text-stone-700 hover:bg-stone-50"
              title="Reset to peak"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Peak</span>
            </button>
          </div>
        </div>

        <div className="p-6 grid grid-cols-1 md:grid-cols-12 gap-6 items-center">
          {/* Visual Wind-From & Transport Diagram */}
          <div className="md:col-span-6 flex flex-col items-center justify-center p-6 bg-stone-50 rounded border border-stone-200 relative min-h-[260px]">
            <div className="text-[11px] font-mono text-stone-500 uppercase tracking-wider mb-2">
              Atmospheric Transport Geometry
            </div>

            {/* Compass rose & wind vector container */}
            <div className="relative w-44 h-44 flex items-center justify-center rounded-full border border-stone-200 bg-white shadow-inner">
              {/* Compass ticks */}
              <span className="absolute top-1 text-[10px] font-mono text-stone-400">N (0°)</span>
              <span className="absolute right-1 text-[10px] font-mono text-stone-400">E (90°)</span>
              <span className="absolute bottom-1 text-[10px] font-mono text-stone-400">S (180°)</span>
              <span className="absolute left-1 text-[10px] font-mono text-stone-400">W (270°)</span>

              {/* Station center marker */}
              <div className="w-4 h-4 rounded-full bg-stone-900 flex items-center justify-center z-10">
                <div className="w-1.5 h-1.5 rounded-full bg-white"></div>
              </div>

              {/* Upwind source area indication */}
              <div 
                className="absolute w-28 h-6 bg-risk-100/60 rounded-full blur-[2px] pointer-events-none"
                style={{
                  transform: `rotate(${frame.windFromDeg}deg) translate(-50px, 0)`,
                  transformOrigin: 'center center'
                }}
              ></div>

              {/* Wind-From Arrow */}
              {/* Meteorological: wind is coming FROM frame.windFromDeg and pushing across station */}
              <div
                className="absolute w-full h-full flex items-center justify-center transition-transform duration-700 ease-out pointer-events-none"
                style={{ transform: `rotate(${arrowRotation}deg)` }}
              >
                <div className="absolute left-2 flex items-center gap-1 bg-stone-900 text-white text-[10px] font-mono px-2 py-0.5 rounded shadow">
                  <Wind className="w-3 h-3" />
                  <span>from {frame.windFromDeg}°</span>
                </div>
                {/* Arrow line pointing through station */}
                <div className="w-32 h-0.5 bg-risk-600 relative flex items-center justify-end">
                  <div className="w-0 h-0 border-y-[4px] border-y-transparent border-l-[8px] border-l-risk-600 mr-[-2px]"></div>
                </div>
              </div>
            </div>

            <div className="mt-4 text-center">
              <div className="text-xs font-mono font-medium text-stone-900">
                Prevailing Wind: from {frame.windFromDeg}.0° at {frame.windSpeed.toFixed(2)} m/s
              </div>
              <div className="text-[11px] text-stone-500 mt-0.5">
                Upwind advection corridor: 263° (West) · Transport lag: 18 min
              </div>
            </div>
          </div>

          {/* Telemetry and Local Excess Gauges */}
          <div className="md:col-span-6 flex flex-col justify-between space-y-4">
            <div className="border border-stone-200 rounded p-4 bg-stone-50">
              <div className="flex items-center justify-between text-xs font-mono text-stone-500 mb-1">
                <span>OBSERVATION TIME</span>
                <span>{frame.phase}</span>
              </div>
              <div className="flex items-baseline justify-between">
                <span className="text-lg font-bold font-mono text-stone-900">{frame.timeUTC}</span>
                <span className="text-xs font-mono text-stone-600">({frame.timeIST} IST)</span>
              </div>
              <div className="text-[11px] text-stone-400 font-mono mt-0.5">
                Hourly interval midpoint convention · Asia/Kolkata (UTC+05:30)
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="border border-stone-200 rounded p-3 bg-white">
                <div className="text-[11px] font-mono text-stone-500 uppercase">Station PM2.5</div>
                <div className="text-2xl font-bold font-mono text-stone-900 mt-1 tabular-nums">
                  {frame.pm25} <span className="text-xs font-normal text-stone-500">µg/m³</span>
                </div>
                <div className="text-[10px] text-stone-500 mt-0.5">Continuous TEOM / Beta</div>
              </div>

              <div className="border border-risk-500/30 rounded p-3 bg-risk-50/50">
                <div className="text-[11px] font-mono text-risk-700 uppercase font-semibold">Local Excess</div>
                <div className="text-2xl font-bold font-mono text-risk-700 mt-1 tabular-nums">
                  +{frame.excess} <span className="text-xs font-normal text-risk-600">µg/m³</span>
                </div>
                <div className="text-[10px] text-risk-600 mt-0.5">Above regional median (148 µg/m³)</div>
              </div>
            </div>

            <div className="border border-stone-200 rounded p-3 bg-white text-xs text-stone-600 space-y-1.5">
              <div className="flex items-center justify-between font-mono text-[11px]">
                <span className="text-stone-500">Chemical signature:</span>
                <span className="text-stone-900 font-medium">Fine soot dominant (PM2.5/PM10 = 0.72)</span>
              </div>
              <div className="flex items-center justify-between font-mono text-[11px]">
                <span className="text-stone-500">Thermal NOx co-emission:</span>
                <span className="text-stone-900 font-medium">189.88 µg/m³ (high-temp combustion)</span>
              </div>
              <div className="flex items-center justify-between font-mono text-[11px]">
                <span className="text-stone-500">Top shortlisted area:</span>
                <span className="text-stone-900 font-medium">Patparganj Industrial Area (0.86 km upwind)</span>
              </div>
            </div>

            {/* Scrubber dots */}
            <div className="flex items-center justify-center gap-2 pt-2">
              {REPLAY_FRAMES.map((_, idx) => (
                <button
                  key={idx}
                  onClick={() => { setFrameIdx(idx); setIsPlaying(false); }}
                  className={`h-1.5 rounded-full transition-all ${
                    idx === frameIdx ? 'w-6 bg-stone-900' : 'w-2 bg-stone-200 hover:bg-stone-400'
                  }`}
                  aria-label={`Frame ${idx + 1}`}
                />
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Exactly one primary button into /officer */}
      <div>
        <Link
          href="/officer"
          className="inline-flex items-center gap-3 px-6 py-3.5 bg-stone-900 hover:bg-stone-800 text-white rounded font-medium text-sm transition-all shadow-sm hover:shadow"
        >
          <span>Open Officer Inspection Desk</span>
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  );
}
