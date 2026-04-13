# visa-appointment-screenshot-bot

A Telegram bot that monitors the [AS Visa appointment pages](https://appointment.as-visa.com) for **Istanbul** and **Ankara**, detects when appointments open, and sends loud alerts to your Telegram.

## How it works

- Runs daily **08:00 – 12:00 (noon) Istanbul time** via GitHub Actions.
- Checks both Istanbul and Ankara appointment pages every **~2 minutes** with randomized timing (±90 s jitter) to avoid detection.
- **Morning report (8 AM):** Sends a silent screenshot of each city's current status.
- **Silent checks:** Every ~2 min, checks both cities — only logs to console, no Telegram spam.
- **Status change alert:** If a city's status changes (closed → open or open → closed), sends an immediate Telegram notification. If appointments **open**, blasts loud photo + text alerts.
- **Noon report (12 PM):** Sends a final silent screenshot showing end-of-window status.

## Environment Variables

| Variable           | Required | Default                                                        | Description                                     |
| ------------------ | -------- | -------------------------------------------------------------- | ----------------------------------------------- |
| `BOT_TOKEN`        | Yes      | –                                                              | Telegram Bot API token                          |
| `CHAT_ID`          | Yes      | –                                                              | Telegram chat/channel ID to send screenshots to |
| `URL_ISTANBUL`     | No       | `https://appointment.as-visa.com/tr/istanbul-bireysel-basvuru` | Istanbul appointment page URL                   |
| `URL_ANKARA`       | No       | `https://appointment.as-visa.com/tr/ankara-bireysel-basvuru`   | Ankara appointment page URL                     |
| `TIMEZONE`         | No       | `Europe/Istanbul`                                              | Timezone for the schedule                       |
| `START_HOUR`       | No       | `8`                                                            | Hour to start checking (24h format)             |
| `END_HOUR`         | No       | `12`                                                           | Hour to stop checking (24h format)              |
| `INTERVAL_MINUTES` | No       | `2`                                                            | Minutes between each check                      |
| `TELEGRAM_USER`    | No       | –                                                              | Your @username for alert mentions               |
| `ALERT_REPEAT`     | No       | `2`                                                            | Number of photo alerts on status change to open |

## Setup

1. **GitHub Secrets** — add `BOT_TOKEN`, `CHAT_ID`, and optionally `TELEGRAM_USER` in your repo → Settings → Secrets and variables → Actions.
2. **Push to main** — the Actions workflow (cron `0 5 * * *` UTC = 08:00 Istanbul) handles scheduling automatically.
3. **Manual trigger** — you can also run it on demand via the "Run workflow" button in Actions.

### Local test

```bash
pip install -r requirements.txt
export BOT_TOKEN="your-bot-token"
export CHAT_ID="your-chat-id"
python visa_bot.py
```
