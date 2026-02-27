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
INTERVAL_MINUTES = int(os.getenv("INTERVAL_MINUTES", "10"))
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
    """Check if current Istanbul time is before END_HOUR."""
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    return now.hour < END_HOUR


async def send_screenshot(bot):
    """Take a screenshot and send it to the Telegram channel."""
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

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


async def main():
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Missing BOT_TOKEN or CHAT_ID. Set them as environment variables.")
        return

    bot = Bot(BOT_TOKEN)
    tz = pytz.timezone(TIMEZONE)

    print(f"🚀 Bot started — will screenshot every {INTERVAL_MINUTES} min "
          f"until {END_HOUR:02d}:00 ({TIMEZONE})")

    # First screenshot immediately
    await send_screenshot(bot)

    # Then loop every INTERVAL_MINUTES until the schedule window ends
    while is_within_schedule():
        print(f"⏳ Sleeping {INTERVAL_MINUTES} minutes...")
        await asyncio.sleep(INTERVAL_MINUTES * 60)

        # Check again after sleep — might have passed END_HOUR
        if not is_within_schedule():
            break
        await send_screenshot(bot)

    now = datetime.now(tz).strftime("%H:%M:%S")
    print(f"🏁 [{now}] Schedule window ended. Done.")


if __name__ == "__main__":
    asyncio.run(main())
