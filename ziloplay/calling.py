import requests
import sys

URL = "https://tmbd-wz5v.onrender.com/movie/popular"  
# 👆 create a simple /health endpoint on Render if possible
# If not, use "/" or "/movie/popular"

try:
    r = requests.get(URL, timeout=10)
    print("Status:", r.status_code)
except Exception as e:
    print("Error waking server:", e)
    sys.exit(1)
