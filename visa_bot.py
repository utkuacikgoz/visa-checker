import os
import asyncio
from datetime import datetime

import pytz
from telegram import Bot
from telegram.error import TelegramError
from pyppeteer import launch

# === Config ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
URL = os.getenv("URL", "https://appointment.as-visa.com/tr/istanbul-bireysel-basvuru")
TIMEZONE = os.getenv("TIMEZONE", "Europe/Istanbul")
START_HOUR = int(os.getenv("START_HOUR", "10"))  # 10 AM
END_HOUR = int(os.getenv("END_HOUR", "12"))      # 12 PM (noon)


async def take_screenshot(url, filename="screenshot.png"):
    browser = await launch(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
    )
    page = await browser.newPage()
    await page.setViewport({"width": 1366, "height": 768})
    await page.goto(url, {"waitUntil": "networkidle2", "timeout": 60000})
    await page.screenshot({"path": filename, "fullPage": True})
    await browser.close()
    return filename


def is_within_schedule():
    """Check if current Istanbul time is between 10:00 and 12:00."""
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    return START_HOUR <= now.hour < END_HOUR


async def main():
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Missing BOT_TOKEN or CHAT_ID. Set them as environment variables.")
        return

    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

    if not is_within_schedule():
        print(f"💤 [{now}] Outside schedule (10:00–12:00 Istanbul). Skipping.")
        return

    bot = Bot(BOT_TOKEN)

    try:
        filename = await take_screenshot(URL)
        with open(filename, "rb") as f:
            await bot.send_photo(
                chat_id=CHAT_ID,
                photo=f,
                caption=f"📸 Visa Appointment Page\n🕐 {now}\n🔗 {URL}",
            )
        print(f"✅ [{now}] Screenshot sent.")
    except TelegramError as e:
        print(f"❌ [{now}] Telegram error: {e}")
    except Exception as e:
        print(f"❌ [{now}] Unexpected error: {e}")


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
