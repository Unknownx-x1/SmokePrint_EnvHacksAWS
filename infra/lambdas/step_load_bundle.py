import os
import json
import boto3

s3 = boto3.client("s3")
DATA_BUCKET = os.environ.get("DATA_BUCKET")

def handler(event, context):
    case_id = event.get("case_id")
    run_id = event.get("run_id")
    triggered_at = event.get("triggered_at")

    if not case_id:
        raise ValueError("Missing required field: case_id")

    s3_key = f"bundles/{case_id}.json"
    try:
        obj = s3.get_object(Bucket=DATA_BUCKET, Key=s3_key)
        bundle_data = json.loads(obj["Body"].read().decode("utf-8"))
    except Exception as e:
        raise RuntimeError(f"Failed to load case bundle from s3://{DATA_BUCKET}/{s3_key}: {e}")

    return {
        "case_id": case_id,
        "run_id": run_id,
        "triggered_at": triggered_at,
        "bundle": bundle_data
    }
