import os
import json
import uuid
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import boto3
from botocore.exceptions import ClientError

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
sfn = boto3.client("stepfunctions")

DATA_BUCKET = os.environ.get("DATA_BUCKET")
CASES_TABLE_NAME = os.environ.get("CASES_TABLE")
RUNS_TABLE_NAME = os.environ.get("RUNS_TABLE")
STATE_MACHINE_ARN = os.environ.get("STATE_MACHINE_ARN")

try:
    from shortlist_builder import build_enriched_shortlist
except ImportError:
    from data.shortlist_builder import build_enriched_shortlist

cases_table = dynamodb.Table(CASES_TABLE_NAME) if CASES_TABLE_NAME else None
runs_table = dynamodb.Table(RUNS_TABLE_NAME) if RUNS_TABLE_NAME else None

KNOWN_CASE_IDS = {
    "case_anand_vihar_20251102",
    "case_anand_vihar_20260131",
    "case_anand_vihar_20260405",
    "case_crri_20260515",
    "case_gurugram_20260630",
    "case_regional_smog_20251020",
    "case_rkpuram_20251112"
}

def sanitize_payload(obj: Any) -> Any:
    """Recursively removes ARNs, account IDs, and internal AWS metadata from public responses."""
    if isinstance(obj, dict):
        clean = {}
        for k, v in obj.items():
            if k in ["execution_arn", "stateMachineArn", "RoleArn"]:
                continue
            clean[k] = sanitize_payload(v)
        return clean
    elif isinstance(obj, list):
        return [sanitize_payload(v) for v in obj]
    elif isinstance(obj, str):
        # Scrub full ARNs containing account numbers
        return re.sub(r'arn:aws:[a-zA-Z0-9\-:]+:[0-9]{12}:[a-zA-Z0-9\-/_]+', '[REDACTED_INTERNAL_RESOURCE]', obj)
    return obj

def response(status_code: int, body: Any, content_type: str = "application/json") -> dict:
    headers = {
        "Content-Type": content_type,
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "*"
    }
    safe_body = sanitize_payload(body) if content_type == "application/json" else body
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(safe_body, default=str) if content_type == "application/json" else safe_body
    }

def handler(event, context):
    try:
        method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
        path = event.get("requestContext", {}).get("http", {}).get("path", "/")
        path_params = event.get("pathParameters") or {}

        # CORS preflight
        if method == "OPTIONS":
            return response(200, {"ok": True})

        # GET /health
        if path == "/health" and method == "GET":
            return response(200, {
                "status": "healthy",
                "service": "smokeprint-backend",
                "region": os.environ.get("AWS_REGION", "us-east-1"),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

        # GET /cases
        if path == "/cases" and method == "GET":
            if cases_table:
                res = cases_table.scan()
                items = res.get("Items", [])
                items.sort(key=lambda x: x.get("case_id", ""))
                return response(200, {"count": len(items), "cases": items})
            return response(500, {"error": "Cases table not configured"})

        # GET /cases/{id}/shortlist
        if path.startswith("/cases/") and path.endswith("/shortlist") and method == "GET":
            case_id = path_params.get("id") or path.split("/")[-2]
            headers_in = event.get("headers") or {}
            accept = headers_in.get("accept", headers_in.get("Accept", "")).lower()

            if "application/json" in accept:
                # Return structured JSON shortlist enriched with coords, wind, operating status
                cdata = None
                try:
                    s3_case_key = f"cases/{case_id}.json"
                    obj = s3.get_object(Bucket=DATA_BUCKET, Key=s3_case_key)
                    cdata = json.loads(obj["Body"].read().decode("utf-8"))
                except Exception:
                    if cases_table:
                        res = cases_table.get_item(Key={"case_id": case_id})
                        cdata = res.get("Item")

                if not cdata:
                    return response(404, {"error": f"Shortlist JSON for {case_id} not found"})

                enriched = build_enriched_shortlist(cdata)
                return response(200, enriched)

            s3_key = f"shortlists/{case_id}_shortlist.md"
            try:
                obj = s3.get_object(Bucket=DATA_BUCKET, Key=s3_key)
                content = obj["Body"].read().decode("utf-8")
                return response(200, content, content_type="text/markdown; charset=utf-8")
            except ClientError as e:
                return response(404, {"error": f"Shortlist for {case_id} not found", "s3_key": s3_key, "detail": str(e)})

        # GET /cases/{id}/trace
        if path.startswith("/cases/") and path.endswith("/trace") and method == "GET":
            case_id = path_params.get("id") or path.split("/")[-2]
            s3_key = f"agent_traces/{case_id}.json"
            try:
                obj = s3.get_object(Bucket=DATA_BUCKET, Key=s3_key)
                trace_data = json.loads(obj["Body"].read().decode("utf-8"))
                return response(200, trace_data)
            except ClientError as e:
                return response(404, {"error": f"Trace for {case_id} not found", "s3_key": s3_key, "detail": str(e)})

        # POST /cases/{id}/recompute
        if path.startswith("/cases/") and path.endswith("/recompute") and method == "POST":
            case_id = path_params.get("id") or path.split("/")[-2]
            
            # Input validation: Restrict strictly to the 7 vetted case IDs
            if case_id not in KNOWN_CASE_IDS:
                return response(400, {
                    "error": f"Invalid case_id '{case_id}'. POST /cases/{{id}}/recompute is restricted to vetted demo cases.",
                    "allowed_cases": sorted(list(KNOWN_CASE_IDS))
                })

            run_id = f"run_{uuid.uuid4().hex[:12]}"
            execution_name = f"recompute_{case_id}_{run_id}"
            input_payload = {
                "case_id": case_id,
                "run_id": run_id,
                "triggered_at": datetime.now(timezone.utc).isoformat()
            }
            sfn_res = sfn.start_execution(
                stateMachineArn=STATE_MACHINE_ARN,
                name=execution_name,
                input=json.dumps(input_payload)
            )
            exec_arn = sfn_res.get("executionArn")
            
            # Record initial run in DynamoDB
            if runs_table:
                runs_table.put_item(Item={
                    "run_id": run_id,
                    "case_id": case_id,
                    "execution_arn": exec_arn,
                    "execution_name": execution_name,
                    "status": "RUNNING",
                    "source": "replayed",
                    "mode": "replayed_from_canonical_output",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "completed_at": None,
                    "output": None
                })

            return response(202, {
                "message": "Replay execution started",
                "run_id": run_id,
                "case_id": case_id,
                "execution_id": execution_name,
                "status": "RUNNING",
                "source": "replayed",
                "mode": "replayed_from_canonical_output",
                "replayed_note": "replayed from validated core output"
            })

        # GET /cases/{id}
        if path.startswith("/cases/") and not (path.endswith("/shortlist") or path.endswith("/trace") or path.endswith("/recompute")) and method == "GET":
            case_id = path_params.get("id") or path.split("/")[-1]
            cdata = None
            s3_key = f"cases/{case_id}.json"
            try:
                obj = s3.get_object(Bucket=DATA_BUCKET, Key=s3_key)
                cdata = json.loads(obj["Body"].read().decode("utf-8"))
            except Exception:
                pass

            db_item = {}
            if cases_table:
                try:
                    res = cases_table.get_item(Key={"case_id": case_id})
                    db_item = res.get("Item") or {}
                except Exception:
                    pass

            if not cdata and not db_item:
                return response(404, {"error": f"Case '{case_id}' not found"})

            if not cdata:
                cdata = db_item
            else:
                for k, v in db_item.items():
                    if k not in cdata:
                        cdata[k] = v

            # Enrich case data with geolocation and wind
            enriched_shortlist_info = build_enriched_shortlist(cdata)
            cdata["shortlist"] = enriched_shortlist_info["shortlist"]
            cdata["other_explanations_considered"] = enriched_shortlist_info.get("other_explanations_considered", [])
            cdata["station_coordinates"] = enriched_shortlist_info.get("station_coordinates", cdata.get("coordinates", {"latitude": 28.6468, "longitude": 77.3160}))
            cdata["wind"] = enriched_shortlist_info["wind"]
            cdata["group"] = enriched_shortlist_info.get("group")
            cdata["dispatch_refused"] = enriched_shortlist_info.get("dispatch_refused", False)
            if enriched_shortlist_info.get("refusal_reason"):
                cdata["refusal_reason"] = enriched_shortlist_info.get("refusal_reason")

            if "source" not in cdata:
                cdata["source"] = "precomputed"
            if "source_description" not in cdata:
                cdata["source_description"] = "precomputed_local_agent"

            sig = cdata.get("signature", {})
            cdata["evidence"] = {
                "station_pm25": str(sig.get("pm25", cdata.get("evidence", {}).get("station_pm25", ""))),
                "station_pm10": str(sig.get("pm10", cdata.get("evidence", {}).get("station_pm10", ""))),
                "ratio_pm25_pm10": str(round(float(sig.get("pm25", 1)) / float(sig.get("pm10", 1)), 3)) if sig.get("pm10") else cdata.get("evidence", {}).get("ratio_pm25_pm10", "N/A"),
                "no2_ugm3": str(sig.get("no2_ugm3", cdata.get("evidence", {}).get("no2_ugm3", ""))),
                "regional_median_pm25": str(cdata.get("regional_median", cdata.get("evidence", {}).get("regional_median_pm25", ""))),
                "local_excess_pm25": str(cdata.get("local_excess", cdata.get("evidence", {}).get("local_excess_pm25", "")))
            }

            return response(200, cdata)

        # GET /runs/{id}
        if path.startswith("/runs/") and method == "GET":
            run_id = path_params.get("id") or path.split("/")[-1]
            if runs_table:
                res = runs_table.get_item(Key={"run_id": run_id})
                item = res.get("Item")
                if item:
                    # If running, check SFN live status
                    if item.get("status") == "RUNNING" and item.get("execution_arn"):
                        try:
                            sfn_desc = sfn.describe_execution(executionArn=item["execution_arn"])
                            if sfn_desc.get("status") in ["SUCCEEDED", "FAILED", "TIMED_OUT"]:
                                item["status"] = sfn_desc.get("status")
                                if sfn_desc.get("output"):
                                    item["output"] = json.loads(sfn_desc["output"])
                        except Exception:
                            pass
                    return response(200, item)
            return response(404, {"error": f"Run '{run_id}' not found"})

        # GET /backtest
        if path == "/backtest" and method == "GET":
            s3_key = "backtest/backtest_results.json"
            try:
                obj = s3.get_object(Bucket=DATA_BUCKET, Key=s3_key)
                bt_data = json.loads(obj["Body"].read().decode("utf-8"))
                return response(200, bt_data)
            except ClientError as e:
                try:
                    obj = s3.get_object(Bucket=DATA_BUCKET, Key="backtest/mismatch_phase27_results.json")
                    bt_data = json.loads(obj["Body"].read().decode("utf-8"))
                    return response(200, bt_data)
                except ClientError:
                    return response(404, {"error": "Backtest results not found in S3", "detail": str(e)})

        return response(404, {"error": f"Route not found: {method} {path}"})

    except Exception as e:
        return response(500, {"error": "Internal server error", "detail": str(e)})
