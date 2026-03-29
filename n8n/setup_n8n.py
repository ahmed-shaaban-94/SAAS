"""One-time n8n setup: wire notification sub-workflows into the pipeline."""
import json
import urllib.request

API = "http://localhost:5678/api/v1"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhODFmMGFlZi02MWJkLTRjZjgtYWE2Mi00NTU4NDAyNWM5NTYiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiYzA4ODIyMDItYWU1Zi00ZDNlLWI4ZDgtODdkMWM0ZWIzNTEwIiwiaWF0IjoxNzc0ODE4MDU4fQ.iD68Gl8vcUJ2jQiXoE4KQEHE7sEDosLTYYnAH-k0uns"
PIPELINE_ID = "gEqqvIszCIsUHMGS"
SUCCESS_WF_ID = "nnjSBIPhm0l13UNw"
FAILURE_WF_ID = "0Z495yoAp137RGnb"
ERROR_HANDLER_ID = "Lc3OGrdoq0s4Xm4K"


def api_request(path, method="GET", data=None):
    url = f"{API}{path}"
    req = urllib.request.Request(url, method=method)
    req.add_header("X-N8N-API-KEY", KEY)
    req.add_header("Content-Type", "application/json")
    if data:
        req.data = json.dumps(data).encode()
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


# Step 1: Get current pipeline workflow
wf = api_request(f"/workflows/{PIPELINE_ID}")
print(f"[OK] Fetched pipeline workflow: {wf['name']}")

# Step 2: Add sub-workflow nodes for notifications
new_nodes = [
    {
        "parameters": {"workflowId": {"value": SUCCESS_WF_ID}, "options": {}},
        "id": "notify-success",
        "name": "Notify Success",
        "type": "n8n-nodes-base.executeWorkflow",
        "typeVersion": 1.2,
        "position": [2760, 300],
    },
    {
        "parameters": {"workflowId": {"value": FAILURE_WF_ID}, "options": {}},
        "id": "notify-fail-bronze",
        "name": "Notify Fail Bronze",
        "type": "n8n-nodes-base.executeWorkflow",
        "typeVersion": 1.2,
        "position": [1440, 700],
    },
    {
        "parameters": {"workflowId": {"value": FAILURE_WF_ID}, "options": {}},
        "id": "notify-fail-silver",
        "name": "Notify Fail Silver",
        "type": "n8n-nodes-base.executeWorkflow",
        "typeVersion": 1.2,
        "position": [2040, 700],
    },
    {
        "parameters": {"workflowId": {"value": FAILURE_WF_ID}, "options": {}},
        "id": "notify-fail-gold",
        "name": "Notify Fail Gold",
        "type": "n8n-nodes-base.executeWorkflow",
        "typeVersion": 1.2,
        "position": [2640, 700],
    },
    {
        "parameters": {"workflowId": {"value": FAILURE_WF_ID}, "options": {}},
        "id": "notify-fail-general",
        "name": "Notify Fail General",
        "type": "n8n-nodes-base.executeWorkflow",
        "typeVersion": 1.2,
        "position": [1680, 700],
    },
]

wf["nodes"].extend(new_nodes)

# Step 3: Add connections for notifications
conns = wf["connections"]
conns["Set Status Success"] = {
    "main": [[{"node": "Notify Success", "type": "main", "index": 0}]]
}
conns["Failed Bronze Quality"] = {
    "main": [[{"node": "Notify Fail Bronze", "type": "main", "index": 0}]]
}
conns["Failed Silver Quality"] = {
    "main": [[{"node": "Notify Fail Silver", "type": "main", "index": 0}]]
}
conns["Failed Gold Quality"] = {
    "main": [[{"node": "Notify Fail Gold", "type": "main", "index": 0}]]
}
conns["Set Status Failed"] = {
    "main": [[{"node": "Notify Fail General", "type": "main", "index": 0}]]
}

# Step 4: Set error workflow on pipeline settings
settings = wf.get("settings", {})
settings["errorWorkflow"] = ERROR_HANDLER_ID

# Step 5: PUT updated workflow
update_payload = {
    "name": wf["name"],
    "nodes": wf["nodes"],
    "connections": wf["connections"],
    "settings": settings,
}

try:
    api_request(f"/workflows/{PIPELINE_ID}", method="PUT", data=update_payload)
    print("[OK] Pipeline updated with 5 notification nodes + error handler")
except Exception as e:
    err = e.read().decode() if hasattr(e, "read") else str(e)
    print(f"[FAIL] Update: {err}")

# Step 6: Re-activate
try:
    result = api_request(f"/workflows/{PIPELINE_ID}/activate", method="POST")
    tag = "ACTIVE" if result.get("active") else "FAIL"
    print(f"[{tag}] Pipeline re-activated")
except Exception as e:
    err = e.read().decode() if hasattr(e, "read") else str(e)
    print(f"[FAIL] Activate: {err}")

# Step 7: Verify all workflows are active
all_wf = api_request("/workflows")
print("\n=== ALL WORKFLOWS ===")
for w in all_wf.get("data", []):
    status = "ACTIVE" if w.get("active") else "INACTIVE"
    print(f"  [{status}] {w['name']} (id={w['id']})")

print("\n=== REMAINING MANUAL STEP ===")
print("Set global error handler in n8n UI:")
print("  Settings (gear) > Error Workflow > select '2.6.4 global error handler'")
