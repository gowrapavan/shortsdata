import os
import json
import requests
from datetime import datetime, timedelta
from time import sleep
from isodate import parse_duration

# === CONFIG ===
# Note: In a production environment, use environment variables for these keys.
API_KEYS = [
    'AIzaSyDy9ZlMxhP7OooTxLS30VwXEQBo7GdcVQg',    
    'AIzaSyAsr9lyCtfa3xizgzs3x4LqYsKHhZuOpzY',
    'AIzaSyAYSP0UZpL85f5l17tqFtxHlr_yClEk7cc',
    'AIzaSyCNqe4uWVgti_ZHBSI8_kKero_I6xf7qYk',
    'AIzaSyCOeLDK4m33SkeRqjhj5PBEdTug13pWGv4',
    'AIzaSyB9KjmivQbVzeGlVSh4sv1DjriFfsp-bCg',
    'AIzaSyDuXasL2olDdV5w8n65zQSq5FmxknofYww',
    'AIzaSyDGNNJg1aQQ2owQ6FIQcoBNmaQzYiMokPY',
    'AIzaSyAnyL18ylsE5Y6Q5h7VPm-xtjFKJOif3B8',
]

CHANNEL_IDS = [
    'UC14UlmYlSNiQCBe9Eookf_A', 'UCWV3obpZVGgJ3j9FVhEjF2Q', 'UCkzCjdRMrW2vXLx8mvPVLdQ',
    'UC9LQwHZoucFT94I2h6JOcjw', 'UCt9a_qP9CqHCNwilf-iULag', 'UCLzKhsxrExAC6yAdtZ-BOWw',
    'UCKcx1uK38H4AOkmfv4ywlrg', 'UCvXzEblUa0cfny4HAJ_ZOWw', 'UCSZ21xyG8w_33KriMM69IxQ',
    'UCooTLkxcpnTNx6vfOovfBFA', 'UCd09ztChTkJ9dlY6RLawSog', 'UC2bW_AY9BlbYLGJSXAbjS4Q',
    'UCWsDFcIhY2DBi3GB5uykGXA', 'UCQBxzdEPXjy05MtpfbdtMxQ', 'UCSZbXT5TLLW_i-5W8FZpFsg',
    'UCE97AW7eR8VVbVPBy4cCLKg', 'UCKvn9VBLAiLiYL4FFJHri6g', 'UCI4hFxNmsvfkus2-XC9MOng',
    'UCG5qGWdu8nIRZqJ_GgDwQ-w', 'UCU2PacFf99vhb3hNiYDmxww', 'UCuzKFwdh7z2GHcIOX_tXgxA',
    'UC3Ad7MMhJ1NHAkYbtgbVJ1Q', 'UCyGa1YEx9ST66rYrJTGIKOw', 'UCcclZ7Nbh0U383eP0N-nV0g',
    'UCBTy8j2cPy6zw68godcE7MQ', 'UCK8rTVgp3-MebXkmeJcQb1Q', 'UCnpdLn1-k-DcyWi0bNezRig',
    'UCUGj4_2zT8gY_O_xaiCsR6A', 'UCL6KKxaCCnOJFaxV53Clp1A', 'UC_apha4piyJCHSuYZbSi8uA',
    'UCeBYAZ84AQA2WVHGjpKRy7A'
]

MAX_RESULTS = 30
OUTPUT_DIR = "shorts_data"
OUTPUT_FILE = "shorts.json"
DAYS_BACK = 30
TOP_COMMENT_COUNT = 5
RETRY_LIMIT = 3
RETRY_DELAY = 2

_api_index = 0

def get_api_key():
    global _api_index
    return API_KEYS[_api_index]

def rotate_api_key():
    global _api_index
    _api_index = (_api_index + 1) % len(API_KEYS)

def safe_request(url):
    for attempt in range(RETRY_LIMIT):
        try:
            res = requests.get(url, timeout=10)
            if res.status_code in (403, 400):
                rotate_api_key()
                url = url.split("key=")[0] + f"key={get_api_key()}"
                continue
            res.raise_for_status()
            return res.json()
        except Exception as e:
            sleep(RETRY_DELAY)
    return {}

def get_channel_metadata(channel_id):
    url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet&id={channel_id}&key={get_api_key()}"
    data = safe_request(url)
    if "items" not in data or not data["items"]: return {"channelName": "Unknown", "channelLogo": ""}
    s = data["items"][0]["snippet"]
    return {"channelName": s["title"], "channelLogo": s["thumbnails"]["default"]["url"]}

def fetch_shorts_list(channel_id, meta):
    url = f"https://www.googleapis.com/youtube/v3/search?key={get_api_key()}&channelId={channel_id}&part=snippet&maxResults={MAX_RESULTS}&order=date&type=video"
    data = safe_request(url)
    results = []
    one_month_ago = datetime.utcnow() - timedelta(days=DAYS_BACK)
    
    for item in data.get("items", []):
        vid = item["id"].get("videoId")
        snippet = item["snippet"]
        if datetime.strptime(snippet["publishedAt"], "%Y-%m-%dT%H:%M:%SZ") < one_month_ago: continue
        
        results.append({
            "videoId": vid,
            "title": snippet["title"],
            "description": snippet.get("description", ""),
            "uploadDate": snippet["publishedAt"],
            "channelName": meta["channelName"],
            "channelLogo": meta["channelLogo"],
            "embedUrl": f"https://www.youtube.com/embed/{vid}?autoplay=0&mute=1"
        })
    return results

def get_video_details(video_ids):
    all_details = {}
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i + 50]
        url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics,contentDetails&id={','.join(chunk)}&key={get_api_key()}"
        data = safe_request(url)
        for item in data.get("items", []):
            stats = item.get("statistics", {})
            all_details[item["id"]] = {
                "likeCount": int(stats.get("likeCount", 0)),
                "viewCount": int(stats.get("viewCount", 0)),
                "duration": item.get("contentDetails", {}).get("duration", "")
            }
    return all_details

def get_top_comments(video_id):
    url = f"https://www.googleapis.com/youtube/v3/commentThreads?part=snippet&videoId={video_id}&key={get_api_key()}&maxResults={TOP_COMMENT_COUNT}&order=relevance"
    data = safe_request(url)
    return [{"author": i["snippet"]["topLevelComment"]["snippet"]["authorDisplayName"], "text": i["snippet"]["topLevelComment"]["snippet"]["textDisplay"]} for i in data.get("items", [])]

def main():
    output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE)
    existing_data = []
    if os.path.exists(output_path):
        with open(output_path, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
    
    existing_by_id = {item["videoId"]: item for item in existing_data}
    new_shorts_found = []

    for channel_id in CHANNEL_IDS:
        meta = get_channel_metadata(channel_id)
        fetched = fetch_shorts_list(channel_id, meta)
        for s in fetched:
            if s["videoId"] not in existing_by_id:
                new_shorts_found.append(s)
                existing_by_id[s["videoId"]] = s

    if new_shorts_found:
        print(f"Found {len(new_shorts_found)} new videos. Fetching details...")
        details = get_video_details([s["videoId"] for s in new_shorts_found])
        for s in new_shorts_found:
            vid = s["videoId"]
            s.update(details.get(vid, {}))
            s["comments"] = get_top_comments(vid)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(list(existing_by_id.values()), f, indent=2, ensure_ascii=False)
        print("✅ Data updated successfully.")
    else:
        print("✅ No new videos found. No changes made.")

if __name__ == "__main__":
    main()
