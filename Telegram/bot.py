import os
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from colorthief import ColorThief
from datetime import datetime

# ===============================
# CONFIGURATION
# ===============================
MATCHES_BASE_URL = "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/matches/"
TEAMS_BASE_URL = "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/"
BRAND_LOGO_URL = "https://goal4u.netlify.app/assets/img/site-logo/bg-white.png"
OUTPUT_DIR, CACHE_DIR = "output_images", "cache"

# Tracker file to prevent duplicate posts
TRACKER_FILE = "posted_matches.txt"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# --- FONT FIX FOR GITHUB ACTIONS ---
FONT_URL = "https://github.com/googlefonts/arimo/raw/main/fonts/ttf/Arimo-Bold.ttf"
FONT_PATH = os.path.join(CACHE_DIR, "Arimo-Bold.ttf")

if not os.path.exists(FONT_PATH):
    try:
        with open(FONT_PATH, "wb") as f:
            f.write(requests.get(FONT_URL).content)
    except Exception as e:
        print(f"⚠️ Font download failed: {e}")

# Leagues to process
LEAGUES = {
    "EPL": "EPL.json",      "ESP": "ESP.json",     "DEB": "DEB.json",
    "DED": "DED.json",      "ITSA": "ITSA.json",   "FRL1": "FRL1.json",
    "BSA": "BSA.json",      "ELC": "ELC.json",     "POR": "POR.json",
    "UCL": "UCL.json",      "WC": "WC.json",       "MLS": "MLS.json"
}

# --- TELEGRAM CONFIG ---
TELEGRAM_TOKEN = "8264321603:AAFA0cLUm97KVQlT5lITS05U-FLNSpmhCYg"
TELEGRAM_CHAT_ID = "@goal4utv"

# ===============================
# UTILITIES
# ===============================
def load_posted_matches():
    if os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE, "r") as f:
            return set(f.read().splitlines())
    return set()

def save_posted_match(unique_id):
    with open(TRACKER_FILE, "a") as f:
        f.write(f"{unique_id}\n")

def download_file(url, filename):
    filepath = os.path.join(CACHE_DIR, filename)
    if not os.path.exists(filepath):
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                with open(filepath, "wb") as f: f.write(r.content)
        except Exception as e:
            print(f"Error downloading {url}: {e}")
    return filepath

def get_team_color(image_path):
    try:
        ct = ColorThief(image_path)
        palette = ct.get_palette(color_count=5)
        color = palette[0]
        return (int(color[0]*0.8), int(color[1]*0.8), int(color[2]*0.8))
    except:
        return (30, 30, 30)

def post_to_telegram(image_path, caption):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    with open(image_path, "rb") as photo:
        response = requests.post(
            url,
            data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption, "parse_mode": "HTML"},
            files={"photo": photo}
        )
    print("📲 Telegram Post Status:", response.status_code, response.text)
    return response.status_code == 200

# ===============================
# THE PREMIUM DESIGN ENGINE
# ===============================
def create_unique_match_card(home, away, league, brand_path, time):
    W, H = 1280, 720
    
    c_home = get_team_color(home['logo'])
    c_away = get_team_color(away['logo'])
    
    canvas = Image.new("RGBA", (W, H), (*c_away, 255))
    
    poly_points = [(0, 0), (W//2 + 120, 0), (W//2 - 120, H), (0, H)]
    
    shadow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_layer)
    shadow_points = [(x+25, y) for x,y in poly_points]
    s_draw.polygon(shadow_points, fill=(0, 0, 0, 180))
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(25)) 
    
    canvas = Image.alpha_composite(canvas, shadow_layer)
    draw = ImageDraw.Draw(canvas)
    draw.polygon(poly_points, fill=(*c_home, 255))

    vignette = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    v_draw = ImageDraw.Draw(vignette)
    for i in range(200):
        alpha = int((i / 200) * 120)
        v_draw.rectangle([i, i, W-i, H-i], outline=(0, 0, 0, alpha))
    canvas = Image.alpha_composite(canvas, vignette)

    # --- FIX: SMART SIZING ENGINE ---
    def prep_img(path, target_size):
        img = Image.open(path).convert("RGBA")
        
        # 1. Slice off invisible padding around the API logos
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)
            
        # 2. Perfect scaling (scales UP tiny images, scales DOWN huge ones)
        w, h = img.size
        if w > 0 and h > 0:
            ratio = target_size / max(w, h)
            new_size = (int(w * ratio), int(h * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            
        return img

    # Tightly controlled logo sizes so they never overlap the edges or text
    h_img = prep_img(home['logo'], 240)
    a_img = prep_img(away['logo'], 240)
    l_img = prep_img(league['logo'], 75)
    b_img = prep_img(brand_path, 150) 

    # Dynamic center paste for Teams
    canvas.paste(h_img, (W//4 - h_img.width//2, H//2 - h_img.height//2 - 20), h_img)
    canvas.paste(a_img, (3*W//4 - a_img.width//2, H//2 - a_img.height//2 - 20), a_img)
    
    draw = ImageDraw.Draw(canvas) 
    
    # Static Anchor for League Logo Circle
    league_x, league_y = 50, 30
    logo_center_x = league_x + (l_img.width // 2)
    logo_center_y = league_y + (l_img.height // 2)
    bg_radius = 55
    draw.ellipse([logo_center_x - bg_radius, logo_center_y - bg_radius, 
                  logo_center_x + bg_radius, logo_center_y + bg_radius], fill="white")
    canvas.paste(l_img, (league_x, league_y), l_img)

    brand_x = W - b_img.width - 50
    brand_y = logo_center_y - (b_img.height // 2) 
    canvas.paste(b_img, (brand_x, brand_y), b_img)

    badge_r = 45
    badge_box = [W//2 - badge_r, H//2 - badge_r - 20, W//2 + badge_r, H//2 + badge_r - 20]
    draw.ellipse(badge_box, fill="white", outline=(20, 20, 20), width=4)

    try:
        font_file = FONT_PATH if os.path.exists(FONT_PATH) else "arialbd.ttf"
        f_teams = ImageFont.truetype(font_file, 55)
        f_vs = ImageFont.truetype(font_file, 45)
        f_time = ImageFont.truetype(font_file, 40)
    except:
        f_teams = f_vs = f_time = ImageFont.load_default()

    draw.text((W//2, H//2 - 20), "VS", font=f_vs, fill="black", anchor="mm")
    
    time_box = [W//2 - 80, H//2 + 50, W//2 + 80, H//2 + 100]
    draw.rounded_rectangle(time_box, radius=25, fill=(0, 0, 0, 200), outline=(255,215,0,255), width=2)
    draw.text((W//2, H//2 + 75), time, font=f_time, fill=(255, 215, 0), anchor="mm")

    def draw_shadow_text(pos, text, font):
        draw.text((pos[0]+3, pos[1]+3), text, font=font, fill=(0,0,0,180), anchor="mm")
        draw.text(pos, text, font=font, fill="white", anchor="mm")

    draw_shadow_text((W//4, H//2 + 220), home['name'].upper(), f_teams)
    draw_shadow_text((3*W//4, H//2 + 220), away['name'].upper(), f_teams)

    out_name = f"{home['name']}_vs_{away['name']}.png".replace(" ", "_")
    out_path = os.path.join(OUTPUT_DIR, out_name)
    canvas.convert("RGB").save(out_path, quality=95)
    print(f"🔥 Successfully generated unique design: {out_name}")
    
    return out_path 

# ===============================
# MAIN RUNNER
# ===============================
print("Fetching Match Data...")

brand_path = download_file(BRAND_LOGO_URL, "brand_logo.png")
posted_matches = load_posted_matches()

# Auto-detect today's date
target_date = datetime.utcnow().strftime("%Y-%m-%d")

# Note: Overriding for testing. Comment out for pure daily automation!
target_date = "2026-02-21" 

for league_code, json_filename in LEAGUES.items():
    print(f"\n⚽ Checking league: {league_code} ({json_filename})")
    
    try:
        matches_req = requests.get(MATCHES_BASE_URL + json_filename)
        teams_req = requests.get(TEAMS_BASE_URL + json_filename)
        
        # Stops the bot from crashing if a JSON is missing
        if matches_req.status_code != 200 or teams_req.status_code != 200:
            print(f"⚠️ JSON file missing for {league_code}. Skipping.")
            continue
            
        matches = matches_req.json()
        teams = teams_req.json()
        
        # Stops the bot from crashing if JSON is empty/broken
        if not isinstance(teams, list):
            print(f"⚠️ Data format error for {league_code}. Skipping.")
            continue

    except Exception as e:
        print(f"⚠️ Fetch Error on {league_code}: {e}")
        continue
        
    team_dict = {t.get('id'): t for t in teams if 'id' in t}

    for m in matches:
        if m.get("Date") == target_date:
            time_str = m["DateTime"].split("T")[1][:5]
            game_id = str(m.get("GameId", "Unknown"))
            
            unique_match_id = f"{m['HomeTeamKey']}_{m['AwayTeamKey']}_{m.get('Date')}_{time_str}"
            if unique_match_id in posted_matches:
                print(f"⏩ ALREADY POSTED: {unique_match_id}. Skipping.")
                continue

            home_t = team_dict.get(m['HomeTeamId'])
            if not home_t: continue

            h_path = download_file(m["HomeTeamLogo"], f"logo_{m['HomeTeamId']}.png")
            a_path = download_file(m["AwayTeamLogo"], f"logo_{m['AwayTeamId']}.png")
            
            league_node = {"name": m.get('RoundName', league_code), "id": "default"}
            if 'runningCompetitions' in home_t and len(home_t['runningCompetitions']) > 0:
                league_node = home_t['runningCompetitions'][0] 
                for comp in home_t['runningCompetitions']:
                    if comp.get('name') == m.get('RoundName'):
                        league_node = comp
                        break
            
            l_emblem = league_node.get('emblem', "https://upload.wikimedia.org/wikipedia/commons/4/44/Soccer_ball.svg")
            l_path = download_file(l_emblem, f"league_{league_node.get('id', 'default')}.png")

            # 1. Create the graphic
            img_path = create_unique_match_card(
                {"name": m['HomeTeamKey'], "logo": h_path},
                {"name": m['AwayTeamKey'], "logo": a_path},
                {"name": league_node.get('name', league_code), "logo": l_path},
                brand_path,
                time_str
            )
            
            # 2. Format your channel's caption
            live_link = f"https://goal4utv.netlify.app/match/{game_id}"
            
            caption = f"""🚨 <b>MATCHDAY</b> 🚨

⚽️ {m['HomeTeamKey']} vs {m['AwayTeamKey']}
🏆 {league_node.get('name', league_code)}
📅 Date: {m.get('Date')}
🕒 Kick-off: {time_str} UTC

🔗 <b>Watch Live:</b> <a href='{live_link}'>Click Here</a>

📺 @goal4utv"""

            # 3. Auto-post!
            print(f"🚀 Posting {m['HomeTeamKey']} vs {m['AwayTeamKey']} to Telegram...")
            if post_to_telegram(img_path, caption):
                save_posted_match(unique_match_id)
                posted_matches.add(unique_match_id)
