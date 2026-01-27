import asyncio
import json
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from playwright.async_api import async_playwright

BASE_URL = "https://hoofoot.com/"
OUTPUT_FILE = "Highlights/hoofoot.json"


async def fetch_hoofoot():
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="en-US"
        )

        page = await context.new_page()

        print("🌐 Opening home page…")
        await page.goto(BASE_URL + "?home", timeout=60000)

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
