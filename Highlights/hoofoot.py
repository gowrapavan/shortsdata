import asyncio
import json
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async 

BASE_URL = "https://hoofoot.com/"
OUTPUT_FILE = "Highlights/hoofoot.json"

async def fetch_hoofoot():
    # 1. Load existing data
    existing_data = []
    existing_ids = set()
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                existing_ids = {item["id"] for item in existing_data if "id" in item}
        except Exception as e:
            print(f"⚠️ Load error: {e}")

    new_results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()
        await stealth_async(page)

        print("🌐 Checking for new matches...")
        try:
            await page.goto(BASE_URL + "?home", wait_until="networkidle", timeout=90000)
            await page.wait_for_timeout(8000) 
            
            soup = BeautifulSoup(await page.content(), "html.parser")
            found_anchors = soup.select('a[href*="?match="]')
            
            matches_to_scrape = []
            for a in found_anchors:
                href = a.get("href")
                # Extract ID from ?match=Everton_v_Leeds_2026_01_26
                match_id = parse_qs(urlparse(href).query).get("match", [None])[0]
                
                if not match_id or match_id in existing_ids:
                    continue 

                title_tag = a.find("h2")
                if title_tag:
                    matches_to_scrape.append({
                        "id": match_id,
                        "title": title_tag.get_text(strip=True),
                        "match_url": urljoin(BASE_URL, href)
                    })

            print(f"🔎 Found {len(matches_to_scrape)} NEW matches.")

            for m in matches_to_scrape:
                try:
                    print(f"🚀 Scraping: {m['id']}")
                    await page.goto(m["match_url"], wait_until="domcontentloaded", timeout=60000)
                    await page.wait_for_timeout(3000)

                    match_soup = BeautifulSoup(await page.content(), "html.parser")
                    embed_url = ""
                    player = match_soup.find("div", id="player")
                    if player:
                        a_tag = player.find("a", href=True)
                        if a_tag: embed_url = a_tag["href"]

                    # DATE LOGIC: Extract date from ID (last 3 segments)
                    # Example: Juventus_v_Napoli_2026_01_25 -> 2026_01_25
                    parts = m["id"].split('_')
                    match_date = "_".join(parts[-3:])

                    new_results.append({
                        "id": m["id"],
                        "title": m["title"],
                        "match_url": m["match_url"],
                        "embed_url": embed_url,
                        "match_date": match_date
                    })
                except Exception as e:
                    print(f"❌ Failed {m['id']}: {e}")

        finally:
            await browser.close()

    # Place NEW matches at the top of the list
    return new_results + existing_data

if __name__ == "__main__":
    os.makedirs("Highlights", exist_ok=True)
    updated_data = asyncio.run(fetch_hoofoot())
    
    # Save the file (Limit to last 150 matches to keep JSON small)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(updated_data[:150], f, indent=2, ensure_ascii=False)
    
    print(f"✅ Finished. {len(updated_data)} total matches in JSON.")
