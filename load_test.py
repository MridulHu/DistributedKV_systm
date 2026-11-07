"""Workload generator for uniform and skewed key access."""
import argparse, random, statistics, time, requests
NODES = ["http://127.0.0.1:5001", "http://127.0.0.1:5002", "http://127.0.0.1:5003"]

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--distribution", choices=["uniform", "skewed"], default="uniform")
    p.add_argument("--requests", type=int, default=300)
    p.add_argument("--keys", type=int, default=150)
    a = p.parse_args()
    random.seed(7)
    requests.post(NODES[0] + "/cluster/reset", timeout=4)
    keys = [f"product-{i:04d}" for i in range(a.keys)]
    # Populate keys through randomly selected entry nodes.
    for i, key in enumerate(keys):
        entry = random.choice(NODES)
        r = requests.put(f"{entry}/kv/{key}",
                         json={"value": {"description": f"item-{i}", "price": i+1}},
                         timeout=4)
        if r.status_code != 200:
            print("Write failed:", key, r.status_code)
    hot = keys[:max(3, a.keys // 20)]
    times, errors = [], 0
    for _ in range(a.requests):
        key = random.choice(hot) if a.distribution == "skewed" and random.random() < .8 else random.choice(keys)
        entry = random.choice(NODES)
        start = time.perf_counter()
        try:
            r = requests.get(f"{entry}/kv/{key}", timeout=4)
            if r.status_code == 200:
                times.append((time.perf_counter()-start)*1000)
            else:
                errors += 1
        except requests.RequestException:
            errors += 1
    print(f"Workload: {a.distribution}; successful reads: {len(times)}; errors: {errors}")
    if times:
        ordered = sorted(times)
        print(f"Mean: {statistics.mean(times):.2f} ms; median: {statistics.median(times):.2f} ms; "
              f"p95: {ordered[min(len(ordered)-1, int(.95*len(ordered)))]:.2f} ms")
    print("Per-node metrics:")
    for row in requests.get(NODES[0] + "/cluster/stats", timeout=5).json()["nodes"]:
        print(row)

if __name__ == "__main__":
    main()
