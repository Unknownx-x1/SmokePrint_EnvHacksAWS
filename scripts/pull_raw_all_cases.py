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
            pass
    if not dfs:
        return pd.DataFrame()
    df = pd.concat(dfs, ignore_index=True)
    df['datetime_utc'] = pd.to_datetime(df['datetime'], utc=True)
    return df

cases = [
    {
        "name": "Anand Vihar (235) - 2025-11-02",
        "loc_id": 235,
        "dates": [(2025, 11, 2), (2025, 11, 3)],
        "start": "2025-11-02 18:00:00+00:00",
        "end": "2025-11-03 00:00:00+00:00"
    },
    {
        "name": "Anand Vihar (235) - 2026-01-31",
        "loc_id": 235,
        "dates": [(2026, 1, 30), (2026, 1, 31)],
        "start": "2026-01-31 02:00:00+00:00",
        "end": "2026-01-31 08:00:00+00:00"
    },
    {
        "name": "R K Puram (17) - 2025-11-12",
        "loc_id": 17,
        "dates": [(2025, 11, 12), (2025, 11, 13)],
        "start": "2025-11-12 13:00:00+00:00",
        "end": "2025-11-12 19:00:00+00:00"
    },
    {
        "name": "CRRI Mathura Road (5627) - 2026-05-15/16",
        "loc_id": 5627,
        "dates": [(2026, 5, 15), (2026, 5, 16)],
        "start": "2026-05-15 20:00:00+00:00",
        "end": "2026-05-16 02:00:00+00:00"
    },
    {
        "name": "Gurugram Sec-51 (301) - 2026-06-30",
        "loc_id": 301,
        "dates": [(2026, 6, 30), (2026, 7, 1)],
        "start": "2026-06-30 06:00:00+00:00",
        "end": "2026-06-30 14:00:00+00:00"
    }
]

print("=== RAW OPENAQ ROWS FROM PUBLIC S3 ARCHIVE (s3://openaq-data-archive) ===\n")
for c in cases:
    print(f"--------------------------------------------------------------------------------")
    print(f"Station: {c['name']} | Window: {c['start']} to {c['end']}")
    df = get_archive_df(c["loc_id"], c["dates"])
    if df.empty:
        print("  No rows found in S3 archive.")
        continue
    sub = df[(df['datetime_utc'] >= c['start']) & (df['datetime_utc'] <= c['end'])]
    sub = sub[sub['parameter'].isin(['pm25', 'pm10'])].sort_values(['datetime_utc', 'parameter'])
    print(f"{'Sensor ID':<12} | {'Datetime From/To (UTC)':<32} | {'Parameter':<8} | {'Value':<8} | {'Unit'}")
    print(f"{'-'*12} | {'-'*32} | {'-'*8} | {'-'*8} | {'-'*8}")
    for idx, r in sub.iterrows():
        dt_str = str(r['datetime_utc'])[:19] + " UTC"
        # 15-minute interval window
        t_from = dt_str
        val = r['value']
        unit = "ug/m3"
        print(f"{r['sensors_id']:<12} | {t_from:<32} | {r['parameter']:<8} | {val:<8.1f} | {unit}")
    print()
