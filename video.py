import os
import json
import requests
import re
from datetime import datetime, timedelta
from itertools import cycle

# === CONFIG ===
API_KEYS = [
    'AIzaSyDh0y7ka_-IP56HAm2VuAwDU9yCNrqS-do',
    'AIzaSyAsr9lyCtfa3xizgzs3x4LqYsKHhZuOpzY',
    'AIzaSyAYSP0UZpL85f5l17tqFtxHlr_yClEk7cc',
    'AIzaSyCNqe4uWVgti_ZHBSI8_kKero_I6xf7qYk',
    'AIzaSyCOeLDK4m33SkeRqjhj5PBEdTug13pWGv4',
    'AIzaSyB9KjmivQbVzeGlVSh4sv1DjriFfsp-bCg',
    'AIzaSyDuXasL2olDdV5w8n65zQSq5FmxknofYww',
    'AIzaSyDGNNJg1aQQ2owQ6FIQcoBNmaQzYiMokPY',
    'AIzaSyAnyL18ylsE5Y6Q5h7VPm-xtjFKJOif3B8',
]

api_key_cycle = cycle(API_KEYS)
API_KEY = next(api_key_cycle)

OUTPUT_DIR = 'videos_data'
OUTPUT_FILE = 'videos.json'

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

SEARCH_QUERY = 'highlights'
MAX_RESULTS = 30
MAX_VIDEOS_PER_CHANNEL = 1
MAX_VIDEO_SECONDS = 10 * 60  # 10 minutes
DAYS_BACK = 60
MIN_COMMENTS = 3
MAX_COMMENTS = 10

# === HELPERS ===
def get_recent_date(days_back):
    date = datetime.utcnow() - timedelta(days=days_back)
    return date.isoformat("T") + "Z"

def parse_duration_to_seconds(duration):
    match = re.match(r'PT((\d+)H)?((\d+)M)?((\d+)S)?', duration)
    if not match:
        return 0
    hours = int(match.group(2) or 0)
    minutes = int(match.group(4) or 0)
    seconds = int(match.group(6) or 0)
    return hours * 3600 + minutes * 60 + seconds

def request_with_key_rotation(url, params):
    global API_KEY
    for _ in range(len(API_KEYS)):
        params['key'] = API_KEY
        response = requests.get(url, params=params)
        if response.status_code == 403 and "quota" in response.text.lower():
            print(f"⚠️ Quota exceeded for key {API_KEY}, rotating key...")
            API_KEY = next(api_key_cycle)
            continue
        return response
    print("❌ All API keys exhausted.")
    return None

def get_channel_info(channel_id):
    url = "https://www.googleapis.com/youtube/v3/channels"
    params = {'id': channel_id, 'part': 'snippet'}
    response = request_with_key_rotation(url, params)
    if response and response.status_code == 200:
        items = response.json().get('items', [])
        if items:
            snippet = items[0]['snippet']
            logo_url = snippet['thumbnails'].get('high', snippet['thumbnails'].get('default', {})).get('url', '')
            return snippet['title'], logo_url
    return "Unknown Channel", ""

def fetch_comments(video_id, min_comments=3, max_comments=10):
    comments_url = "https://www.googleapis.com/youtube/v3/commentThreads"
    params = {
        'part': 'snippet',
        'videoId': video_id,
        'maxResults': max_comments,
        'order': 'relevance',
        'textFormat': 'plainText'
    }
    response = request_with_key_rotation(comments_url, params)
    if not response or response.status_code != 200:
        return []
    items = response.json().get('items', [])
    comments = []
    for item in items:
        snippet = item['snippet']['topLevelComment']['snippet']
        comments.append({
            'author': snippet.get('authorDisplayName'),
            'text': snippet.get('textDisplay'),
            'likeCount': snippet.get('likeCount', 0),
            'publishedAt': snippet.get('publishedAt')
        })
    return comments if len(comments) >= min_comments else []

# === FETCH VIDEOS ===
def fetch_videos(channel_id):
    search_url = "https://www.googleapis.com/youtube/v3/search"
    search_params = {
        'channelId': channel_id,
        'part': 'snippet',
        'type': 'video',
        'maxResults': MAX_RESULTS,
        'publishedAfter': get_recent_date(DAYS_BACK),
        'q': SEARCH_QUERY,
        'order': 'date'
    }

    search_response = request_with_key_rotation(search_url, search_params)
    if not search_response or search_response.status_code != 200:
        print(f"❌ Error searching channel {channel_id}")
        return []

    items = search_response.json().get('items', [])
    video_ids = [item['id']['videoId'] for item in items]
    if not video_ids:
        return []

    details_url = "https://www.googleapis.com/youtube/v3/videos"
    details_params = {'part': 'contentDetails,snippet', 'id': ','.join(video_ids)}
    details_response = request_with_key_rotation(details_url, details_params)
    if not details_response or details_response.status_code != 200:
        print(f"❌ Error getting video details for channel {channel_id}")
        return []

    valid_videos = []
    for item in details_response.json().get('items', []):
        duration = item['contentDetails']['duration']
        seconds = parse_duration_to_seconds(duration)
        if 60 <= seconds <= MAX_VIDEO_SECONDS:
            thumbnails = item['snippet']['thumbnails']
            thumbnail_url = thumbnails.get('high', thumbnails.get('medium', thumbnails.get('default', {}))).get('url', '')
            valid_videos.append({
                'videoId': item['id'],
                'title': item['snippet']['title'],
                'uploadDate': item['snippet']['publishedAt'],
                'channelName': item['snippet']['channelTitle'],
                'embedUrl': f"https://www.youtube.com/embed/{item['id']}?enablejsapi=1&controls=1&modestbranding=1&autoplay=0",
                'thumbnail': thumbnail_url,
                'tags': item['snippet'].get('tags', []),  # <-- New
                'comments': fetch_comments(item['id'], MIN_COMMENTS, MAX_COMMENTS)
            })

    return valid_videos[:MAX_VIDEOS_PER_CHANNEL]

# === BACKFILL TAGS ===
def backfill_tags(videos):
    missing_tag_ids = [v['videoId'] for v in videos if not v.get('tags')]
    if not missing_tag_ids:
        return videos
    print(f"🔍 Fetching tags for {len(missing_tag_ids)} videos without tags...")
    for i in range(0, len(missing_tag_ids), 50):
        batch_ids = missing_tag_ids[i:i+50]
        details_url = "https://www.googleapis.com/youtube/v3/videos"
        details_params = {'part': 'snippet', 'id': ','.join(batch_ids)}
        resp = request_with_key_rotation(details_url, details_params)
        if resp and resp.status_code == 200:
            for item in resp.json().get('items', []):
                vid_id = item['id']
                tags = item['snippet'].get('tags', [])
                for v in videos:
                    if v['videoId'] == vid_id:
                        v['tags'] = tags
    return videos

# === SAVE JSON ===
def save_to_json(data, folder, filename):
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)

    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            try:
                existing_data = json.load(f)
            except json.JSONDecodeError:
                existing_data = []
    else:
        existing_data = []

    existing_dict = {video['videoId']: video for video in existing_data}
    for video in data:
        if video['videoId'] in existing_dict:
            existing_dict[video['videoId']].update(video)
        else:
            existing_dict[video['videoId']] = video

    merged_data = backfill_tags(list(existing_dict.values()))
    merged_data = sorted(merged_data, key=lambda x: x['uploadDate'], reverse=True)

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(merged_data, f, indent=2, ensure_ascii=False)
    print(f"✅ JSON updated. Total videos: {len(merged_data)}")

# === MAIN ===
def main():
    all_videos = []
    for channel_id in CHANNEL_IDS:
        videos = fetch_videos(channel_id)
        channel_name, channel_logo = get_channel_info(channel_id)
        print(f"📡 {channel_name} ({channel_id}): {len(videos)} videos fetched")
        for v in videos:
            v['channelLogo'] = channel_logo
        all_videos.extend(videos)

    save_to_json(all_videos, OUTPUT_DIR, OUTPUT_FILE)

if __name__ == "__main__":
    main()
