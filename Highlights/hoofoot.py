import asyncio
import json
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from playwright.async_api import async_playwright
# Add this import (requires playwright-stealth in requirements)
from playwright_stealth import stealth_async 

BASE_URL = "https://hoofoot.com/"
OUTPUT_FILE = "Highlights/hoofoot.json"

async def fetch_hoofoot():
    results = []
    async with async_playwright() as p:
        # 1. Launch with extra arguments to look more human
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )

        # 2. Use a modern, randomized User-Agent
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )

        page = await context.new_page()
        
        # 3. Apply stealth to hide Playwright
        await stealth_async(page)

        print("🌐 Opening home page…")
        # 4. Use 'networkidle' to ensure Cloudflare challenge finishes
        await page.goto(BASE_URL + "?home", wait_until="networkidle", timeout=90000)

        # Rest of your BeautifulSoup logic remains the same...

        # Let JS render
        await page.wait_for_timeout(5000)

        home_html = await page.content()
        soup = BeautifulSoup(home_html, "html.parser")

        matches = []

        for a in soup.select('a[href*="?match="]'):
            title_tag = a.find("h2")
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            match_url = urljoin(BASE_URL, a.get("href"))

            matches.append({
                "title": title,
                "match_url": match_url
            })

        print(f"✅ Found {len(matches)} matches")

        for i, m in enumerate(matches, 1):
            print(f"[{i}/{len(matches)}] Fetching:", m["title"])

            try:
                await page.goto(m["match_url"], timeout=60000)
                await page.wait_for_timeout(4000)

                match_html = await page.content()
                match_soup = BeautifulSoup(match_html, "html.parser")

                embed_url = ""

                player = match_soup.find("div", id="player")
                if player:
                    a = player.find("a", href=True)
                    if a:
                        embed_url = a["href"]

                results.append({
                    "title": m["title"],
                    "match_url": m["match_url"],
                    "embed_url": embed_url
                })

                await page.wait_for_timeout(2000)

            except Exception as e:
                print("❌ Failed:", m["title"], e)

        await browser.close()

    return results


if __name__ == "__main__":
    os.makedirs("Highlights", exist_ok=True)

    data = asyncio.run(fetch_hoofoot())

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved {OUTPUT_FILE} with {len(data)} matches")
