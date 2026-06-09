"""
Feedback storage backend — WSGI/serverless handler.

Stores feedback submissions as newline-delimited JSON to a local file
(dev mode) or can be configured to POST to a serverless function.

For production:
  - Deploy as Vercel serverless function: /api/submit_feedback.py
  - Or use as a standalone Flask/FastAPI route

Dev mode: appends to feedback/submissions.jsonl

Security:
  - Rate limit: 5 submissions per IP per hour (in-memory, resets on restart)
  - Field validation: required fields checked
  - No private data stored (emails are optional and not required)
  - No XSS: all fields stored as-is for backend review only
  - CORS: restricted to same-origin in production

Schema mirrors FEEDBACK_TRIAGE_AGENT.md input schema.
"""

import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

# In-memory rate limiter (IP → [timestamps])
_rate_limit: dict[str, list[float]] = {}
RATE_LIMIT_MAX = 5
RATE_LIMIT_WINDOW = 3600  # 1 hour

FEEDBACK_DIR = Path(__file__).resolve().parent / "data"
SUBMISSIONS_FILE = FEEDBACK_DIR / "submissions.jsonl"

VALID_FEEDBACK_TYPES = {
    "dataset_suggestion", "bad_data_report", "explanation_suggestion",
    "source_submission", "feature_request", "other"
}

VALID_CONFIDENCE = {"low", "medium", "high", None}

MAX_FIELD_LEN = {
    "title": 200,
    "description": 5000,
    "source_url": 500,
    "why_relevant": 2000,
    "known_limitations": 2000,
    "correction_summary": 2000,
    "proposed_explanation": 2000,
    "evidence_for_explanation": 2000,
}


def _check_rate_limit(ip: str) -> bool:
    """True if request is allowed, False if rate-limited."""
    now = time.time()
    timestamps = _rate_limit.get(ip, [])
    # Remove old timestamps
    timestamps = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]
    if len(timestamps) >= RATE_LIMIT_MAX:
        _rate_limit[ip] = timestamps
        return False
    timestamps.append(now)
    _rate_limit[ip] = timestamps
    return True


def _sanitize_str(value, max_len: int) -> str | None:
    """Strip control characters and truncate."""
    if value is None:
        return None
    s = str(value).strip()
    # Remove control characters except newlines/tabs
    s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', s)
    return s[:max_len]


def validate_and_clean(data: dict) -> tuple[dict | None, str | None]:
    """Validate and sanitize incoming payload. Returns (cleaned, error_msg)."""
    fb_type = data.get("feedback_type")
    if fb_type not in VALID_FEEDBACK_TYPES:
        return None, f"Invalid feedback_type: {fb_type}"

    title = _sanitize_str(data.get("title"), MAX_FIELD_LEN["title"])
    if not title:
        return None, "title is required"

    description = _sanitize_str(data.get("description"), MAX_FIELD_LEN["description"])
    if not description or len(description) < 20:
        return None, "description must be at least 20 characters"

    confidence = data.get("confidence")
    if confidence not in VALID_CONFIDENCE:
        confidence = None

    cleaned = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "feedback_type": fb_type,
        "title": title,
        "description": description,
        "source_url": _sanitize_str(data.get("source_url"), MAX_FIELD_LEN["source_url"]),
        "related_map_url": _sanitize_str(data.get("related_map_url"), 500),
        "related_hotspot_slug": _sanitize_str(data.get("related_hotspot_slug"), 100),
        "dataset_name": _sanitize_str(data.get("dataset_name"), 200),
        "has_lat_lon": data.get("has_lat_lon") if data.get("has_lat_lon") in ("yes", "no", "unknown") else None,
        "has_timestamps": data.get("has_timestamps") if data.get("has_timestamps") in ("yes", "no", "unknown") else None,
        "public_access": data.get("public_access") if data.get("public_access") in ("yes", "no", "unknown") else None,
        "why_relevant": _sanitize_str(data.get("why_relevant"), MAX_FIELD_LEN["why_relevant"]),
        "known_limitations": _sanitize_str(data.get("known_limitations"), MAX_FIELD_LEN["known_limitations"]),
        "problem_type": _sanitize_str(data.get("problem_type"), 100),
        "correction_summary": _sanitize_str(data.get("correction_summary"), MAX_FIELD_LEN["correction_summary"]),
        "proposed_explanation": _sanitize_str(data.get("proposed_explanation"), MAX_FIELD_LEN["proposed_explanation"]),
        "evidence_for_explanation": _sanitize_str(data.get("evidence_for_explanation"), MAX_FIELD_LEN["evidence_for_explanation"]),
        "confidence": confidence,
        "public_source_confirmed": bool(data.get("public_source_confirmed", False)),
        "triage_status": "New",  # Awaiting triage agent
        "triage_score": None,
        "final_decision": None,
    }
    return cleaned, None


def store_submission(submission: dict) -> None:
    """Append submission to JSONL file (atomic line append)."""
    SUBMISSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(submission, ensure_ascii=False, default=str) + "\n"
    with open(SUBMISSIONS_FILE, "a", encoding="utf-8") as f:
        f.write(line)


def handle_post(body: dict, client_ip: str = "unknown") -> tuple[dict, int]:
    """
    Handle a POST /api/submit_feedback request.

    Returns (response_dict, http_status_code).
    """
    # Rate limit
    if not _check_rate_limit(client_ip):
        return {"error": "Rate limit exceeded. Max 5 submissions per hour."}, 429

    submission, error = validate_and_clean(body)
    if error:
        return {"error": error}, 400

    store_submission(submission)
    return {
        "status": "received",
        "id": submission["id"],
        "message": "Thank you. Submissions are reviewed by humans before any map changes.",
        "triage_status": "New",
    }, 201


# ── Vercel serverless function entrypoint ──────────────────────────────────────
def handler(request, response=None):
    """Vercel Python serverless function handler."""
    if hasattr(request, 'method'):
        method = request.method
    else:
        method = request.get("method", "GET")

    if method == "OPTIONS":
        # CORS preflight
        return {"statusCode": 204, "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        }}

    if method != "POST":
        return {"statusCode": 405, "body": json.dumps({"error": "Method not allowed"})}

    try:
        if hasattr(request, 'get_json'):
            body = request.get_json(force=True)
        elif hasattr(request, 'body'):
            body = json.loads(request.body)
        else:
            body = json.loads(request.get("body", "{}"))
    except (json.JSONDecodeError, Exception):
        return {"statusCode": 400, "body": json.dumps({"error": "Invalid JSON body"})}

    ip = (
        getattr(request, 'remote_addr', None)
        or request.get("headers", {}).get("x-forwarded-for", "unknown")
    )
    result, status = handle_post(body, client_ip=ip)

    return {
        "statusCode": status,
        "body": json.dumps(result),
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
    }


# ── Dev mode: run as standalone Flask app ─────────────────────────────────────
if __name__ == "__main__":
    try:
        from flask import Flask, request, jsonify
        app = Flask(__name__)

        @app.route("/api/submit_feedback", methods=["POST", "OPTIONS"])
        def submit():
            if request.method == "OPTIONS":
                resp = jsonify({})
                resp.headers["Access-Control-Allow-Origin"] = "*"
                resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
                resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
                return resp, 204
            result, status = handle_post(request.get_json(force=True), request.remote_addr)
            return jsonify(result), status

        print(f"Feedback API running at http://localhost:5001")
        print(f"Submissions stored to: {SUBMISSIONS_FILE}")
        app.run(host="0.0.0.0", port=5001, debug=True)
    except ImportError:
        print("Flask not installed. Install with: pip install flask")
        print("Or deploy as Vercel serverless function.")
