import asyncio
import io
import time
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


def format_audit_message(message: discord.Message) -> str:
    lines = [
        "=" * 72,
        f"Message link: {message.jump_url}",
        f"Created at: {message.created_at.isoformat()}",
        f"Bot: {message.author} (ID: {message.author.id})",
        "",
        "Message content:",
        message.content or "(none)",
    ]
    for index, embed in enumerate(message.embeds, start=1):
        lines.extend(
            [
                "",
                f"Embed {index}:",
                f"Title: {embed.title or '(none)'}",
                "Description:",
                embed.description or "(none)",
            ]
        )
        if embed.url:
            lines.append(f"URL: {embed.url}")
        if embed.author.name:
            lines.append(f"Author: {embed.author.name}")
        for field in embed.fields:
            lines.extend([f"Field: {field.name}", str(field.value)])
        if embed.footer.text:
            lines.append(f"Footer: {embed.footer.text}")
    return "\n".join(lines) + "\n\n"


def split_audit_report(text: str, max_bytes: int) -> t.Iterator[bytes]:
    """Split on complete lines, measuring the encoded upload size."""
    chunk = bytearray()
    for line in io.StringIO(text):
        encoded = line.encode("utf-8")
        if len(encoded) > max_bytes:
            raise ValueError("A single report line exceeds the upload limit.")
        if len(chunk) + len(encoded) > max_bytes:
            yield bytes(chunk)
            chunk.clear()
        chunk.extend(encoded)
    if chunk:
        yield bytes(chunk)


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
        report_text = io.StringIO()
        progress = await interaction.followup.send(
            f"Scanning {channel.mention}: **0** messages processed; **0** matches found. "
            "The total message count is unavailable.",
            ephemeral=True,
            wait=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

        async def scan() -> None:
            nonlocal scanned, matched, earliest, latest
            async for message in channel.history(
                limit=None, oldest_first=True, before=interaction.created_at
            ):
                scanned += 1
                if matches_api_log(message):
                    matched += 1
                    report_text.write(format_audit_message(message))
                    if earliest is None or message.created_at < earliest.created_at:
                        earliest = message
                    if latest is None or message.created_at > latest.created_at:
                        latest = message
                if scanned % 2500 == 0:
                    try:
                        await progress.edit(
                            content=f"Scanning {channel.mention}: **{scanned:,}** messages "
                            f"processed; **{matched:,}** matches found. "
                            "The total message count is unavailable."
                        )
                    except discord.HTTPException:
                        # A status update failure should not interrupt the history scan.
                        pass

        incomplete = ""
        started_at = time.monotonic()
        try:
            # Leave time to deliver results before the interaction token expires.
            await asyncio.wait_for(scan(), timeout=720)
        except asyncio.TimeoutError:
            incomplete = "Scan stopped after 12 minutes; these results are incomplete.\n\n"
        except discord.HTTPException:
            incomplete = "Discord interrupted the history scan; these results are incomplete.\n\n"

        elapsed_seconds = int(time.monotonic() - started_at)
        minutes, seconds = divmod(elapsed_seconds, 60)

        summary = discord.Embed(
            title="API moderator log audit",
            description=(
                f"{incomplete}Channel: {channel.mention}\n"
                f"Messages scanned: **{scanned}**\nMatching bot messages: **{matched}**\n"
                f"Scan duration: **{minutes}m {seconds}s**"
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
        try:
            await progress.edit(
                content=(
                    f"{'Scan stopped (incomplete)' if incomplete else 'Scan complete'}: "
                    f"**{scanned:,}** messages processed; **{matched:,}** matches found."
                )
            )
        except discord.HTTPException:
            pass
        await interaction.followup.send(
            embed=summary, ephemeral=False, allowed_mentions=discord.AllowedMentions.none()
        )
        await self.send_audit_report(
            interaction, report_text.getvalue() or "No matching messages.\n"
        )

    async def send_audit_report(
        self, interaction: discord.Interaction[commands.Bot], text: str
    ) -> None:
        # Leave a little headroom below Discord's limit and upload each part separately.
        max_bytes = max(1, int(interaction.filesize_limit * 0.95))
        try:
            parts = list(split_audit_report(text, max_bytes))
        except ValueError:
            await interaction.followup.send(
                "The audit report could not fit Discord's upload limit. "
                "The audit summary above is still available; no report was saved to disk.",
                ephemeral=False,
            )
            return
        for index, part in enumerate(parts, start=1):
            filename = (
                "api-mod-log-messages.txt"
                if len(parts) == 1
                else f"api-mod-log-messages-part-{index}-of-{len(parts)}.txt"
            )
            buffer = io.BytesIO(part)
            report = discord.File(buffer, filename=filename)
            try:
                await interaction.followup.send(
                    content=f"Matching messages (part {index} of {len(parts)}).",
                    file=report,
                    ephemeral=False,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except discord.HTTPException:
                await interaction.followup.send(
                    f"Discord rejected report part {index} of {len(parts)}. "
                    f"{index - 1} parts were uploaded; the remaining report was not delivered. "
                    "The audit summary above is still available. No report was saved to disk.",
                    ephemeral=False,
                )
                return
            finally:
                report.close()
                buffer.close()


async def setup(bot: Bot) -> None:
    await bot.add_cog(AuditModLogs())
