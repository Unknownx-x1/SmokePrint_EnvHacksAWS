import json
import os
import sys
import glob

sys.path.insert(0, os.getcwd())
from data.qc import run_qc_on_station

files = glob.glob('data/stations_12m/station_*_12m.json')
candidates = []

for f in files:
    with open(f) as fp:
        st = json.load(fp)
    clean_dict, stats = run_qc_on_station(st)
    if not clean_dict:
        continue
    # find row at 2025-10-20T17:00:00Z
    rec = [r for r in clean_dict.get('records', []) if r.get('timestamp_utc') == '2025-10-20T17:00:00Z']
    if rec:
        r = rec[0]
        val = r.get('pm25')
        is_suspect = r.get('is_suspect', False)
        faults = clean_dict.get('fault_reasons', {}).get('2025-10-20T17:00:00Z', [])
        candidates.append({
            'station_id': st['station_id'],
            'name': st['name'],
            'pm25': val,
            'pm10': r.get('pm10'),
            'is_suspect': is_suspect,
            'faults': faults
        })

candidates.sort(key=lambda x: (x['pm25'] is not None, x['pm25'] or 0), reverse=True)
reporting = [c for c in candidates if c['pm25'] is not None]
print(f"Total reporting stations at 2025-10-20 17:00Z: {len(reporting)}")
print("\nTop 10 reporting stations:")
for c in candidates[:10]:
    clean_str = 'CLEAN' if not c['is_suspect'] and not c['faults'] else f'SUSPECT: {c["faults"]}'
    print(f"Station {c['station_id']} - {c['name']}: PM2.5 = {c['pm25']} ug/m3 | {clean_str}")

clean_cands = [c for c in candidates if not c['is_suspect'] and not c['faults'] and c['pm25'] is not None]
if clean_cands:
    top_clean = clean_cands[0]
    print(f"\nHighest QC-clean station: Station {top_clean['station_id']} ({top_clean['name']}) with PM2.5 = {top_clean['pm25']} ug/m3")
