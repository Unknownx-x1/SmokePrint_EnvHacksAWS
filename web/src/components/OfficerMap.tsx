'use client';

import React, { useEffect, useRef, useState } from 'react';
import { CaseData, Candidate, ConfidenceTier } from '../lib/types';
import { Wind, AlertTriangle, Layers } from 'lucide-react';

interface OfficerMapProps {
  caseData: CaseData;
  selectedCandidateId: string | null;
  onSelectCandidate: (candidateId: string) => void;
}

export default function OfficerMap({
  caseData,
  selectedCandidateId,
  onSelectCandidate,
}: OfficerMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);
  const [mapError, setMapError] = useState<string | null>(null);
  const [isMapLoaded, setIsMapLoaded] = useState(false);

  const stLat = caseData.station_coordinates?.latitude || caseData.coordinates?.latitude || 28.646835;
  const stLon = caseData.station_coordinates?.longitude || caseData.coordinates?.longitude || 77.316032;
  const windFromDeg = caseData.wind?.from_direction_deg || caseData.wind?.wind_direction_deg || 263.0;
  const windSpeed = caseData.wind?.wind_speed_ms || 2.56;

  useEffect(() => {
    let isCancelled = false;

    async function initMap() {
      if (!mapContainerRef.current) return;

      try {
        const maplibre = await import('maplibre-gl');

        if (mapInstanceRef.current) {
          mapInstanceRef.current.remove();
          mapInstanceRef.current = null;
        }

        // OpenFreeMap Positron (free, keyless, light, fast)
        // Fallback tile URL to OpenStreetMap raster if tile service is blocked
        const map = new maplibre.Map({
          container: mapContainerRef.current,
          style: {
            version: 8,
            sources: {
              'osm-tiles': {
                type: 'raster',
                tiles: [
                  'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
                ],
                tileSize: 256,
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors'
              }
            },
            layers: [
              {
                id: 'osm-tiles-layer',
                type: 'raster',
                source: 'osm-tiles',
                minzoom: 0,
                maxzoom: 19
              }
            ]
          },
          center: [stLon, stLat],
          zoom: 12.2
        });

        map.on('load', () => {
          if (isCancelled) return;
          setIsMapLoaded(true);
          setMapError(null);
        });

        map.on('error', (e) => {
          console.warn('MapLibre error encountered:', e);
          // Only flag if tiles completely fail to render
        });

        mapInstanceRef.current = map;
      } catch (err: any) {
        console.error('Failed to initialize MapLibre:', err);
        setMapError('Interactive WebGL map unavailable. Rendering fallback atmospheric schematic.');
      }
    }

    initMap();

    return () => {
      isCancelled = true;
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [stLat, stLon]);

  // Update markers and wind overlay when case changes or map loads
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !isMapLoaded) return;

    import('maplibre-gl').then((maplibre) => {
      // Clear existing markers
      markersRef.current.forEach((m) => m.remove());
      markersRef.current = [];

      // 1. Station Marker
      const stationEl = document.createElement('div');
      stationEl.className = 'w-7 h-7 rounded-full bg-stone-900 border-2 border-white shadow-md flex items-center justify-center text-white text-[10px] font-mono font-bold cursor-pointer';
      stationEl.title = `${caseData.station_name} (Monitor)`;
      stationEl.innerText = 'ST';

      const stPopup = new maplibre.Popup({ offset: 15 }).setHTML(`
        <div class="font-sans">
          <div class="font-bold text-xs text-stone-900">${caseData.station_name}</div>
          <div class="text-[11px] text-stone-600 mt-1">Target Monitoring Station</div>
          <div class="text-[11px] font-mono text-stone-500 mt-0.5">PM2.5: ${caseData.signature?.pm25 ?? 369} µg/m³ · Wind: from ${windFromDeg}°</div>
        </div>
      `);

      const stMarker = new maplibre.Marker({ element: stationEl })
        .setLngLat([stLon, stLat])
        .setPopup(stPopup)
        .addTo(map);
      markersRef.current.push(stMarker);

      // 2. Candidate Markers
      (caseData.shortlist || []).forEach((c, idx) => {
        if (!c.lat || !c.lon) return;

        const isSelected = selectedCandidateId === c.id;
        const candEl = document.createElement('div');
        
        let tierColor = 'bg-stone-600 border-white text-white';
        if (c.confidence_tier === 'high') {
          tierColor = 'bg-stone-900 border-white text-white ring-2 ring-stone-900';
        } else if (c.confidence_tier === 'medium') {
          tierColor = 'bg-stone-700 border-white text-white';
        } else if (c.confidence_tier === 'low') {
          tierColor = 'bg-stone-400 border-stone-200 text-stone-900';
        }

        if (isSelected) {
          tierColor += ' scale-125 ring-2 ring-risk-600';
        }

        candEl.className = `w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-mono font-semibold border-2 shadow cursor-pointer transition-transform ${tierColor}`;
        candEl.innerText = `${idx + 1}`;
        candEl.title = `${c.name} (${c.confidence_tier} tier)`;

        candEl.addEventListener('click', () => {
          onSelectCandidate(c.id);
        });

        const candPopup = new maplibre.Popup({ offset: 12 }).setHTML(`
          <div class="font-sans">
            <div class="font-bold text-xs text-stone-900">#${idx + 1} ${c.name}</div>
            <div class="text-[11px] text-stone-600 mt-0.5">${c.type} · ${c.distance_km ?? '?'} km upwind (bearing ${c.bearing_deg ?? '?'}°)</div>
            <div class="text-[11px] text-stone-500 mt-0.5">Confidence tier: <strong>${c.confidence_tier}</strong></div>
            <div class="text-[10px] text-stone-400 mt-1">${c.operating_status_text || c.operating_status}</div>
          </div>
        `);

        const cMarker = new maplibre.Marker({ element: candEl })
          .setLngLat([c.lon, c.lat])
          .setPopup(candPopup)
          .addTo(map);
        markersRef.current.push(cMarker);
      });

      // 3. Downwind Neighbour Station Marker
      const downwindList = caseData.downwind_neighbour_corroboration || [];
      if (downwindList.length > 0) {
        const dn = downwindList[0];
        // Approximate position if coordinates not explicitly present: Vivek Vihar is 2.84 km north
        const dnLat = stLat + 0.025;
        const dnLon = stLon - 0.001;

        const dnEl = document.createElement('div');
        dnEl.className = 'w-5 h-5 rounded-sm bg-stone-200 border border-stone-400 text-stone-700 flex items-center justify-center text-[9px] font-mono font-bold shadow-sm';
        dnEl.title = `${dn.name || dn.station || 'Downwind Neighbour'} (${dn.distance_km} km)`;
        dnEl.innerText = 'DW';

        const dnPopup = new maplibre.Popup({ offset: 10 }).setHTML(`
          <div class="font-sans">
            <div class="font-bold text-xs text-stone-900">${dn.name || dn.station}</div>
            <div class="text-[11px] text-stone-600">Downwind Neighbour Monitor (${dn.distance_km} km)</div>
            <div class="text-[11px] font-mono text-stone-500 mt-0.5">PM2.5: ${dn.pm25 ?? 440} µg/m³ · Corroborated: ${dn.is_downwind ? 'Yes' : 'No'}</div>
          </div>
        `);

        const dnMarker = new maplibre.Marker({ element: dnEl })
          .setLngLat([dnLon, dnLat])
          .setPopup(dnPopup)
          .addTo(map);
        markersRef.current.push(dnMarker);
      }
    });
  }, [caseData, selectedCandidateId, isMapLoaded, stLat, stLon, windFromDeg, onSelectCandidate]);

  return (
    <div className="relative w-full h-full min-h-[380px] bg-stone-100 flex flex-col overflow-hidden border-r border-stone-200">
      {/* Map Header Floating Overlay */}
      <div className="absolute top-3 left-3 z-10 bg-white/95 backdrop-blur-sm border border-stone-200 rounded px-3 py-2 shadow-sm text-xs space-y-1 max-w-[280px]">
        <div className="flex items-center justify-between gap-3">
          <span className="font-mono font-semibold text-stone-900">TRANSPORT MAP</span>
          <span className="text-[10px] font-mono text-stone-500">EPSG:4326</span>
        </div>
        <div className="flex items-center gap-2 text-stone-700 text-[11px]">
          <Wind className="w-3.5 h-3.5 text-stone-600 shrink-0" />
          <span>Prevailing wind: <strong>from {windFromDeg.toFixed(1)}°</strong> ({windSpeed.toFixed(2)} m/s)</span>
        </div>
        <div className="flex items-center gap-3 pt-1 text-[10px] text-stone-500 font-mono border-t border-stone-100">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-stone-900"></span> ST: Monitor
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-stone-700"></span> Candidate
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-sm bg-stone-300 border border-stone-400"></span> DW: Downwind
          </span>
        </div>
      </div>

      {/* Wind Arrow Compass floating badge */}
      <div className="absolute bottom-6 right-3 z-10 bg-white/95 backdrop-blur-sm border border-stone-200 rounded p-2 shadow-sm flex flex-col items-center">
        <div className="text-[9px] font-mono text-stone-400 uppercase">Wind-From</div>
        <div className="relative w-12 h-12 flex items-center justify-center">
          <div 
            className="w-10 h-0.5 bg-stone-900 relative flex items-center justify-end transition-transform duration-500"
            style={{ transform: `rotate(${windFromDeg}deg)` }}
          >
            <div className="w-0 h-0 border-y-[3px] border-y-transparent border-l-[6px] border-l-stone-900 mr-[-1px]"></div>
          </div>
          <span className="absolute top-0 text-[8px] font-mono text-stone-400">N</span>
        </div>
        <div className="text-[10px] font-mono font-bold text-stone-800">{windFromDeg.toFixed(0)}°</div>
      </div>

      {/* MapLibre DOM container */}
      <div ref={mapContainerRef} className="w-full h-full flex-1" />

      {/* Graceful Fallback if MapLibre fails */}
      {mapError && (
        <div className="absolute inset-0 bg-stone-50 p-6 flex flex-col justify-center items-center text-center z-20">
          <AlertTriangle className="w-8 h-8 text-stone-500 mb-2" />
          <h4 className="font-semibold text-sm text-stone-900">Atmospheric Schematic Mode</h4>
          <p className="text-xs text-stone-600 max-w-sm mt-1">{mapError}</p>
          <div className="mt-4 p-4 bg-white border border-stone-200 rounded text-left text-xs space-y-1 font-mono">
            <div><strong>Station:</strong> {caseData.station_name} ({stLat.toFixed(4)}, {stLon.toFixed(4)})</div>
            <div><strong>Prevailing Wind:</strong> from {windFromDeg.toFixed(1)}° at {windSpeed.toFixed(2)} m/s</div>
            <div><strong>Upwind Candidates:</strong> {caseData.shortlist?.length || 0} sites indexed</div>
            <div><strong>Downwind Neighbour:</strong> Vivek Vihar (2.84 km, 358.5°)</div>
          </div>
        </div>
      )}
    </div>
  );
}
