# 2-hour lab: Distributed Key-Value Store — Partitioning and Performance

## Purpose
Run three independent Flask nodes. Each has its own in-memory dictionary. Requests may enter through any node; that node routes the key to its designated owner.

Initially, `owner_index()` returns 0, so every key is stored on node 1. Students modify this function to distribute keys using deterministic hashing. The lab focuses on partitioning, routing, data skew, and performance—not replication or consensus.

## Requirements
Python 3.10+, pip, and three terminals.

## Install
macOS/Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```
Windows PowerShell:
```powershell
py -m venv .venv
.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Start three nodes
Run each in a separate terminal from this folder; activate the virtual environment in each.

macOS/Linux:
```bash
NODE_ID=node-1 PORT=5001 SELF_URL=http://127.0.0.1:5001 python app.py
NODE_ID=node-2 PORT=5002 SELF_URL=http://127.0.0.1:5002 python app.py
NODE_ID=node-3 PORT=5003 SELF_URL=http://127.0.0.1:5003 python app.py
```
Windows PowerShell (one command per terminal):
```powershell
$env:NODE_ID="node-1"; $env:PORT="5001"; $env:SELF_URL="http://127.0.0.1:5001"; python app.py
$env:NODE_ID="node-2"; $env:PORT="5002"; $env:SELF_URL="http://127.0.0.1:5002"; python app.py
$env:NODE_ID="node-3"; $env:PORT="5003"; $env:SELF_URL="http://127.0.0.1:5003"; python app.py
```
The default node list is ports 5001, 5002, and 5003 in that order on every process.

## Part 1 — Baseline (15 min)
Leave `owner_index()` as `return 0`. In a fourth terminal run:
```bash
python load_test.py --distribution uniform --requests 300
```
Inspect per-node metrics. All keys and owner-side operations should be on node 1, even though client requests enter through randomly selected nodes.

## Part 2 — Implement hash partitioning (25 min)
Edit `owner_index(key)` in `app.py`:
1. Compute SHA-256 of the key.
2. Convert the hexadecimal digest to an integer.
3. Return that integer modulo `len(NODES)`.

The hint is in the starter function. Do not use Python's built-in `hash()`: its result can vary across processes/runs. Restart all three processes after editing, then run:
```bash
python load_test.py --distribution uniform --requests 300
```
Compare key counts and operation counts with the baseline.

## Part 3 — Investigate skew (20 min)
Run:
```bash
python load_test.py --distribution skewed --requests 300
```
The skewed workload sends 80% of reads to a small hot set of keys. Inspect the counters. Discuss whether hashing guarantees equal request load, and why a few popular keys can overload their owner even when the number of keys is balanced.

## Part 4 — Analyse results (20 min)
Record:
- Key count per node in baseline and hash-partitioned runs.
- Reads and writes per node.
- Mean, median, and 95th percentile read latency.
- Why uniform and skewed access patterns differ.

## Suggested schedule (120 min)
| Activity | Time |
|---|---:|
| Install, start nodes, inspect API | 15 min |
| Baseline run and observations | 15 min |
| Implement hash partitioning | 25 min |
| Skewed workload experiment | 20 min |
| Compare metrics and discuss | 20 min |
| Written answers / buffer | 25 min |

## API
- `PUT /kv/<key>` with JSON `{"value": ...}` — write.
- `GET /kv/<key>` — read.
- `GET /cluster/stats` — inspect per-node key and operation counts.
- `POST /cluster/reset` — clear all in-memory stores and counters.

Example:
```bash
curl -X PUT http://127.0.0.1:5001/kv/student42 -H "Content-Type: application/json" -d '{"value":"Distributed Systems"}'
curl http://127.0.0.1:5002/kv/student42
curl http://127.0.0.1:5001/cluster/stats
```

## Limitations and extension
Data is in memory and is lost when a node stops. There is no replication, consensus, persistence, authentication, or recovery. This lab uses simple modulo hashing, not consistent hashing; changing the number/order of nodes can remap many keys. The load generator runs on one computer, so timings illustrate measurement methods rather than production performance.

Optional extension: implement consistent hashing and compare the number of keys remapped when a fourth node is added.
