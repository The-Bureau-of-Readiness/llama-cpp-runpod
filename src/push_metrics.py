import os
import time
import requests

PUSHGATEWAY_URL = os.getenv("PUSHGATEWAY_URL", "").strip()
JOB = os.getenv("PUSHGATEWAY_JOB", "llamacpp-serverless").strip()
INTERVAL = float(os.getenv("PUSH_INTERVAL_SECONDS", "2"))
METRICS_PORT = int(os.getenv("METRICS_PORT", "8080"))

if not PUSHGATEWAY_URL:
    raise SystemExit(0)

metrics_url = f"http://127.0.0.1:{METRICS_PORT}/metrics"
push_url = f"{PUSHGATEWAY_URL.rstrip('/')}/metrics/job/{JOB}"

while True:
    try:
        r = requests.get(metrics_url, timeout=2)
        r.raise_for_status()
        requests.put(push_url, data=r.text.encode("utf-8"), timeout=2)
    except Exception as e:
        print(f"push_metrics: {e}", flush=True)
    time.sleep(INTERVAL)
