import os
import json
import math
import boto3
from typing import Dict, Any, List

try:
    from tier_rules import determine_confidence_tier
    from shortlist_builder import build_enriched_shortlist
except ImportError:
    from data.tier_rules import determine_confidence_tier
    from data.shortlist_builder import build_enriched_shortlist

s3 = boto3.client("s3")
DATA_BUCKET = os.environ.get("DATA_BUCKET")

def handler(event, context):
    case_id = event.get("case_id")
    run_id = event.get("run_id")
    bundle = event.get("bundle", {})

    # Load canonical case JSON from S3
    s3_key = f"cases/{case_id}.json"
    try:
        obj = s3.get_object(Bucket=DATA_BUCKET, Key=s3_key)
        case_data = json.loads(obj["Body"].read().decode("utf-8"))
    except Exception as e:
        # Fallback to bundle if present
        case_data = bundle.get("case_facts", bundle)

    enriched = build_enriched_shortlist(case_data)
    enriched["run_id"] = run_id
    return enriched
