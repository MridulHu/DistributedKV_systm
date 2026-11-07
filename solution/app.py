"""
Three-node key-value store starter.
Initially all keys are assigned to node 1. Students modify owner_index().
"""
import os
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)
NODE_ID = os.getenv("NODE_ID", "node-1")
PORT = int(os.getenv("PORT", "5001"))
SELF_URL = os.getenv("SELF_URL", f"http://127.0.0.1:{PORT}").rstrip("/")
NODES = [x.strip().rstrip("/") for x in os.getenv(
    "NODES", "http://127.0.0.1:5001,http://127.0.0.1:5002,http://127.0.0.1:5003"
).split(",") if x.strip()]
STORE = {}
METRICS = {"reads": 0, "writes": 0, "forwarded": 0}
TIMEOUT = 2.0

def owner_index(key):
    # Stable deterministic mapping: every process computes the same owner.
    import hashlib
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return int(digest, 16) % len(NODES)

def get_owner_url(key):
    return NODES[owner_index(key)]

def local_put(key, value):
    STORE[key] = value
    METRICS["writes"] += 1

def local_get(key):
    METRICS["reads"] += 1
    return STORE.get(key), key in STORE

@app.get("/health")
def health():
    return jsonify({"status": "ok", "node": NODE_ID})

@app.put("/kv/<key>")
def put_key(key):
    body = request.get_json(silent=True) or {}
    if "value" not in body:
        return jsonify({"error": "JSON body must contain 'value'"}), 400
    owner = get_owner_url(key)
    if owner == SELF_URL:
        local_put(key, body["value"])
        return jsonify({"stored": True, "key": key, "owner": NODE_ID})
    METRICS["forwarded"] += 1
    try:
        r = requests.put(f"{owner}/internal/kv/{key}", json={"value": body["value"]}, timeout=TIMEOUT)
        return (r.content, r.status_code, r.headers.items())
    except requests.RequestException:
        return jsonify({"error": "key owner unavailable", "owner_url": owner}), 503

@app.get("/kv/<key>")
def get_key(key):
    owner = get_owner_url(key)
    if owner == SELF_URL:
        value, found = local_get(key)
        if not found:
            return jsonify({"error": "key not found", "key": key, "owner": NODE_ID}), 404
        return jsonify({"key": key, "value": value, "owner": NODE_ID})
    METRICS["forwarded"] += 1
    try:
        r = requests.get(f"{owner}/internal/kv/{key}", timeout=TIMEOUT)
        return (r.content, r.status_code, r.headers.items())
    except requests.RequestException:
        return jsonify({"error": "key owner unavailable", "owner_url": owner}), 503

@app.put("/internal/kv/<key>")
def internal_put(key):
    body = request.get_json(silent=True) or {}
    if "value" not in body:
        return jsonify({"error": "value required"}), 400
    local_put(key, body["value"])
    return jsonify({"stored": True, "key": key, "node": NODE_ID})

@app.get("/internal/kv/<key>")
def internal_get(key):
    value, found = local_get(key)
    if not found:
        return jsonify({"error": "key not found", "key": key, "owner": NODE_ID}), 404
    return jsonify({"key": key, "value": value, "owner": NODE_ID})

@app.get("/internal/stats")
def internal_stats():
    return jsonify({"node": NODE_ID, "key_count": len(STORE),
                    "reads": METRICS["reads"], "writes": METRICS["writes"],
                    "forwarded": METRICS["forwarded"]})

@app.get("/cluster/stats")
def cluster_stats():
    rows = []
    for url in NODES:
        try:
            rows.append(requests.get(url + "/internal/stats", timeout=TIMEOUT).json())
        except requests.RequestException:
            rows.append({"node_url": url, "status": "unavailable"})
    return jsonify({"nodes": rows})

@app.post("/internal/reset")
def internal_reset():
    STORE.clear()
    for k in METRICS:
        METRICS[k] = 0
    return jsonify({"reset": True, "node": NODE_ID})

@app.post("/cluster/reset")
def cluster_reset():
    rows = []
    for url in NODES:
        try:
            rows.append(requests.post(url + "/internal/reset", timeout=TIMEOUT).json())
        except requests.RequestException:
            rows.append({"node_url": url, "status": "unavailable"})
    return jsonify({"results": rows})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=PORT, threaded=True, debug=False)
