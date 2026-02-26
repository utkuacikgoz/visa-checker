# visa-appointment-screenshot-bot

A Telegram bot that automatically takes screenshots of the [AS Visa Istanbul appointment page](https://appointment.as-visa.com/tr/istanbul-bireysel-basvuru) and sends them to a Telegram channel.

## How it works

- Runs **every 10 minutes** between **10:00 AM and 12:00 PM (noon)** Istanbul time via GitHub Actions cron.
- Each run takes a full-page screenshot of the visa appointment website using a headless Chromium browser.
- Sends the screenshot to the configured Telegram channel with a timestamp.
- Outside the schedule window, the run exits silently.

## Environment Variables

| Variable     | Required | Default                                                        | Description                                     |
| ------------ | -------- | -------------------------------------------------------------- | ----------------------------------------------- |
| `BOT_TOKEN`  | Yes      | –                                                              | Telegram Bot API token                          |
| `CHAT_ID`    | Yes      | –                                                              | Telegram chat/channel ID to send screenshots to |
| `URL`        | No       | `https://appointment.as-visa.com/tr/istanbul-bireysel-basvuru` | Target URL to screenshot                        |
| `TIMEZONE`   | No       | `Europe/Istanbul`                                              | Timezone for the schedule                       |
| `START_HOUR` | No       | `10`                                                           | Hour to start (24h format)                      |
| `END_HOUR`   | No       | `12`                                                           | Hour to stop (24h format)                       |

## Setup

1. **GitHub Secrets** — add `BOT_TOKEN` and `CHAT_ID` in your repo → Settings → Secrets.
2. **Push to main** — the Actions workflow (`*/10 7-8 * * *` UTC) handles scheduling automatically.
3. **Manual trigger** — you can also run it on demand via the "Run workflow" button in Actions.

### Local test

```bash
pip install -r requirements.txt
export BOT_TOKEN="your-bot-token"
export CHAT_ID="your-chat-id"
python visa_bot.py
```
