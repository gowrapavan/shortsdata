import asyncio
import json
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from playwright.async_api import async_playwright

BASE_URL = "https://hoofoot.com/"
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "hoofoot.json")


async def fetch_hoofoot():
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless="new",  # more stable in CI
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled"
            ]
        )

        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="en-US"
        )

        page = await context.new_page()

        print("🌐 Opening home page…")
        await page.goto(BASE_URL + "?home", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)  # allow JS to render

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
                await page.goto(m["match_url"], wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(4000)

                embed_url = ""

                # Try iframe first (more reliable)
                iframe = await page.query_selector("iframe")
                if iframe:
                    embed_url = await iframe.get_attribute("src")

                # Fallback to HTML parsing
                if not embed_url:
                    match_html = await page.content()
                    match_soup = BeautifulSoup(match_html, "html.parser")

                    player = match_soup.find("div", id="player")
                    if player:
                        a_tag = player.find("a", href=True)
                        if a_tag:
                            embed_url = a_tag["href"]

                results.append({
                    "title": m["title"],
                    "match_url": m["match_url"],
                    "embed_url": embed_url or ""
                })

                await page.wait_for_timeout(2000)

            except Exception as e:
                print("❌ Failed:", m["title"], e)

        await browser.close()

    return results


if __name__ == "__main__":
    data = asyncio.run(fetch_hoofoot())

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved hoofoot.json with {len(data)} matches")
