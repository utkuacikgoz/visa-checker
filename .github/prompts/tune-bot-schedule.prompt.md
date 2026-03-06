---
description: "Tune visa bot scheduling — adjust check interval, start/end hours, or timezone"
agent: "agent"
---

Adjust the visa bot's scheduling configuration in [visa_bot.py](../../visa_bot.py).

The user will specify one or more of:

- **Interval**: How often to check the appointment page (in minutes)
- **Schedule window**: Start and end hours for the checking period
- **Timezone**: Which timezone to use for scheduling

Update the default values in the environment variable config section. Keep the `os.getenv()` pattern so values can still be overridden via environment variables at deploy time.

After making changes, summarize the new schedule in plain language (e.g., "Bot will check every 2 minutes between 10:00–12:00 Istanbul time").
