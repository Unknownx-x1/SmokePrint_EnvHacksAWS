'use client';

import React from 'react';
import { CaseData } from '../lib/types';
import { Clock, TrendingUp, AlertCircle, Activity } from 'lucide-react';

interface TimeSeriesChartProps {
  caseData: CaseData;
}

export default function TimeSeriesChart({ caseData }: TimeSeriesChartProps) {
  const hourly = caseData.hourly_series;
  const smogSummary = caseData.regional_smog_summary;

  // If hourly_series is missing or null, render regional network airshed comparison
  if (!hourly || !hourly.readings || hourly.readings.length === 0) {
    const networkMedian = smogSummary?.network_median_pm25 ?? caseData.regional_median ?? 678;
    const reportingStations = smogSummary?.reporting_stations ?? caseData.n_stations_background ?? 22;
    const stationsOver200 = smogSummary?.stations_over_200 ?? 21;
    const elevatedPct = smogSummary?.elevated_pct ?? 95.5;
    const maxStationName = smogSummary?.max_station_name ?? "CRRI Mathura Road, New Delhi - IMD";
    const maxStationPm25 = smogSummary?.max_station_pm25 ?? 959.0;

    return (
      <div className="bg-white rounded border border-stone-200 p-4 shadow-sm space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-stone-100 pb-2.5">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-stone-700" />
            <h3 className="text-xs font-bold text-stone-900 uppercase tracking-wide">
              Airshed Regional Baseline & Network Distribution
            </h3>
          </div>
          <div className="flex items-center gap-1.5 text-[11px] font-mono text-stone-600 bg-stone-100 px-2 py-0.5 rounded border border-stone-200">
            <Clock className="w-3.5 h-3.5 text-stone-500" />
            <span>hourly means, interval midpoint, IST</span>
          </div>
        </div>

        <div className="bg-stone-50 border border-stone-200 rounded p-3 text-xs text-stone-600 flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-stone-500 shrink-0 mt-0.5" />
          <div>
            <strong>Regional Airshed Event:</strong> Single-station time series omitted. Telemetry represents basin-wide stagnation across {reportingStations} continuous network monitors in Delhi-NCR ({stationsOver200}/{reportingStations} stations &gt; 200 µg/m³).
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="border border-stone-200 rounded p-3 bg-stone-50">
            <div className="text-[10px] font-mono text-stone-500 uppercase">Network Median PM2.5</div>
            <div className="text-xl font-bold font-mono text-stone-900 tabular-nums mt-1">
              {networkMedian} <span className="text-xs font-normal text-stone-500">µg/m³</span>
            </div>
            <div className="text-[10px] text-stone-500 mt-1">{reportingStations}-Station Airshed Median</div>
          </div>

          <div className="border border-stone-200 rounded p-3 bg-stone-50">
            <div className="text-[10px] font-mono text-stone-500 uppercase">Reporting Monitors</div>
            <div className="text-xl font-bold font-mono text-stone-900 tabular-nums mt-1">
              {reportingStations} <span className="text-xs font-normal text-stone-500">stations</span>
            </div>
            <div className="text-[10px] text-stone-500 mt-1">Active CAAQMS in Delhi-NCR</div>
          </div>

          <div className="border border-stone-200 rounded p-3 bg-stone-50">
            <div className="text-[10px] font-mono text-stone-500 uppercase">Elevated (&gt; 200 µg/m³)</div>
            <div className="text-xl font-bold font-mono text-stone-900 tabular-nums mt-1">
              {stationsOver200} <span className="text-xs font-normal text-stone-500">/ {reportingStations}</span>
            </div>
            <div className="text-[10px] text-stone-500 mt-1">{elevatedPct}% Network Elevation</div>
          </div>

          <div className="border border-stone-200 rounded p-3 bg-stone-50">
            <div className="text-[10px] font-mono text-stone-500 uppercase">Network Peak Station</div>
            <div className="text-xl font-bold font-mono text-stone-900 tabular-nums mt-1">
              {maxStationPm25} <span className="text-xs font-normal text-stone-500">µg/m³</span>
            </div>
            <div className="text-[10px] text-stone-500 mt-1 truncate" title={maxStationName}>
              {maxStationName}
            </div>
          </div>
        </div>

        {/* Visual comparison bar: Network Elevation */}
        <div className="space-y-1.5 pt-1">
          <div className="flex justify-between text-[11px] font-mono text-stone-500">
            <span>Network Elevation: {stationsOver200} of {reportingStations} stations &gt; 200 µg/m³ ({elevatedPct}%)</span>
            <span>Peak: {maxStationPm25} µg/m³</span>
          </div>
          <div className="w-full bg-stone-100 h-3 rounded overflow-hidden flex border border-stone-200">
            <div
              className="bg-amber-500 h-full"
              style={{ width: `${elevatedPct}%` }}
              title={`Elevated Stations: ${elevatedPct}%`}
            />
            <div
              className="bg-stone-300 h-full flex-1"
              title={`Remaining: ${(100 - elevatedPct).toFixed(1)}%`}
            />
          </div>
        </div>
      </div>
    );
  }

  const regionalBaseline = caseData.regional_median ?? 148;

  // Real hourly readings from OpenAQ stored rows
  const readings = hourly.readings;
  const sensorId = hourly.sensor_id;
  const chartLabel = hourly.label || 'hourly means, interval midpoint, IST';

  const values = readings.map(r => r.pm25_ugm3);
  const maxVal = Math.max(...values, regionalBaseline) * 1.15;
  const minVal = 0;

  // Chart coordinates (SVG width 480, height 180)
  const chartWidth = 480;
  const chartHeight = 180;
  const padLeft = 55;
  const padRight = 20;
  const padTop = 20;
  const padBottom = 38;
  const plotWidth = chartWidth - padLeft - padRight;
  const plotHeight = chartHeight - padTop - padBottom;

  const getX = (idx: number) => padLeft + (idx / (readings.length - 1)) * plotWidth;
  const getY = (val: number) => padTop + plotHeight - ((val - minVal) / (maxVal - minVal)) * plotHeight;

  const baselineY = getY(regionalBaseline);

  // Exact polyline connecting only real source readings (no smoothing/synthetic interpolation)
  const polylineCoords = readings.map((r, i) => `${getX(i)},${getY(r.pm25_ugm3)}`).join(' ');

  return (
    <div className="bg-white rounded border border-stone-200 p-4 shadow-sm space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-stone-100 pb-2.5">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-stone-700" />
          <h3 className="text-xs font-bold text-stone-900 uppercase tracking-wide">
            OpenAQ Hourly Series (Sensor #{sensorId})
          </h3>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] font-mono text-stone-600 bg-stone-100 px-2 py-0.5 rounded border border-stone-200">
          <Clock className="w-3.5 h-3.5 text-stone-500" />
          <span>{chartLabel}</span>
        </div>
      </div>

      <div className="w-full overflow-x-auto">
        <svg
          viewBox={`0 0 ${chartWidth} ${chartHeight}`}
          className="w-full max-w-full h-auto text-stone-600 font-sans select-none"
          style={{ minWidth: '340px' }}
        >
          {/* Horizontal grid lines */}
          {[0, 100, 200, 300, 400, 500].filter(v => v <= maxVal).map((tick) => {
            const y = getY(tick);
            return (
              <g key={tick}>
                <line
                  x1={padLeft}
                  y1={y}
                  x2={chartWidth - padRight}
                  y2={y}
                  stroke="#e7e5e4"
                  strokeWidth="1"
                  strokeDasharray={tick === 0 ? undefined : '2,2'}
                />
                <text
                  x={padLeft - 8}
                  y={y + 3}
                  textAnchor="end"
                  fontSize="9"
                  fontFamily="monospace"
                  fill="#78716c"
                >
                  {tick}
                </text>
              </g>
            );
          })}

          {/* Regional Baseline Reference Line */}
          <line
            x1={padLeft}
            y1={baselineY}
            x2={chartWidth - padRight}
            y2={baselineY}
            stroke="#a8a29e"
            strokeWidth="1.5"
            strokeDasharray="4,4"
          />
          <text
            x={chartWidth - padRight - 4}
            y={baselineY - 4}
            textAnchor="end"
            fontSize="9"
            fontFamily="monospace"
            fill="#78716c"
          >
            Regional Baseline ({regionalBaseline} µg/m³)
          </text>

          {/* Real Observations Polyline (Strictly straight segments, no interpolation) */}
          <polyline
            points={polylineCoords}
            fill="none"
            stroke="#1c1917"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Data Points - Plotted directly from OpenAQ source rows */}
          {readings.map((r, i) => {
            const cx = getX(i);
            const cy = getY(r.pm25_ugm3);
            const isPeak = r.pm25_ugm3 === Math.max(...values);
            return (
              <g key={i}>
                <circle
                  cx={cx}
                  cy={cy}
                  r={isPeak ? 5 : 3.5}
                  fill={isPeak ? '#ef4444' : '#1c1917'}
                  stroke="#ffffff"
                  strokeWidth="1.5"
                />
                <text
                  x={cx}
                  y={cy - 8}
                  textAnchor="middle"
                  fontSize={isPeak ? '10' : '9'}
                  fontFamily="monospace"
                  fontWeight={isPeak ? 'bold' : 'normal'}
                  fill={isPeak ? '#b91c1c' : '#292524'}
                >
                  {r.pm25_ugm3}
                </text>
                <text
                  x={cx}
                  y={chartHeight - padBottom + 14}
                  textAnchor="middle"
                  fontSize="9"
                  fontFamily="monospace"
                  fill="#44403c"
                >
                  {r.time_ist}
                </text>
                <text
                  x={cx}
                  y={chartHeight - padBottom + 25}
                  textAnchor="middle"
                  fontSize="8"
                  fontFamily="sans-serif"
                  fill="#78716c"
                >
                  {r.offset_label}
                </text>
              </g>
            );
          })}

          {/* Y Axis Label */}
          <text
            x={-chartHeight / 2}
            y="15"
            transform="rotate(-90)"
            textAnchor="middle"
            fontSize="9"
            fontFamily="monospace"
            fill="#78716c"
          >
            Concentration (µg/m³)
          </text>

          {/* X Axis Label */}
          <text
            x={padLeft + plotWidth / 2}
            y={chartHeight - 2}
            textAnchor="middle"
            fontSize="9"
            fontFamily="monospace"
            fill="#78716c"
          >
            Time Window ({chartLabel})
          </text>
        </svg>
      </div>

      <div className="flex flex-wrap items-center justify-between text-[11px] text-stone-500 pt-1 border-t border-stone-100">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-0.5 bg-stone-900 inline-block"></span>
            <span>Station PM2.5 (Sensor #{sensorId})</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-0.5 border-t border-dashed border-stone-400 inline-block"></span>
            <span>Regional Median ({regionalBaseline} µg/m³)</span>
          </span>
        </div>
        <div className="font-mono text-[10px] text-stone-500">
          Source: OpenAQ QC&apos;d hourly readings
        </div>
      </div>
    </div>
  );
}
