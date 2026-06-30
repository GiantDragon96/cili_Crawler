import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

INTERVAL_SECONDS = 300
CRAWLER_DIR = Path(__file__).parent
PYTHON = sys.executable


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def run_crawler():
    log("Starting crawler run")
    result = subprocess.run(
        [PYTHON, str(CRAWLER_DIR / "crawler.py"), "--all-sources", "--submit"],
        cwd=str(CRAWLER_DIR),
        stdin=subprocess.DEVNULL,
    )
    log(f"Crawler exited with code {result.returncode}")


if __name__ == "__main__":
    log("Scheduler started. Running once immediately, then every 5 mins.")
    run_crawler()
    while True:
        log(f"Sleeping {INTERVAL_SECONDS}s until next run")
        time.sleep(INTERVAL_SECONDS)
        run_crawler()
