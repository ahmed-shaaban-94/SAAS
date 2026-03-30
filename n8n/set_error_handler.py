"""Set errorWorkflow on all n8n workflows to point to global error handler.

Usage:
    N8N_API_KEY=<your-key> python n8n/set_error_handler.py
"""
import json
import os
import urllib.request

API = os.environ.get("N8N_API_URL", "http://localhost:5678/api/v1")
KEY = os.environ["N8N_API_KEY"]
ERROR_HANDLER_ID = os.environ.get("N8N_ERROR_HANDLER_ID", "Lc3OGrdoq0s4Xm4K")


def api_req(path, method="GET", data=None):
    req = urllib.request.Request(f"{API}{path}", method=method)
    req.add_header("X-N8N-API-KEY", KEY)
    req.add_header("Content-Type", "application/json")
    if data:
        req.data = json.dumps(data).encode()
    return json.loads(urllib.request.urlopen(req).read())


all_wf = api_req("/workflows")
for w in all_wf.get("data", []):
    wf_id = w["id"]
    wf_name = w["name"]

    if wf_id == ERROR_HANDLER_ID:
        continue

    wf = api_req(f"/workflows/{wf_id}")
    settings = wf.get("settings", {})

    if settings.get("errorWorkflow") == ERROR_HANDLER_ID:
        print(f"[SKIP] {wf_name} - already set")
        continue

    settings["errorWorkflow"] = ERROR_HANDLER_ID
    payload = {
        "name": wf["name"],
        "nodes": wf["nodes"],
        "connections": wf["connections"],
        "settings": settings,
    }
    try:
        api_req(f"/workflows/{wf_id}", method="PUT", data=payload)
        api_req(f"/workflows/{wf_id}/activate", method="POST")
        print(f"[OK] {wf_name} - error handler set + re-activated")
    except Exception as e:
        err = e.read().decode() if hasattr(e, "read") else str(e)
        print(f"[FAIL] {wf_name}: {err}")

print("\nDone! All workflows now use the global error handler.")
