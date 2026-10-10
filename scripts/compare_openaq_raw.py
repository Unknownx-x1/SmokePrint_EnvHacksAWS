import boto3
import gzip
import io
import json
import os
import pandas as pd
from botocore import UNSIGNED
from botocore.config import Config

s3 = boto3.client('s3', region_name='us-east-1', config=Config(signature_version=UNSIGNED))

def get_archive_df(loc_id, dates):
    dfs = []
    for (y, m, d) in dates:
        k = f'records/csv.gz/locationid={loc_id}/year={y}/month={m:02d}/location-{loc_id}-{y}{m:02d}{d:02d}.csv.gz'
        try:
            obj = s3.get_object(Bucket='openaq-data-archive', Key=k)
            with gzip.GzipFile(fileobj=io.BytesIO(obj['Body'].read())) as gz:
                dfs.append(pd.read_csv(gz))
        except Exception as e:
            print(f'Warning: failed {k}: {e}')
    if not dfs:
        return pd.DataFrame()
    df = pd.concat(dfs, ignore_index=True)
    df['datetime_utc'] = pd.to_datetime(df['datetime'], utc=True)
    return df

cases_meta = [
    ('Anand Vihar Nov 2025', 235, [(2025, 11, 2), (2025, 11, 3)], '2025-11-02 18:00:00+00:00', '2025-11-03 00:30:00+00:00', 'case_anand_vihar_20251102'),
    ('Anand Vihar Jan 2026', 235, [(2026, 1, 30), (2026, 1, 31)], '2026-01-31 02:00:00+00:00', '2026-01-31 08:30:00+00:00', 'case_anand_vihar_20260131'),
    ('RK Puram Nov 2025', 17, [(2025, 11, 12), (2025, 11, 13)], '2025-11-12 13:00:00+00:00', '2025-11-12 20:00:00+00:00', 'case_rkpuram_20251112'),
    ('CRRI May 2026', 5627, [(2026, 5, 15), (2026, 5, 16)], '2026-05-15 20:00:00+00:00', '2026-05-16 03:00:00+00:00', 'case_crri_20260515'),
    ('Gurugram June 2026', 301, [(2026, 6, 30), (2026, 7, 1)], '2026-06-30 06:00:00+00:00', '2026-06-30 14:00:00+00:00', 'case_gurugram_20260630'),
]

for label, loc_id, dates, t_start, t_end, case_id in cases_meta:
    print('=' * 60)
    print(f'Case: {label} (loc_id={loc_id}, case_id={case_id})')
    print(f'Window: {t_start} to {t_end}')
    
    # 1. Archive
    df = get_archive_df(loc_id, dates)
    if not df.empty:
        sub = df[(df['datetime_utc'] >= t_start) & (df['datetime_utc'] <= t_end)]
        sub = sub[sub['parameter'].isin(['pm25', 'pm10'])].sort_values(['datetime_utc', 'parameter'])
        print(f'--- Public S3 Archive Raw Measurements (total {len(sub)} rows in window) ---')
        for dt, grp in sub.groupby('datetime_utc'):
            p25_rows = grp[grp['parameter'] == 'pm25']
            p10_rows = grp[grp['parameter'] == 'pm10']
            p25_val = p25_rows['value'].values.tolist()
            p25_sid = p25_rows['sensors_id'].values.tolist()
            p10_val = p10_rows['value'].values.tolist()
            p10_sid = p10_rows['sensors_id'].values.tolist()
            print(f'  {dt}: PM2.5(s={p25_sid})={p25_val}, PM10(s={p10_sid})={p10_val}')
            
    # 2. stations_12m
    st_path = f'data/stations_12m/station_{loc_id}_12m.json'
    if os.path.exists(st_path):
        with open(st_path) as fp:
            st_data = json.load(fp)
        p25_12m = st_data.get('data', {}).get('pm25', {})
        p10_12m = st_data.get('data', {}).get('pm10', {})
        print(f'--- data/stations_12m/station_{loc_id}_12m.json ---')
        for k in sorted(p25_12m.keys()):
            k_dt = k.replace('Z', '+00:00')
            if (t_start[:10] in k or t_end[:10] in k) and (t_start <= k_dt <= t_end):
                print(f'  {k}: PM2.5={p25_12m.get(k)}, PM10={p10_12m.get(k)}')
                    
    # 3. Canonical case JSON
    case_path = f'data/cases_out/{case_id}.json'
    if os.path.exists(case_path):
        with open(case_path) as fp:
            cdata = json.load(fp)
        print(f'--- Canonical case JSON signature & hourly_series ---')
        sig = cdata.get('signature', {})
        print(f'  Signature: PM2.5={sig.get("pm25")}, PM10={sig.get("pm10")}, ratio={sig.get("ratio_pm25_pm10")}')
        hs = cdata.get('hourly_series', {})
        print(f'  hourly_series sensor={hs.get("sensor_id")}, readings:')
        for r in hs.get('readings', []):
            print(f'    {r.get("timestamp_utc")} ({r.get("offset_label")}): {r.get("pm25_ugm3")}')
