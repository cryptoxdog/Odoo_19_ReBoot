import json
import time
import urllib.request
from urllib.error import URLError, HTTPError

def post_json(url, payload, api_key=None, timeout_sec=30, trace=None, span_id=None):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")

    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read().decode("utf-8")
            latency = time.time() - start
            if trace and span_id:
                trace.event(span_id, "http_ok", {
                    "latency_sec": latency,
                    "status": getattr(resp, "status", None),
                    "request_bytes": len(body),
                    "response_bytes": len(raw),
                })
            return json.loads(raw) if raw else {}
    except HTTPError as e:
        latency = time.time() - start
        if trace and span_id:
            trace.event(span_id, "http_error", {
                "latency_sec": latency,
                "status": getattr(e, "code", None),
                "error": str(e),
            })
        raise
    except URLError as e:
        latency = time.time() - start
        if trace and span_id:
            trace.event(span_id, "http_error", {
                "latency_sec": latency,
                "status": None,
                "error": str(e),
            })
        raise

