import asyncio
import io
import typing as t

import discord
from discord import app_commands
from discord.ext import commands

from hom import utils
from hom.bot import Bot


def matches_api_log(message: discord.Message) -> bool:
    if not message.author.bot:
        return False
    texts = [message.content.casefold()]
    for embed in message.embeds:
        texts.extend([(embed.title or "").casefold(), (embed.description or "").casefold()])
    return any("api" in text for text in texts) and not any(
        "channel" in text or "for user" in text for text in texts
    )


class AuditModLogs(commands.Cog):
    def __init__(self) -> None:
        self.running_channels: t.Set[int] = set()

    @app_commands.guild_only()  # type: ignore
    @app_commands.describe(channel="The channel whose bot messages should be searched.")
    @app_commands.command(
        name="audit-mod-logs", description="[Mod 🔒]: Find API-related bot messages in a channel."
    )
    async def audit_mod_logs(
        self, interaction: discord.Interaction[commands.Bot], channel: discord.TextChannel
    ) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        if not await utils.mod_check(interaction):
            return
        assert interaction.guild
        assert isinstance(interaction.user, discord.Member)
        if channel.guild.id != interaction.guild.id:
            await interaction.followup.send("Select a channel in this server.", ephemeral=True)
            return
        for member in (interaction.user, interaction.guild.me):
            permissions = channel.permissions_for(member)
            if not permissions.view_channel or not permissions.read_message_history:
                await interaction.followup.send(
                    "Both you and the bot need View Channel and Read Message History "
                    "permissions in the selected channel.",
                    ephemeral=True,
                )
                return
        if channel.id in self.running_channels:
            await interaction.followup.send(
                "An audit is already running for this channel.", ephemeral=True
            )
            return

        self.running_channels.add(channel.id)
        try:
            await self.scan_channel(interaction, channel)
        finally:
            self.running_channels.discard(channel.id)

    async def scan_channel(
        self, interaction: discord.Interaction[commands.Bot], channel: discord.TextChannel
    ) -> None:
        scanned = matched = 0
        earliest: t.Optional[discord.Message] = None
        latest: t.Optional[discord.Message] = None
        links = io.StringIO()

        async def scan() -> None:
            nonlocal scanned, matched, earliest, latest
            async for message in channel.history(
                limit=None, oldest_first=True, before=interaction.created_at
            ):
                scanned += 1
                if not matches_api_log(message):
                    continue
                matched += 1
                links.write(message.jump_url + "\n")
                if earliest is None or message.created_at < earliest.created_at:
                    earliest = message
                if latest is None or message.created_at > latest.created_at:
                    latest = message

        incomplete = ""
        try:
            # Leave time to deliver results before the interaction token expires.
            await asyncio.wait_for(scan(), timeout=720)
        except asyncio.TimeoutError:
            incomplete = "Scan stopped after 12 minutes; these results are incomplete.\n\n"
        except discord.HTTPException:
            incomplete = "Discord interrupted the history scan; these results are incomplete.\n\n"

        summary = discord.Embed(
            title="API moderator log audit",
            description=(
                f"{incomplete}Channel: {channel.mention}\n"
                f"Messages scanned: **{scanned}**\nMatching bot messages: **{matched}**"
            ),
        )
        for label, found in (("Earliest match", earliest), ("Latest match", latest)):
            value = (
                f"{discord.utils.format_dt(found.created_at, 'F')}\n[View message]({found.jump_url})"
                if found is not None
                else "None found"
            )
            summary.add_field(name=label, value=value, inline=False)
        summary.set_footer(
            text="Case-insensitive: includes 'api'; excludes 'channel' and 'for user' "
            "in message content or any embed title/description."
        )
        report = discord.File(
            io.BytesIO((links.getvalue() or "No matching messages.\n").encode("utf-8")),
            filename="api-mod-log-message-links.txt",
        )
        try:
            await interaction.followup.send(
                embed=summary,
                file=report,
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        finally:
            report.close()


async def setup(bot: Bot) -> None:
    await bot.add_cog(AuditModLogs())
