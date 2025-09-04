const fs = require("fs");
const puppeteer = require("puppeteer");

(async () => {
  const browser = await puppeteer.launch({
    headless: "new",
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });
  const page = await browser.newPage();

  await page.goto("https://shahid-koora.com/", { waitUntil: "networkidle2" });

  const matches = await page.$$eval(".card", (cards) =>
    cards.map((card) => {
      const league = card.querySelector(".league")?.innerText.trim() || "";
      const home = card.querySelector(".teams .team:first-child .name")?.innerText.trim() || "";
      const away = card.querySelector(".teams .team:last-child .name")?.innerText.trim() || "";
      const time = card.querySelector(".meta")?.innerText.trim() || "";
      const link = card.querySelector("a.watch-link")?.getAttribute("data-url") || "";
      return { league, home, away, time, url: link };
    })
  );

  fs.writeFileSync("dataurls.json", JSON.stringify(matches, null, 2), "utf-8");

  console.log(`✅ Scraped ${matches.length} matches`);
  await browser.close();
})();
