import os
import asyncio
import random
import signal
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import Bot
from telegram.error import TelegramError, TimedOut, NetworkError
from pyppeteer import launch

# === Config ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
URLS = {
    "Istanbul": os.getenv("URL_ISTANBUL", "https://appointment.as-visa.com/tr/istanbul-bireysel-basvuru"),
    "Ankara": os.getenv("URL_ANKARA", "https://appointment.as-visa.com/tr/ankara-bireysel-basvuru"),
}
TIMEZONE = os.getenv("TIMEZONE", "Europe/Istanbul")
INTERVAL_MINUTES = int(os.getenv("INTERVAL_MINUTES", "2"))
START_HOUR = int(os.getenv("START_HOUR", "8"))    # 8 AM
END_HOUR = int(os.getenv("END_HOUR", "12"))       # 12 PM (noon)
TELEGRAM_USER = os.getenv("TELEGRAM_USER", "")
ALERT_REPEAT = int(os.getenv("ALERT_REPEAT", "2"))

# Telegram send timeouts (seconds) — keep as low as possible
TG_CONNECT_TIMEOUT = 5
TG_READ_TIMEOUT = 10
TG_WRITE_TIMEOUT = 10

# State tracking per city
last_status = {}  # city -> bool (True = open, False = closed)


async def take_screenshot_and_detect(url, filename="screenshot.png"):
    """Take a screenshot and detect if the appointment form is available.
    Returns (filename, form_detected). Kills browser process on failure to prevent leaks."""
    browser = None
    try:
        browser = await launch(
            headless=True,
            args=[
                "--no-sandbox", "--disable-setuid-sandbox",
                "--disable-dev-shm-usage", "--disable-gpu",
                "--single-process",  # reduces child processes
            ],
        )
        page = await browser.newPage()
        await page.setViewport({"width": 1366, "height": 768})
        await page.goto(url, {"waitUntil": "networkidle2", "timeout": 60000})
        await asyncio.sleep(2)
        await page.screenshot({"path": filename, "fullPage": True})
        form_detected = await page.evaluate('''
            () => {
                const inputs = document.querySelectorAll('form input, form select, form textarea');
                return inputs.length > 0;
            }
        ''')
        return filename, form_detected
    finally:
        if browser:
            try:
                await asyncio.wait_for(browser.close(), timeout=10)
            except Exception:
                # Force-kill the Chromium process if graceful close fails
                pid = browser.process.pid
                try:
                    os.kill(pid, signal.SIGKILL)
                    print(f"⚠️ Force-killed browser process {pid}")
                except OSError:
                    pass


def is_within_schedule():
    """Check if current Istanbul time is within 8 AM – 12 PM (noon)."""
    now = datetime.now(ZoneInfo(TIMEZONE))
    return START_HOUR <= now.hour < END_HOUR


async def _tg_retry(coro_fn, retries=2):
    """Retry a Telegram send on transient errors."""
    for attempt in range(retries + 1):
        try:
            return await coro_fn()
        except (TimedOut, NetworkError) as e:
            if attempt < retries:
                wait = 1 * (attempt + 1)
                print(f"⚠️ Telegram send failed ({e}), retrying in {wait}s…")
                await asyncio.sleep(wait)
            else:
                raise


async def send_photo_fast(bot, photo_bytes, caption, silent=True):
    """Send a photo (bytes) with optimized timeouts + retry."""
    async def _send():
        await bot.send_photo(
            chat_id=CHAT_ID, photo=photo_bytes, caption=caption,
            disable_notification=silent,
            connect_timeout=TG_CONNECT_TIMEOUT,
            read_timeout=TG_READ_TIMEOUT,
            write_timeout=TG_WRITE_TIMEOUT,
        )
    await _tg_retry(_send)


async def send_msg_fast(bot, text, silent=False):
    """Send a text message with optimized timeouts + retry."""
    async def _send():
        await bot.send_message(
            chat_id=CHAT_ID, text=text,
            disable_notification=silent,
            connect_timeout=TG_CONNECT_TIMEOUT,
            read_timeout=TG_READ_TIMEOUT,
            write_timeout=TG_WRITE_TIMEOUT,
        )
    await _tg_retry(_send)


async def send_loud_alert(bot, city, url, filename, now_str):
    """Blast extremely loud alerts — status changed to OPEN."""
    mention = f"@{TELEGRAM_USER}" if TELEGRAM_USER else ""
    caption = (
        f"🚨🚨🚨🚨🚨 {city.upper()} APPOINTMENTS OPEN!!! 🚨🚨🚨🚨🚨\n"
        f"‼️‼️‼️ GO GO GO GO GO ‼️‼️‼️\n"
        f"🕐 {now_str}\n"
        f"🔗 {url}\n"
        f"{mention} APPLY NOW!!!"
    )
    # Read file once into memory — avoids repeated I/O and race conditions
    with open(filename, "rb") as f:
        photo_bytes = f.read()

    async def _send_photo_alert():
        await _tg_retry(lambda: bot.send_photo(
            chat_id=CHAT_ID, photo=photo_bytes, caption=caption,
            disable_notification=False,
            connect_timeout=TG_CONNECT_TIMEOUT,
            read_timeout=TG_READ_TIMEOUT,
            write_timeout=TG_WRITE_TIMEOUT,
        ))

    # Send first photo immediately, then blast the rest + text concurrently
    await _send_photo_alert()
    tasks = [_send_photo_alert() for _ in range(ALERT_REPEAT - 1)]
    urgent = [
        f"🔴🔴🔴 {city.upper()} VISA APPOINTMENTS OPEN!!! 🔴🔴🔴\n{url}\n{mention}",
        f"⚡⚡⚡ {city.upper()} — APPLY RIGHT NOW!!! ⚡⚡⚡\n{url}\n{mention}",
        f"🆘🆘🆘 {city.upper()} SLOT AVAILABLE — HURRY!!! 🆘🆘🆘\n{url}\n{mention}",
    ]
    tasks += [send_msg_fast(bot, text, silent=False) for text in urgent]
    await asyncio.gather(*tasks)
    print(f"🚨 [{now_str}] {city}: OPEN — {ALERT_REPEAT} photo + 3 text alerts sent!")


async def check_city(bot, city, url, force_notify=False):
    """Check one city. Notifies only on status change or when forced (morning / noon)."""
    now_str = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")
    filename = f"screenshot_{city.lower()}.png"

    try:
        _, form_detected = await take_screenshot_and_detect(url, filename)

        # Read screenshot bytes once — used by all send paths
        with open(filename, "rb") as f:
            photo_bytes = f.read()

        prev_status = last_status.get(city)
        status_changed = prev_status is not None and prev_status != form_detected
        should_notify = force_notify or status_changed

        if status_changed and form_detected:
            # 🚨 Status CHANGED to OPEN — loud as fuck
            await send_loud_alert(bot, city, url, filename, now_str)
        elif status_changed and not form_detected:
            # Was open → now closed — notify with sound
            await send_photo_fast(
                bot, photo_bytes,
                caption=f"🔔 {city} — NOW CLOSED ❌\n🕐 {now_str}\n🔗 {url}",
                silent=False,
            )
            print(f"🔔 [{now_str}] {city}: CLOSED (was open)")
        elif force_notify:
            # Morning / noon report — silent
            status_text = "OPEN ✅" if form_detected else "CLOSED ❌"
            await send_photo_fast(
                bot, photo_bytes,
                caption=f"📸 {city} — {status_text}\n🕐 {now_str}\n🔗 {url}",
                silent=True,
            )
            print(f"📸 [{now_str}] {city}: {status_text} (scheduled report)")
        else:
            # No change — silent log only
            status_text = "OPEN" if form_detected else "CLOSED"
            print(f"🔇 [{now_str}] {city}: {status_text} (no change)")

        last_status[city] = form_detected
        return form_detected

    except Exception as e:
        print(f"❌ [{now_str}] {city} error: {e}")
        return None
    finally:
        if os.path.exists(filename):
            os.remove(filename)


async def check_all_cities(bot, force_notify=False):
    """Check all cities sequentially."""
    for city, url in URLS.items():
        await check_city(bot, city, url, force_notify=force_notify)


async def main():
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Missing BOT_TOKEN or CHAT_ID. Set them as environment variables.")
        return

    bot = Bot(BOT_TOKEN)
    tz = ZoneInfo(TIMEZONE)

    print(f"🚀 Bot started — checking every ~{INTERVAL_MINUTES} min "
          f"({START_HOUR:02d}:00–{END_HOUR:02d}:00 {TIMEZONE})")
    print(f"📍 Cities: {', '.join(URLS.keys())}")
    print(f"📢 Alerts: morning report → silent checks → notify on status change → noon report")

    # Wait for schedule window if started outside hours
    while not is_within_schedule():
        now = datetime.now(tz)
        print(f"⏳ [{now.strftime('%H:%M')}] Outside schedule (before {START_HOUR:02d}:00). Waiting…")
        await asyncio.sleep(60)

    # === Morning report — always notify ===
    print("🌅 Morning check — sending first report…")
    await check_all_cities(bot, force_notify=True)

    # === Main loop — silent unless status changes ===
    while is_within_schedule():
        jitter = random.uniform(-90, 90)  # ±90 s randomization to avoid detection
        sleep_secs = max(60, INTERVAL_MINUTES * 60 + jitter)
        print(f"⏳ Next check in {sleep_secs:.0f}s (~{sleep_secs / 60:.1f} min)")
        await asyncio.sleep(sleep_secs)

        if not is_within_schedule():
            break
        await check_all_cities(bot, force_notify=False)

    # === Noon report — always notify ===
    now = datetime.now(tz)
    print(f"☀️ [{now.strftime('%H:%M')}] End of window — sending final screenshots…")
    await check_all_cities(bot, force_notify=True)
    print("🏁 Done for today.")


if __name__ == "__main__":
    asyncio.run(main())
