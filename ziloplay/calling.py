# ziloplay/calling.py

import requests
import time
import sys

URL = "https://tmbd-wz5v.onrender.com/discover/movie"

TIMEOUT = 240        # 4 minutes (Render cold start safe)
MAX_RETRIES = 3      # retry in case Render resets connection
SLEEP_BETWEEN = 20   # seconds


def wake_render():
    print("🔄 Starting Render wake-up job")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"➡️ Attempt {attempt}/{MAX_RETRIES}")
            response = requests.get(URL, timeout=TIMEOUT)

            print("✅ Server responded")
            print("Status Code:", response.status_code)
            print("Response:", response.text[:200])

            return  # SUCCESS — exit cleanly

        except requests.exceptions.RequestException as error:
            print(f"⚠️ Attempt {attempt} failed:", error)

            if attempt < MAX_RETRIES:
                print(f"⏳ Waiting {SLEEP_BETWEEN}s before retry...")
                time.sleep(SLEEP_BETWEEN)

    print("🟡 Render did not respond in time, but workflow will NOT fail")
    sys.exit(0)  # IMPORTANT: keep workflow GREEN


if __name__ == "__main__":
    wake_render()
