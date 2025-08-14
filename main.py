import os
import json
import requests
from datetime import datetime, timedelta
from time import sleep
from isodate import parse_duration  # needed for duration parsing

# === CONFIG ===
API_KEYS = [
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
 #Top Clubs
  'UC14UlmYlSNiQCBe9Eookf_A',  # FC Barcelona
  'UCWV3obpZVGgJ3j9FVhEjF2Q',  # Real Madrid
  'UCkzCjdRMrW2vXLx8mvPVLdQ',  # Manchester City
  'UC9LQwHZoucFT94I2h6JOcjw',  # Liverpool FCd
  'UCt9a_qP9CqHCNwilf-iULag',  # PSG
  'UCLzKhsxrExAC6yAdtZ-BOWw', #Juventus
  'UCKcx1uK38H4AOkmfv4ywlrg', #AC Milan
  'UCvXzEblUa0cfny4HAJ_ZOWw', #Inter Milan
  'UCSZ21xyG8w_33KriMM69IxQ',
  'UCooTLkxcpnTNx6vfOovfBFA',
  'UCd09ztChTkJ9dlY6RLawSog',
  'UC2bW_AY9BlbYLGJSXAbjS4Q',
  'UCWsDFcIhY2DBi3GB5uykGXA',
  'UCQBxzdEPXjy05MtpfbdtMxQ',
  'UCSZbXT5TLLW_i-5W8FZpFsg',
  'UCE97AW7eR8VVbVPBy4cCLKg',
  'UCKvn9VBLAiLiYL4FFJHri6g',


  'UCI4hFxNmsvfkus2-XC9MOng',

 #Popular Leagues & Competitions
  #'UCTv-XvfzLX3i4IGWAm4sbmA', #LaLiga not alowed
  'UCG5qGWdu8nIRZqJ_GgDwQ-w', #Premier League
  'UCU2PacFf99vhb3hNiYDmxww', #Champions League (UEFA)

 #Other Clubs & Channels
  'UCuzKFwdh7z2GHcIOX_tXgxA', #Atlético Madrid
  'UC3Ad7MMhJ1NHAkYbtgbVJ1Q', #Hamid TV (shorts/highlights content)
  'UCyGa1YEx9ST66rYrJTGIKOw', #UEFA (⚠️ allows embedding, but avoid FIFA content)

 #Additional Safe Channels
  'UCcclZ7Nbh0U383eP0N-nV0g', #433 (works well)
  'UCBTy8j2cPy6zw68godcE7MQ', #AFTV
  'UCK8rTVgp3-MebXkmeJcQb1Q', #Borussia Dortmund
  'UCvXzEblUa0cfny4HAJ_ZOWw', #Inter Milan (alt)
  'UCnpdLn1-k-DcyWi0bNezRig',
'UCUGj4_2zT8gY_O_xaiCsR6A',
'UCL6KKxaCCnOJFaxV53Clp1A',
'UC_apha4piyJCHSuYZbSi8uA',
'UCeBYAZ84AQA2WVHGjpKRy7A',
]


MAX_RESULTS = 30
OUTPUT_DIR = "shorts_data"
OUTPUT_FILE = "shorts.json"
DAYS_BACK = 30
TOP_COMMENT_COUNT = 10
RETRY_LIMIT = 3
RETRY_DELAY = 2

# === INTERNAL STATE ===
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
                print(f"🔁 API quota issue with key {_api_index + 1}, rotating key...")
                rotate_api_key()
                url = url.replace(f"key={get_api_key()}", f"key={API_KEYS[_api_index]}")
                continue
            res.raise_for_status()
            return res.json()
        except Exception as e:
            print(f"⚠️ Request failed (attempt {attempt + 1}): {e}")
            sleep(RETRY_DELAY)
    return {}

def get_channel_metadata(channel_id):
    url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet&id={channel_id}&key={get_api_key()}"
    data = safe_request(url)
    if "items" not in data or not data["items"]:
        return {"channelName": "Unknown", "channelLogo": ""}
    snippet = data["items"][0]["snippet"]
    return {
        "channelName": snippet["title"],
        "channelLogo": snippet["thumbnails"]["default"]["url"],
    }

def fetch_shorts(channel_id, meta):
    url = (
        f"https://www.googleapis.com/youtube/v3/search?"
        f"key={get_api_key()}&channelId={channel_id}&part=snippet&maxResults={MAX_RESULTS}&order=date&type=video"
    )
    data = safe_request(url)

    recent_videos = []
    one_month_ago = datetime.utcnow() - timedelta(days=DAYS_BACK)
    video_ids = []
    snippets = {}

    for item in data.get("items", []):
        video_id = item["id"]["videoId"]
        snippet = item["snippet"]
        upload_date = datetime.strptime(snippet["publishedAt"], "%Y-%m-%dT%H:%M:%SZ")
        if upload_date < one_month_ago:
            continue
        video_ids.append(video_id)
        snippets[video_id] = snippet

    details = get_video_details(video_ids)

    for video_id in video_ids:
        snippet = snippets[video_id]
        detail = details.get(video_id, {})
        duration_str = detail.get("duration", "PT0S")

        try:
            duration_seconds = parse_duration(duration_str).total_seconds()
        except Exception:
            duration_seconds = 0

        is_short = (
            "#shorts" in snippet["title"].lower()
            or "shorts" in snippet.get("description", "").lower()
            or duration_seconds <= 120
        )

        if not is_short:
            continue

        recent_videos.append({
            "videoId": video_id,
            "title": snippet["title"],
            "description": snippet.get("description", ""),
            "uploadDate": snippet["publishedAt"],
            "channelName": meta["channelName"],
            "channelLogo": meta["channelLogo"],
            "embedUrl": f"https://www.youtube.com/embed/{video_id}?autoplay=0&mute=1"
        })

    return recent_videos

def get_video_details(video_ids):
    all_details = {}
    chunk_size = 50
    for i in range(0, len(video_ids), chunk_size):
        chunk = video_ids[i:i + chunk_size]
        url = (
            f"https://www.googleapis.com/youtube/v3/videos?"
            f"part=snippet,statistics,contentDetails&id={','.join(chunk)}&key={get_api_key()}"
        )
        data = safe_request(url)
        for item in data.get("items", []):
            vid = item["id"]
            stats = item.get("statistics", {})
            snippet = item.get("snippet", {})
            all_details[vid] = {
                "tags": snippet.get("tags", []),
                "categoryId": snippet.get("categoryId", ""),
                "likeCount": int(stats.get("likeCount", 0)),
                "viewCount": int(stats.get("viewCount", 0)),
                "publishedAt": snippet.get("publishedAt", ""),
                "duration": item.get("contentDetails", {}).get("duration", "")
            }
    return all_details

def get_top_comments(video_id, max_comments=TOP_COMMENT_COUNT):
    url = (
        f"https://www.googleapis.com/youtube/v3/commentThreads?"
        f"part=snippet&videoId={video_id}&key={get_api_key()}"
        f"&maxResults={max_comments}&order=relevance"
    )
    data = safe_request(url)
    comments = []
    for item in data.get("items", []):
        top_comment = item["snippet"]["topLevelComment"]["snippet"]
        comments.append({
            "author": top_comment["authorDisplayName"],
            "text": top_comment["textDisplay"],
            "likeCount": top_comment.get("likeCount", 0),
            "publishedAt": top_comment["publishedAt"]
        })
    return comments

def safe_load_json(path):
    """Load JSON safely, return [] if file is missing, empty, or invalid."""
    if not os.path.exists(path) or os.stat(path).st_size == 0:
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"⚠️ Warning: {path} is invalid JSON. Starting fresh.")
        return []

def save_to_json(data, folder, filename):
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ Updated {filename} with {len(data)} total shorts.")

def main():
    output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE)
    existing_data = safe_load_json(output_path)

    existing_by_id = {item["videoId"]: item for item in existing_data}
    all_video_ids = set(existing_by_id.keys())
    recent_uploads = {}

    for channel_id in CHANNEL_IDS:
        meta = get_channel_metadata(channel_id)
        fetched = fetch_shorts(channel_id, meta)
        print(f"📺 {meta['channelName']}: {len(fetched)} recent shorts found.")

        new_shorts = [s for s in fetched if s["videoId"] not in all_video_ids]
        for short in new_shorts:
            recent_uploads[short["videoId"]] = short
            all_video_ids.add(short["videoId"])

        if not new_shorts:
            print(f"⏩ Skipping {meta['channelName']} — All recent shorts already fetched.")

    for vid, short in recent_uploads.items():
        existing_by_id[vid] = short

    all_ids = list(existing_by_id.keys())
    print(f"📊 Fetching full metadata for {len(all_ids)} videos...")

    details = get_video_details(all_ids)

    for i, vid in enumerate(all_ids, 1):
        video_info = details.get(vid, {})
        existing_by_id[vid].update(video_info)
        if vid in recent_uploads:
            existing_by_id[vid]["comments"] = get_top_comments(vid)
        if i % 25 == 0:
            print(f"⏳ Processed {i}/{len(all_ids)} videos...")

    all_shorts = list(existing_by_id.values())
    save_to_json(all_shorts, OUTPUT_DIR, OUTPUT_FILE)

if __name__ == "__main__":
    main()
