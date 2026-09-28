# Scheduling (launchd)

Two agents make the pipeline fully unattended on the Mac mini:

- `com.malgcheong.orchestrator` — runs the daily digest at 06:00 (pauses at approval).
- `com.malgcheong.orchestrator-bot` — the always-on Discord approval bot.

Enable them **after** the Discord webhook/bot is configured (see
[discord-setup.md](discord-setup.md)); until then a run pauses with nowhere to send
the preview.

## Install

```bash
cp scripts/com.malgcheong.orchestrator.plist      ~/Library/LaunchAgents/
cp scripts/com.malgcheong.orchestrator-bot.plist  ~/Library/LaunchAgents/

# daily run at 06:00
launchctl load ~/Library/LaunchAgents/com.malgcheong.orchestrator.plist
# always-on approval bot (needs DISCORD_BOT_TOKEN + DISCORD_CHANNEL_ID)
launchctl load ~/Library/LaunchAgents/com.malgcheong.orchestrator-bot.plist
```

Trigger the daily run once by hand to check it:

```bash
launchctl start com.malgcheong.orchestrator
tail -f /tmp/orchestrator-daily.log
```

## Disable

```bash
launchctl unload ~/Library/LaunchAgents/com.malgcheong.orchestrator.plist
launchctl unload ~/Library/LaunchAgents/com.malgcheong.orchestrator-bot.plist
```

Notes:
- Paths in the plists are absolute (`/Users/sukyungmac/...`); adjust if the repo moves.
- Live publishing stays off until `BLOG_AUTO_PUSH=true`; approval otherwise commits
  the post locally so you can push when ready.
