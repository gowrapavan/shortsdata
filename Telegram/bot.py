import os
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from colorthief import ColorThief

# ===============================
# CONFIGURATION
# ===============================
MATCHES_BASE_URL = "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/matches/"
TEAMS_BASE_URL = "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/"
BRAND_LOGO_URL = "https://goal4u.netlify.app/assets/img/site-logo/bg-white.png"
OUTPUT_DIR, CACHE_DIR = "output_images", "cache"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# Leagues to process
LEAGUES = {
    "EPL": "EPL.json",      # Premier League
    "ESP": "ESP.json",      # Primera Division (La Liga)
    "DEB": "DEB.json",     # Bundesliga
    "DED": "DED.json",     # Eredivisie
    "ITSA": "ITSA.json",     # Serie A
    "FRL1": "FRL1.json",    # Ligue 1
    "BSA": "BSA.json",     # Campeonato Brasileiro Série A
    "ELC": "ELC.json",     # Championship
    "POR": "POR.json",     # Primeira Liga
    "UCL": "UCL.json",      # UEFA Champions League
    "WC": "WC.json",       # FIFA World Cup
    "MLS": "MLS.json"      # Major League Soccer
}

# --- TELEGRAM CONFIG ---
TELEGRAM_TOKEN = "8264321603:AAFA0cLUm97KVQlT5lITS05U-FLNSpmhCYg"
TELEGRAM_CHAT_ID = "@goal4utv"

# ===============================
# UTILITIES
# ===============================
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

# --- TELEGRAM AUTO-POSTER ---
def post_to_telegram(image_path, caption):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    with open(image_path, "rb") as photo:
        response = requests.post(
            url,
            data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption, "parse_mode": "HTML"},
            files={"photo": photo}
        )
    print("📲 Telegram Post Status:", response.status_code, response.text)

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

    def prep_img(path, size):
        img = Image.open(path).convert("RGBA")
        img.thumbnail((size, size), Image.Resampling.LANCZOS)
        return img

    h_img = prep_img(home['logo'], 350)
    a_img = prep_img(away['logo'], 350)
    l_img = prep_img(league['logo'], 100)
    b_img = prep_img(brand_path, 180) 

    canvas.paste(h_img, (W//4 - h_img.width//2, H//2 - h_img.height//2 - 20), h_img)
    canvas.paste(a_img, (3*W//4 - a_img.width//2, H//2 - a_img.height//2 - 20), a_img)
    
    draw = ImageDraw.Draw(canvas) 
    
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
        f_teams = ImageFont.truetype("arialbd.ttf", 55)
        f_vs = ImageFont.truetype("arialbd.ttf", 45)
        f_time = ImageFont.truetype("arialbd.ttf", 40)
        f_date = ImageFont.truetype("arial.ttf", 25)
    except:
        f_teams = f_vs = f_time = f_date = ImageFont.load_default()

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

# Download brand logo once
brand_path = download_file(BRAND_LOGO_URL, "brand_logo.png")

# Target date for matches
target_date = "2026-02-21" 

# Loop through every league in the dictionary
for league_code, json_filename in LEAGUES.items():
    print(f"\n⚽ Checking league: {league_code} ({json_filename})")
    
    try:
        matches = requests.get(MATCHES_BASE_URL + json_filename).json()
        teams = requests.get(TEAMS_BASE_URL + json_filename).json()
    except Exception as e:
        print(f"⚠️ Skipping {league_code} - Data not found or error: {e}")
        continue
        
    team_dict = {t['id']: t for t in teams}

    for m in matches:
        if m.get("Date") == target_date:
            home_t = team_dict.get(m['HomeTeamId'])
            if not home_t: continue

            # Downloads
            h_path = download_file(m["HomeTeamLogo"], f"logo_{m['HomeTeamId']}.png")
            a_path = download_file(m["AwayTeamLogo"], f"logo_{m['AwayTeamId']}.png")
            
            # Find the correct league logo from the team's running competitions
            league_node = home_t['runningCompetitions'][0] # Default fallback
            for comp in home_t['runningCompetitions']:
                if comp.get('name') == m.get('RoundName'):
                    league_node = comp
                    break
            
            l_path = download_file(league_node['emblem'], f"league_{league_node['id']}.png")

            time_str = m["DateTime"].split("T")[1][:5]
            game_id = m.get("GameId", "Unknown")

            # 1. Create the graphic
            img_path = create_unique_match_card(
                {"name": m['HomeTeamKey'], "logo": h_path},
                {"name": m['AwayTeamKey'], "logo": a_path},
                {"name": league_node['name'], "logo": l_path},
                brand_path,
                time_str
            )
            
            # 2. Format your channel's caption with the Live Stream Link
            live_link = f"https://goal4utv.netlify.app/match/{game_id}"
            
            caption = f"""🚨 <b>MATCHDAY</b> 🚨

⚽️ {m['HomeTeamKey']} vs {m['AwayTeamKey']}
🏆 {league_node['name']}
🕒 Kick-off: {time_str} UTC

🔗 <b>Watch Live:</b> <a href='{live_link}'>Click Here</a>

📺 @goal4utv"""

            # 3. Auto-post!
            print(f"🚀 Posting {m['HomeTeamKey']} vs {m['AwayTeamKey']} to Telegram...")
            post_to_telegram(img_path, caption)
