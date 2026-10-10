import os
import json
from decimal import Decimal
from datetime import datetime, timezone
import boto3

dynamodb = boto3.resource("dynamodb")

RUNS_TABLE_NAME = os.environ.get("RUNS_TABLE")
runs_table = dynamodb.Table(RUNS_TABLE_NAME) if RUNS_TABLE_NAME else None

def handler(event, context):
    case_id = event.get("case_id")
    run_id = event.get("run_id")
    triggered_at = event.get("triggered_at")
    core_triage = event.get("core_triage") or event
    agent_review = event.get("agent_review", {})

    now_iso = datetime.now(timezone.utc).isoformat()

    run_output = {
        "case_id": case_id,
        "run_id": run_id,
        "source": "replayed",
        "mode": "replayed_from_canonical_output",
        "replayed_note": "replayed from validated core output",
        "classification": core_triage.get("classification"),
        "group": core_triage.get("group"),
        "dispatch_refused": core_triage.get("dispatch_refused"),
        "refusal_reason": core_triage.get("refusal_reason"),
        "shortlist": core_triage.get("shortlist", []),
        "shortlist_count": len(core_triage.get("shortlist", [])),
        "wind": core_triage.get("wind", {}),
        "station_coordinates": core_triage.get("station_coordinates", {}),
        "telemetry": core_triage.get("telemetry", {}),
        "agent_review": agent_review,
        "agent_review_verdict": agent_review.get("review_verdict"),
        "replayed_at": now_iso
    }

    # Write recompute results strictly to the runs table (does not overwrite canonical case table)
    if runs_table and run_id:
        dynamo_safe_output = json.loads(json.dumps(run_output), parse_float=Decimal)
        runs_table.update_item(
            Key={"run_id": run_id},
            UpdateExpression="SET #st = :st, completed_at = :cat, #out = :out",
            ExpressionAttributeNames={"#st": "status", "#out": "output"},
            ExpressionAttributeValues={
                ":st": "SUCCEEDED",
                ":cat": now_iso,
                ":out": dynamo_safe_output
            }
        )

    return {
        "status": "SUCCEEDED",
        "case_id": case_id,
        "run_id": run_id,
        "source": "replayed",
        "mode": "replayed_from_canonical_output",
        "replayed_note": "replayed from validated core output",
        "replayed_at": now_iso,
        "output": run_output
    }
