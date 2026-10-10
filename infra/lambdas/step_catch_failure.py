import os
import json
from datetime import datetime, timezone
import boto3

dynamodb = boto3.resource("dynamodb")
RUNS_TABLE_NAME = os.environ.get("RUNS_TABLE")
runs_table = dynamodb.Table(RUNS_TABLE_NAME) if RUNS_TABLE_NAME else None

def handler(event, context):
    error_info = event.get("error", {})
    case_id = event.get("case_id", "unknown")
    run_id = event.get("run_id", "unknown")
    now_iso = datetime.now(timezone.utc).isoformat()

    error_msg = error_info.get("Cause") or error_info.get("Error") or str(error_info)

    if runs_table and run_id != "unknown":
        runs_table.update_item(
            Key={"run_id": run_id},
            UpdateExpression="SET #st = :st, completed_at = :cat, error_details = :err",
            ExpressionAttributeNames={"#st": "status"},
            ExpressionAttributeValues={
                ":st": "FAILED",
                ":cat": now_iso,
                ":err": error_msg
            }
        )

    return {
        "status": "FAILED",
        "case_id": case_id,
        "run_id": run_id,
        "failed_at": now_iso,
        "error": error_msg
    }
