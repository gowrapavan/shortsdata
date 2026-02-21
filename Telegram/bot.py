import os
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from colorthief import ColorThief

# ===============================
# CONFIGURATION
# ===============================
MATCHES_URL = "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/matches/EPL.json"
TEAMS_URL = "https://raw.githubusercontent.com/gowrapavan/shortsdata/main/teams/EPL.json"
BRAND_LOGO_URL = "https://goal4u.netlify.app/assets/img/site-logo/bg-white.png"
OUTPUT_DIR, CACHE_DIR = "output_images", "cache"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# --- TELEGRAM CONFIG ---
# Replace the 'x's with your real bot token before running!
TELEGRAM_TOKEN = "xxxxxxxx:AAFA0cLUm97KVQlT5lITS05U-xxxxxxxxxxxxx"
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
        # Get palette and find a vibrant, dark-ish color
        palette = ct.get_palette(color_count=5)
        color = palette[0]
        # Darken slightly to ensure white text always pops
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
    
    # 1. Colors
    c_home = get_team_color(home['logo'])
    c_away = get_team_color(away['logo'])
    
    # Base canvas (Away color fills the background)
    canvas = Image.new("RGBA", (W, H), (*c_away, 255))
    
    # 2. Dynamic Diagonal Slash (Home color) with Drop Shadow
    # Coordinates for the diagonal cut
    poly_points = [(0, 0), (W//2 + 120, 0), (W//2 - 120, H), (0, H)]
    
    # Create shadow layer
    shadow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_layer)
    # Offset shadow slightly to the right
    shadow_points = [(x+25, y) for x,y in poly_points]
    s_draw.polygon(shadow_points, fill=(0, 0, 0, 180))
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(25)) # Blur the shadow
    
    # Paste shadow, then draw the crisp home color polygon on top
    canvas = Image.alpha_composite(canvas, shadow_layer)
    draw = ImageDraw.Draw(canvas)
    draw.polygon(poly_points, fill=(*c_home, 255))

    # 3. Add Vignette (Darken corners for focus)
    vignette = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    v_draw = ImageDraw.Draw(vignette)
    for i in range(200):
        alpha = int((i / 200) * 120)
        v_draw.rectangle([i, i, W-i, H-i], outline=(0, 0, 0, alpha))
    canvas = Image.alpha_composite(canvas, vignette)

    # 4. Process and Add Images
    def prep_img(path, size):
        img = Image.open(path).convert("RGBA")
        img.thumbnail((size, size), Image.Resampling.LANCZOS)
        return img

    h_img = prep_img(home['logo'], 350)
    a_img = prep_img(away['logo'], 350)
    l_img = prep_img(league['logo'], 100)
    b_img = prep_img(brand_path, 180) # Slightly wider for brand text

    # Logo Positions (Centered in their respective halves)
    canvas.paste(h_img, (W//4 - h_img.width//2, H//2 - h_img.height//2 - 20), h_img)
    canvas.paste(a_img, (3*W//4 - a_img.width//2, H//2 - a_img.height//2 - 20), a_img)
    
    # --- FIX: League Logo Left, Brand Logo Right ---
    draw = ImageDraw.Draw(canvas) # Initialize draw for top layers
    
    # League Logo (Top Left)
    league_x, league_y = 50, 30
    logo_center_x = league_x + (l_img.width // 2)
    logo_center_y = league_y + (l_img.height // 2)
    bg_radius = 55
    # Keep the white background fix
    draw.ellipse([logo_center_x - bg_radius, logo_center_y - bg_radius, 
                  logo_center_x + bg_radius, logo_center_y + bg_radius], fill="white")
    canvas.paste(l_img, (league_x, league_y), l_img)

    # Brand Logo (Top Right)
    brand_x = W - b_img.width - 50
    brand_y = logo_center_y - (b_img.height // 2) # Vertically aligns with the League Logo
    canvas.paste(b_img, (brand_x, brand_y), b_img)

    # 5. Central "VS" Badge
    badge_r = 45
    badge_box = [W//2 - badge_r, H//2 - badge_r - 20, W//2 + badge_r, H//2 + badge_r - 20]
    draw.ellipse(badge_box, fill="white", outline=(20, 20, 20), width=4)

    # 6. Typography
    try:
        f_teams = ImageFont.truetype("arialbd.ttf", 55)
        f_vs = ImageFont.truetype("arialbd.ttf", 45)
        f_time = ImageFont.truetype("arialbd.ttf", 40)
        f_date = ImageFont.truetype("arial.ttf", 25)
    except:
        f_teams = f_vs = f_time = f_date = ImageFont.load_default()

    # Draw VS text inside the badge
    draw.text((W//2, H//2 - 20), "VS", font=f_vs, fill="black", anchor="mm")
    
    # Draw Match Time in a sleek pill beneath the VS badge
    time_box = [W//2 - 80, H//2 + 50, W//2 + 80, H//2 + 100]
    draw.rounded_rectangle(time_box, radius=25, fill=(0, 0, 0, 200), outline=(255,215,0,255), width=2)
    draw.text((W//2, H//2 + 75), time, font=f_time, fill=(255, 215, 0), anchor="mm")

    # Draw Team Names
    def draw_shadow_text(pos, text, font):
        draw.text((pos[0]+3, pos[1]+3), text, font=font, fill=(0,0,0,180), anchor="mm")
        draw.text(pos, text, font=font, fill="white", anchor="mm")

    draw_shadow_text((W//4, H//2 + 220), home['name'].upper(), f_teams)
    draw_shadow_text((3*W//4, H//2 + 220), away['name'].upper(), f_teams)

    # 7. Save the masterpiece
    out_name = f"{home['name']}_vs_{away['name']}.png".replace(" ", "_")
    out_path = os.path.join(OUTPUT_DIR, out_name)
    canvas.convert("RGB").save(out_path, quality=95)
    print(f"🔥 Successfully generated unique design: {out_name}")
    
    return out_path # Ensure we return the path so Telegram can grab it

# ===============================
# MAIN RUNNER
# ===============================
print("Fetching Match Data...")
matches = requests.get(MATCHES_URL).json()
teams = requests.get(TEAMS_URL).json()
team_dict = {t['id']: t for t in teams}

# Download brand logo
brand_path = download_file(BRAND_LOGO_URL, "brand_logo.png")

# Target date for the City vs Newcastle match in your JSON
target_date = "2026-02-21" 

for m in matches:
    if m.get("Date") == target_date:
        home_t = team_dict.get(m['HomeTeamId'])
        if not home_t: continue

        # Downloads
        h_path = download_file(m["HomeTeamLogo"], f"logo_{m['HomeTeamId']}.png")
        a_path = download_file(m["AwayTeamLogo"], f"logo_{m['AwayTeamId']}.png")
        
        # Get League Logo
        league = next((c for c in home_t['runningCompetitions'] if c['name'] == "Premier League"), home_t['runningCompetitions'][0])
        l_path = download_file(league['emblem'], "league_logo.png")

        time_str = m["DateTime"].split("T")[1][:5]

        # 1. Create the graphic
        img_path = create_unique_match_card(
            {"name": m['HomeTeamKey'], "logo": h_path},
            {"name": m['AwayTeamKey'], "logo": a_path},
            {"name": league['name'], "logo": l_path},
            brand_path,
            time_str
        )
        
        # 2. Format your channel's caption
        caption = f"🚨 <b>MATCHDAY</b> 🚨\n\n⚽️ {m['HomeTeamKey']} vs {m['AwayTeamKey']}\n🏆 {league['name']}\n🕒 Kick-off: {time_str} UTC\n\n📺 @goal4utv"

        # 3. Auto-post!
        print(f"🚀 Posting {m['HomeTeamKey']} vs {m['AwayTeamKey']} to Telegram...")
        post_to_telegram(img_path, caption)
