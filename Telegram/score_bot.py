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
STANDINGS_BASE_URL = "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/standing/"
BRAND_LOGO_URL = "https://goal4u.netlify.app/assets/img/site-logo/bg-white.png"

OUTPUT_DIR, CACHE_DIR = "output_images", "cache"
TRACKER_FILE = "posted_scores.txt" # New tracker specifically for final scores!

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# --- FONT FIX FOR GITHUB ACTIONS ---
FONT_BOLD_URL = "https://github.com/googlefonts/arimo/raw/main/fonts/ttf/Arimo-Bold.ttf"
FONT_REG_URL = "https://github.com/googlefonts/arimo/raw/main/fonts/ttf/Arimo-Regular.ttf"
FONT_BOLD = os.path.join(CACHE_DIR, "Arimo-Bold.ttf")
FONT_REG = os.path.join(CACHE_DIR, "Arimo-Regular.ttf")

for f_path, f_url in [(FONT_BOLD, FONT_BOLD_URL), (FONT_REG, FONT_REG_URL)]:
    if not os.path.exists(f_path):
        try:
            with open(f_path, "wb") as f: f.write(requests.get(f_url).content)
        except Exception as e:
            print(f"⚠️ Font download failed: {e}")

LEAGUES = {
    "EPL": "EPL.json",      "ESP": "ESP.json",     "DEB": "DEB.json",
    "DED": "DED.json",      "ITSA": "ITSA.json",   "FRL1": "FRL1.json",
    "BSA": "BSA.json",      "ELC": "ELC.json",     "POR": "POR.json",
    "UCL": "UCL.json",      "WC": "WC.json",       "MLS": "MLS.json"
}

TELEGRAM_TOKEN = "8264321603:AAFA0cLUm97KVQlT5lITS05U-FLNSpmhCYg"
TELEGRAM_CHAT_ID = "@goal4utv"

# ===============================
# UTILITIES
# ===============================
def load_posted_scores():
    if os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE, "r") as f: return set(f.read().splitlines())
    return set()

def save_posted_score(unique_id):
    with open(TRACKER_FILE, "a") as f: f.write(f"{unique_id}\n")

def download_file(url, filename):
    filepath = os.path.join(CACHE_DIR, filename)
    if not os.path.exists(filepath):
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                with open(filepath, "wb") as f: f.write(r.content)
        except: pass
    return filepath

def get_team_color(image_path):
    try:
        ct = ColorThief(image_path)
        r, g, b = ct.get_palette(color_count=5)[0]
        brightness = (r * 0.299 + g * 0.587 + b * 0.114)
        if brightness < 40: return (85, 85, 85)
        return (int(r * 0.8), int(g * 0.8), int(b * 0.8))
    except: return (50, 50, 50)

def post_to_telegram(image_path, caption):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    with open(image_path, "rb") as photo:
        response = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption, "parse_mode": "HTML"}, files={"photo": photo})
    print("📲 Telegram Post Status:", response.status_code)
    return response.status_code == 200

# ===============================
# POST-MATCH SCORECARD ENGINE
# ===============================
def create_score_card(home, away, league, brand_path, h_score, a_score, h_stand, a_stand):
    # Canvas expanded to 960px tall to fit the standings table at the bottom
    W, H_GRAPHIC, H_TABLE = 1280, 720, 240
    H_TOTAL = H_GRAPHIC + H_TABLE
    
    c_home = get_team_color(home['logo'])
    c_away = get_team_color(away['logo'])
    
    canvas = Image.new("RGBA", (W, H_TOTAL), (20, 20, 24, 255)) # Base dark color for table
    
    # --- 1. TOP GRAPHIC (Match Design) ---
    graphic = Image.new("RGBA", (W, H_GRAPHIC), (*c_away, 255))
    poly_points = [(0, 0), (W//2 + 120, 0), (W//2 - 120, H_GRAPHIC), (0, H_GRAPHIC)]
    
    shadow_layer = Image.new("RGBA", (W, H_GRAPHIC), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_layer)
    s_draw.polygon([(x+25, y) for x,y in poly_points], fill=(0, 0, 0, 180))
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(25)) 
    
    graphic = Image.alpha_composite(graphic, shadow_layer)
    g_draw = ImageDraw.Draw(graphic)
    g_draw.polygon(poly_points, fill=(*c_home, 255))

    vignette = Image.new("RGBA", (W, H_GRAPHIC), (0, 0, 0, 0))
    v_draw = ImageDraw.Draw(vignette)
    for i in range(200):
        alpha = int((i / 200) * 120)
        v_draw.rectangle([i, i, W-i, H_GRAPHIC-i], outline=(0, 0, 0, alpha))
    graphic = Image.alpha_composite(graphic, vignette)

    def prep_img(path, target_size):
        img = Image.open(path).convert("RGBA")
        bbox = img.getbbox()
        if bbox: img = img.crop(bbox)
        w, h = img.size
        if w > 0 and h > 0:
            ratio = target_size / max(w, h)
            img = img.resize((int(w * ratio), int(h * ratio)), Image.Resampling.LANCZOS)
        return img

    h_img = prep_img(home['logo'], 240)
    a_img = prep_img(away['logo'], 240)
    l_img = prep_img(league['logo'], 75)
    b_img = prep_img(brand_path, 150) 

    graphic.paste(h_img, (W//4 - h_img.width//2, H_GRAPHIC//2 - h_img.height//2 - 20), h_img)
    graphic.paste(a_img, (3*W//4 - a_img.width//2, H_GRAPHIC//2 - a_img.height//2 - 20), a_img)
    
    g_draw = ImageDraw.Draw(graphic) 
    
    # League Logo Anchor
    circle_center_x, circle_center_y = 105, 85
    bg_radius = 55
    g_draw.ellipse([circle_center_x - bg_radius, circle_center_y - bg_radius, circle_center_x + bg_radius, circle_center_y + bg_radius], fill="white")
    graphic.paste(l_img, (circle_center_x - l_img.width//2, circle_center_y - l_img.height//2), l_img)

    brand_x, brand_y = W - b_img.width - 50, circle_center_y - (b_img.height // 2)
    graphic.paste(b_img, (brand_x, brand_y), b_img)

    # FINAL SCORE BUBBLE (Replaces "VS")
    badge_w, badge_h = 160, 90
    badge_box = [W//2 - badge_w//2, H_GRAPHIC//2 - badge_h//2 - 20, W//2 + badge_w//2, H_GRAPHIC//2 + badge_h//2 - 20]
    g_draw.rounded_rectangle(badge_box, radius=45, fill="white", outline=(20, 20, 20), width=4)

    try:
        f_score = ImageFont.truetype(FONT_BOLD, 55)
        f_teams = ImageFont.truetype(FONT_BOLD, 55)
        f_pill = ImageFont.truetype(FONT_BOLD, 30)
        f_th = ImageFont.truetype(FONT_BOLD, 22) # Table Header Font
        f_td = ImageFont.truetype(FONT_REG, 26)  # Table Data Font
    except:
        f_score = f_teams = f_pill = f_th = f_td = ImageFont.load_default()

    score_text = f"{h_score} - {a_score}"
    g_draw.text((W//2, H_GRAPHIC//2 - 20), score_text, font=f_score, fill="black", anchor="mm")
    
    # FULL TIME Pill
    pill_box = [W//2 - 80, H_GRAPHIC//2 + 50, W//2 + 80, H_GRAPHIC//2 + 100]
    g_draw.rounded_rectangle(pill_box, radius=25, fill=(0, 0, 0, 220), outline=(255,215,0,255), width=2)
    g_draw.text((W//2, H_GRAPHIC//2 + 75), "FULL TIME", font=f_pill, fill=(255, 215, 0), anchor="mm")

    def draw_shadow_text(pos, text, font):
        g_draw.text((pos[0]+3, pos[1]+3), text, font=font, fill=(0,0,0,180), anchor="mm")
        g_draw.text(pos, text, font=font, fill="white", anchor="mm")

    draw_shadow_text((W//4, H_GRAPHIC//2 + 220), home['name'].upper(), f_teams)
    draw_shadow_text((3*W//4, H_GRAPHIC//2 + 220), away['name'].upper(), f_teams)

    # Paste Top Graphic onto Base Canvas
    canvas.paste(graphic, (0, 0))
    
    # --- 2. BOTTOM GRAPHIC (Standings Table) ---
    c_draw = ImageDraw.Draw(canvas)
    
    # Header Row
    y_hdr = H_GRAPHIC + 20
    c_draw.rectangle([0, H_GRAPHIC, W, y_hdr + 40], fill=(40, 40, 50, 255))
    
    cols = {"POS": 80, "TEAM": 220, "MP": 700, "W": 820, "D": 940, "L": 1060, "PTS": 1180}
    for title, x_pos in cols.items():
        c_draw.text((x_pos, y_hdr + 20), title, font=f_th, fill=(200, 200, 200), anchor="mm")

    def draw_table_row(y_pos, stand_data, team_name, logo_path):
        # Draw subtle row background
        c_draw.rectangle([0, y_pos, W, y_pos + 70], fill=(30, 30, 38, 255))
        
        # If no standings data (e.g. Cup match), just print N/A
        if not stand_data:
            c_draw.text((W//2, y_pos + 35), f"Standings unavailable for {team_name}", font=f_td, fill=(150, 150, 150), anchor="mm")
            return

        # Data
        pos = str(stand_data.get('position', '-')).zfill(2)
        mp = str(stand_data.get('playedGames', '-'))
        w = str(stand_data.get('won', '-'))
        d = str(stand_data.get('draw', '-'))
        l = str(stand_data.get('lost', '-'))
        pts = str(stand_data.get('points', '-'))

        # Draw Text
        c_draw.text((cols["POS"], y_pos + 35), pos, font=f_td, fill="white", anchor="mm")
        c_draw.text((cols["TEAM"] + 50, y_pos + 35), team_name, font=f_td, fill="white", anchor="lm")
        c_draw.text((cols["MP"], y_pos + 35), mp, font=f_td, fill="white", anchor="mm")
        c_draw.text((cols["W"], y_pos + 35), w, font=f_td, fill="white", anchor="mm")
        c_draw.text((cols["D"], y_pos + 35), d, font=f_td, fill="white", anchor="mm")
        c_draw.text((cols["L"], y_pos + 35), l, font=f_td, fill="white", anchor="mm")
        c_draw.text((cols["PTS"], y_pos + 35), pts, font=f_score, fill=(255, 215, 0), anchor="mm") # Highlight PTS

        # Paste Tiny Logo
        t_logo = prep_img(logo_path, 40)
        canvas.paste(t_logo, (cols["TEAM"] - 10, y_pos + 15), t_logo)

    # Draw the two rows
    draw_table_row(H_GRAPHIC + 70, h_stand, home['name'], home['logo'])
    draw_table_row(H_GRAPHIC + 150, a_stand, away['name'], away['logo'])

    out_name = f"SCORE_{home['name']}_vs_{away['name']}.png".replace(" ", "_")
    out_path = os.path.join(OUTPUT_DIR, out_name)
    canvas.convert("RGB").save(out_path, quality=95)
    return out_path 

# ===============================
# MAIN RUNNER
# ===============================
print("Fetching Match Data...")
brand_path = download_file(BRAND_LOGO_URL, "brand_logo.png")
posted_scores = load_posted_scores()

# Target date
target_date = datetime.utcnow().strftime("%Y-%m-%d")
# target_date = "2026-02-21" # Uncomment to test with yesterday's JSON!

for league_code, json_filename in LEAGUES.items():
    print(f"\n⚽ Checking league: {league_code} ({json_filename})")
    try:
        matches_req = requests.get(MATCHES_BASE_URL + json_filename)
        teams_req = requests.get(TEAMS_BASE_URL + json_filename)
        standings_req = requests.get(STANDINGS_BASE_URL + json_filename)
        
        if matches_req.status_code != 200 or teams_req.status_code != 200: continue
            
        matches, teams = matches_req.json(), teams_req.json()
        if not isinstance(teams, list): continue
        
        # Parse Standings safely
        stand_list = []
        if standings_req.status_code == 200:
            s_data = standings_req.json()
            if 'standings' in s_data and len(s_data['standings']) > 0:
                stand_list = s_data['standings'][0].get('table', [])

    except Exception as e:
        print(f"⚠️ Error: {e}")
        continue
        
    team_dict = {t.get('id'): t for t in teams if 'id' in t}

    for m in matches:
        # CRITICAL CHECK: Date matches AND Status is Final
        if m.get("Date") == target_date and m.get("Status") == "Final":
            
            # Using _FINAL to separate from pre-match posts
            unique_match_id = f"{m['HomeTeamKey']}_{m['AwayTeamKey']}_{m.get('Date')}_FINAL"
            if unique_match_id in posted_scores:
                print(f"⏩ ALREADY POSTED SCORE: {unique_match_id}. Skipping.")
                continue

            home_t = team_dict.get(m['HomeTeamId'])
            if not home_t: continue

            h_path = download_file(m["HomeTeamLogo"], f"logo_{m['HomeTeamId']}.png")
            a_path = download_file(m["AwayTeamLogo"], f"logo_{m['AwayTeamId']}.png")
            
            league_node = {"name": m.get('RoundName', league_code), "id": "default"}
            if 'runningCompetitions' in home_t and len(home_t['runningCompetitions']) > 0:
                league_node = home_t['runningCompetitions'][0] 
                
            l_path = download_file(league_node.get('emblem', "https://upload.wikimedia.org/wikipedia/commons/4/44/Soccer_ball.svg"), f"league_{league_code}.png")

            # Extract Scores & Standings
            h_score = m.get('HomeTeamScore', 0)
            a_score = m.get('AwayTeamScore', 0)
            h_stand = next((t for t in stand_list if t['team']['id'] == m['HomeTeamId']), None)
            a_stand = next((t for t in stand_list if t['team']['id'] == m['AwayTeamId']), None)

            # 1. Create the Graphic
            img_path = create_score_card(
                {"name": m['HomeTeamKey'], "logo": h_path},
                {"name": m['AwayTeamKey'], "logo": a_path},
                {"name": league_node.get('name', league_code), "logo": l_path},
                brand_path, h_score, a_score, h_stand, a_stand
            )
            
            # 2. Format Highlight Link (Date formatting: 2026-02-21 -> 2026_02_21)
            date_underscores = m.get('Date', '').replace('-', '_')
            highlight_link = f"https://goal4u.netlify.app/highlight/{m['HomeTeamKey']}_v_{m['AwayTeamKey']}_{date_underscores}"
            
            caption = f"""🚨 <b>FULL TIME</b> 🚨

⚽️ {m['HomeTeamKey']} {h_score} - {a_score} {m['AwayTeamKey']}
🏆 {league_node.get('name', league_code)}
📊 Standings Updated!

🔗 <b>Watch Highlights:</b> <a href='{highlight_link}'>Click Here</a>

📺 @goal4utv"""

            # 3. Post!
            print(f"🚀 Posting FINAL SCORE {m['HomeTeamKey']} {h_score}-{a_score} {m['AwayTeamKey']}...")
            if post_to_telegram(img_path, caption):
                save_posted_score(unique_match_id)
                posted_scores.add(unique_match_id)
