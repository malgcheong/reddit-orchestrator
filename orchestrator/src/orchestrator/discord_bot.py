"""Always-on Discord approval bot (stage 7, interactive variant).

Polls Postgres for runs in `pending_approval`, posts an embed with Approve/Reject
buttons, and on click resumes the run via resume.apply_decision. This is the
interactive alternative to the resume CLI; it needs DISCORD_BOT_TOKEN and
DISCORD_CHANNEL_ID. Run it as a long-lived service (e.g. launchd):

  uv run python -m orchestrator.discord_bot

Message Content / Guild intents must be enabled for the bot in the Discord portal.
"""
import discord
from discord.ext import tasks

from . import db, notify, resume
from .config import settings

_posted: set[str] = set()


class ApprovalView(discord.ui.View):
    def __init__(self, digest_key: str):
        super().__init__(timeout=settings.approval_timeout_hours * 3600)
        self.digest_key = digest_key

    async def _decide(self, interaction: discord.Interaction, approved: bool):
        await interaction.response.defer()
        out = resume.apply_decision(self.digest_key, approved, by=str(interaction.user))
        verb = "발행 승인" if approved else "반려"
        tail = f" → {out['publish']['url']}" if out.get("publish", {}).get("url") else ""
        await interaction.followup.send(f"[{self.digest_key}] {verb} ({interaction.user}){tail}")
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)
        self.stop()

    @discord.ui.button(label="승인 ✅", style=discord.ButtonStyle.success)
    async def approve(self, interaction, button):
        await self._decide(interaction, True)

    @discord.ui.button(label="반려 ❌", style=discord.ButtonStyle.danger)
    async def reject(self, interaction, button):
        await self._decide(interaction, False)


class Bot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())

    async def on_ready(self):
        print(f"[discord] logged in as {self.user}")
        if not self.poll.is_running():
            self.poll.start()

    @tasks.loop(seconds=30)
    async def poll(self):
        channel = self.get_channel(settings.discord_channel_id)
        if channel is None:
            return
        for row in db.pending_approvals():
            key = row["digest_key"]
            if key in _posted:
                continue
            _posted.add(key)
            embed_payload = notify.build_embed(key, {"title": row["title"]}, row["judge"],
                                               row["markdown"], row["steps"])
            e = embed_payload["embeds"][0]
            embed = discord.Embed(title=e["title"], description=e["description"], color=e["color"])
            for f in e["fields"]:
                embed.add_field(name=f["name"], value=f["value"], inline=f.get("inline", False))
            await channel.send(embed=embed, view=ApprovalView(key))


def main():
    if not settings.discord_bot_token:
        raise SystemExit("DISCORD_BOT_TOKEN is not set")
    Bot().run(settings.discord_bot_token)


if __name__ == "__main__":
    main()
