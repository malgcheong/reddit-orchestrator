# Discord approval setup

Approval (stage 7) has two levels. Start with the webhook; add the bot later if you
want one-tap buttons.

## Level 1 — Webhook (5 minutes, preview only)

A webhook posts the digest preview to a channel. You still approve with the resume
CLI. No Discord app needed.

1. Discord → your server → **Server Settings → Integrations → Webhooks → New Webhook**.
2. Pick the channel, **Copy Webhook URL**.
3. Put it in `orchestrator/.env`:
   ```
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/....
   ```
4. Run a digest. The preview is posted to the channel; approve/reject with:
   ```
   uv run python -m orchestrator.resume digest-YYYY-MM-DD approve
   uv run python -m orchestrator.resume digest-YYYY-MM-DD reject
   ```

With no `DISCORD_WEBHOOK_URL` set, notifications run in **dry mode** (printed to the
console), so the whole flow is testable without Discord.

## Level 2 — Bot (interactive Approve / Reject buttons)

The bot posts the preview with buttons and resumes the run when you tap one. Run it
as an always-on service.

1. https://discord.com/developers/applications → **New Application**.
2. **Bot** tab → **Reset Token** → copy it → `DISCORD_BOT_TOKEN` in `.env`.
   (Message Content / Server Members intents can stay default; buttons do not need them.)
3. **Installation / OAuth2 → URL Generator**: scope `bot`, permissions
   *Send Messages* + *Embed Links*. Open the generated URL and add the bot to your server.
4. Enable **Developer Mode** (User Settings → Advanced), right-click the target
   channel → **Copy Channel ID** → `DISCORD_CHANNEL_ID` in `.env`.
5. `.env` now has:
   ```
   DISCORD_BOT_TOKEN=...
   DISCORD_CHANNEL_ID=123456789012345678
   ```
6. Run the bot (keep it running):
   ```
   uv run python -m orchestrator.discord_bot
   ```

The bot polls Postgres every 30s for runs in `pending_approval`, posts each once with
Approve/Reject buttons, and calls the same `resume.apply_decision` as the CLI. On
approve it publishes (commit; push only if `BLOG_AUTO_PUSH=true`).

## Going fully unattended

Once the webhook (or bot) works, enable the daily schedule and, for buttons, the bot
service. See [scheduling.md](scheduling.md).
