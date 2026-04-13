---
description: "Tune visa bot scheduling — adjust check interval, start/end hours, cities, or timezone"
agent: "agent"
---

Adjust the visa bot's scheduling and monitoring configuration in `visa_bot.py`.

The bot monitors **multiple cities** (Istanbul, Ankara) for visa appointment availability. It uses a **status-change notification model**: morning report → silent checks → alert only on status change → noon report.

The user will specify one or more of:

- **Interval**: How often to check the appointment pages (in minutes)
- **Schedule window**: Start and end hours for the checking period
- **Timezone**: Which timezone to use for scheduling
- **Cities**: Add or remove cities from the `URLS` dictionary
- **Alert intensity**: Number of repeated alerts (`ALERT_REPEAT`) on status change to open

Update the default values in the environment variable config section. Keep the `os.getenv()` pattern so values can still be overridden via environment variables at deploy time.

If the schedule window changes, also update:

1. The cron expression in `.github/workflows/bot.yml` (cron is UTC — Istanbul = UTC+3)
2. The `timeout-minutes` in the workflow (should be window duration + 10 min buffer)

After making changes, summarize the new schedule in plain language (e.g., "Bot will check Istanbul and Ankara every 2 minutes between 08:00–12:00 Istanbul time").
