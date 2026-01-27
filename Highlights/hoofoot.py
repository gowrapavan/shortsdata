import asyncio
import json
import os
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async 

BASE_URL = "https://hoofoot.com/"
OUTPUT_FILE = "Highlights/hoofoot.json"

async def fetch_hoofoot():
    # 1. Load existing data to skip duplicates
    existing_data = []
    existing_ids = set()
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                existing_ids = {item["id"] for item in existing_data if "id" in item}
        except Exception as e:
            print(f"⚠️ Could not load existing JSON: {e}")

    new_results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()
        await stealth_async(page)

        print("🌐 Checking for new matches on Hoofoot...")
        try:
            await page.goto(BASE_URL + "?home", wait_until="networkidle", timeout=90000)
            await page.wait_for_timeout(8000) 
            
            home_html = await page.content()
            soup = BeautifulSoup(home_html, "html.parser")
            
            found_anchors = soup.select('a[href*="?match="]')
            matches_to_scrape = []

            for a in found_anchors:
                href = a.get("href")
                # Extract ID from href: ?match=Everton_v_Leeds_2026_01_26
                parsed_url = urlparse(href)
                match_id = parse_qs(parsed_url.query).get("match", [None])[0]
                
                if not match_id or match_id in existing_ids:
                    continue # SKIP logic

                title_tag = a.find("h2")
                if title_tag:
                    matches_to_scrape.append({
                        "id": match_id,
                        "title": title_tag.get_text(strip=True),
                        "match_url": urljoin(BASE_URL, href)
                    })

            print(f"🔎 Found {len(matches_to_scrape)} NEW matches to scrape.")

            for i, m in enumerate(matches_to_scrape, 1):
                print(f"[{i}/{len(matches_to_scrape)}] Fetching embed for: {m['title']}")
                try:
                    await page.goto(m["match_url"], wait_until="domcontentloaded", timeout=60000)
                    await page.wait_for_timeout(3000)

                    match_soup = BeautifulSoup(await page.content(), "html.parser")
                    embed_url = ""
                    player = match_soup.find("div", id="player")
                    if player:
                        a_tag = player.find("a", href=True)
                        if a_tag: embed_url = a_tag["href"]
# Extract the date from the ID (e.g., Juventus_v_Napoli_2026_01_25)
                    # We take the last 10 characters or split by underscores
                    parts = m["id"].split('_')
                    # Joins the last 3 parts: '2026', '01', '25' -> '2026_01_25'
                    match_date = "_".join(parts[-3:]) 

                    new_results.append({
                        "id": m["id"],
                        "title": m["title"],
                        "match_url": m["match_url"],
                        "embed_url": embed_url,
                        "match_date": match_date  # Now shows 2026_01_25
                    })
                except Exception as e:
                    print(f"❌ Failed to fetch details for {m['id']}: {e}")

        except Exception as e:
            print(f"❌ Main page load failed: {e}")

        await browser.close()

    # Combine old data with new data (Newest first)
    final_data = new_results + existing_data
    # Optional: Limit total matches kept (e.g., keep last 100)
    return final_data[:100] 

if __name__ == "__main__":
    os.makedirs("Highlights", exist_ok=True)
    updated_data = asyncio.run(fetch_hoofoot())
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(updated_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Sync Complete. Total matches in database: {len(updated_data)}")
