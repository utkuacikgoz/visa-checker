import os
import asyncio
import random
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
INTERVAL_MINUTES = int(os.getenv("INTERVAL_MINUTES", "2"))
START_HOUR = int(os.getenv("START_HOUR", "10"))  # 10 AM
END_HOUR = int(os.getenv("END_HOUR", "12"))      # 12 PM (noon)
TELEGRAM_USER = os.getenv("TELEGRAM_USER", "")  # Your @username for mentions
ALERT_REPEAT = int(os.getenv("ALERT_REPEAT", "3"))  # How many alert messages to send


async def take_screenshot_and_detect(url, filename="screenshot.png"):
    """Take a screenshot and detect if the appointment form is available."""
    browser = await launch(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
    )
    page = await browser.newPage()
    await page.setViewport({"width": 1366, "height": 768})
    await page.goto(url, {"waitUntil": "networkidle2", "timeout": 60000})
    await page.screenshot({"path": filename, "fullPage": True})

    # Detect form elements — when appointments are open the page has input/select fields
    form_detected = await page.evaluate('''
        () => {
            const inputs = document.querySelectorAll('form input, form select, form textarea');
            return inputs.length > 0;
        }
    ''')

    await browser.close()
    return filename, form_detected


def is_within_schedule():
    """Check if current Istanbul time is before END_HOUR."""
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    return now.hour < END_HOUR


async def send_screenshot(bot):
    """Take a screenshot, detect form availability, and send to Telegram."""
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

    try:
        filename, form_detected = await take_screenshot_and_detect(URL)

        if form_detected:
            # 🚨 Appointments are OPEN — send loud alerts
            mention = f"@{TELEGRAM_USER}" if TELEGRAM_USER else ""
            caption = (
                f"🚨🚨🚨 APPOINTMENTS OPEN! 🚨🚨🚨\n"
                f"🕐 {now}\n"
                f"🔗 {URL}\n"
                f"{mention} GO NOW!"
            )
            for i in range(ALERT_REPEAT):
                with open(filename, "rb") as f:
                    await bot.send_photo(
                        chat_id=CHAT_ID, photo=f, caption=caption,
                        disable_notification=False,  # 🔊 Sound ON
                    )
                if i < ALERT_REPEAT - 1:
                    await asyncio.sleep(1)
            print(f"🚨 [{now}] FORM DETECTED — {ALERT_REPEAT} alerts sent!")
        else:
            # Regular update — appointments still closed
            with open(filename, "rb") as f:
                await bot.send_photo(
                    chat_id=CHAT_ID,
                    photo=f,
                    caption=f"📸 Visa Appointment Page (closed)\n🕐 {now}\n🔗 {URL}",
                    disable_notification=True,  # 🔇 Silent — no ping for routine checks
                )
            print(f"✅ [{now}] Screenshot sent (closed).")

        return form_detected
    except TelegramError as e:
        print(f"❌ [{now}] Telegram error: {e}")
    except Exception as e:
        print(f"❌ [{now}] Unexpected error: {e}")
    return False


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

    # Then loop every INTERVAL_MINUTES (±30s jitter) until the schedule window ends
    while is_within_schedule():
        jitter = random.uniform(-30, 30)
        sleep_secs = INTERVAL_MINUTES * 60 + jitter
        print(f"⏳ Sleeping {sleep_secs:.0f}s (~{INTERVAL_MINUTES} min + jitter)...")
        await asyncio.sleep(sleep_secs)

        # Check again after sleep — might have passed END_HOUR
        if not is_within_schedule():
            break
        await send_screenshot(bot)

    now = datetime.now(tz).strftime("%H:%M:%S")
    print(f"🏁 [{now}] Schedule window ended. Done.")


if __name__ == "__main__":
    asyncio.run(main())
