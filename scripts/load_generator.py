import time
import threading
import requests
import subprocess
import json
import sys
import os


# Configuration
TERRAFORM_DIR = os.path.join(os.path.dirname(__file__), "../terraform")


def get_alb_url():
    """Retrieve the Load Balancer URL from Terraform outputs."""
    try:
        cmd = ["terraform", "output", "-json"]
        result = subprocess.run(
            cmd, cwd=TERRAFORM_DIR, capture_output=True, text=True, check=True
        )
        outputs = json.loads(result.stdout)
        dns_name = outputs.get("alb_dns_name", {}).get("value")
        if not dns_name:
            print("❌ Error: Terraform output 'alb_dns_name' not found.")
            sys.exit(1)
        return f"http://{dns_name}"
    except Exception as e:
        print(f"❌ Terraform error: {e}")
        sys.exit(1)


def send_traffic(url, thread_id):
    """Continuously send HTTP requests to the target URL."""
    count = 0
    session = requests.Session()  # Connection reuse optimization
    print(f"🚀 [Thread-{thread_id}] Starting traffic load...")

    while True:
        try:
            resp = session.get(url)
            count += 1

            # Log every 50 calls to avoid spamming the terminal
            if count % 50 == 0:
                print(
                    f"   [Thread-{thread_id}] {count} requests sent (Status: {resp.status_code})"
                )

        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(1)


if __name__ == "__main__":
    print("============================================================")
    print("      LOAD GENERATOR 'WINTER SALES' (STRESS TEST)           ")
    print("============================================================")

    target_url = get_alb_url()
    print(f"🎯 Target locked: {target_url}")
    print("⚠️  WARNING: This script will generate real traffic.")
    print("    Press CTRL+C to stop.")
    print("============================================================")
    time.sleep(2)

    # Start worker threads (virtual clients)
    # 20 threads are usually enough to load a t3.micro
    NUM_THREADS = 100
    threads = []

    try:
        for i in range(NUM_THREADS):
            t = threading.Thread(target=send_traffic, args=(target_url, i + 1))
            t.daemon = True  # Ensure threads exit when the main program stops
            t.start()
            threads.append(t)

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n🛑 Stopping traffic. End of the simulation.")
        print("   Check CloudWatch to observe the drop in load!")
