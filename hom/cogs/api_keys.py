import asyncio
import csv
import io
import time
import typing as t
from collections import Counter

import discord
from discord import app_commands
from discord.ext import commands

from hom import utils
from hom.bot import Bot

MAX_CSV_BYTES = 1024 * 1024
MAX_DEVELOPERS = 5000


def read_developers(data: bytes) -> t.List[str]:
    """Validate the entire CSV before making any changes; preserve exact names."""
    if len(data) > MAX_CSV_BYTES:
        raise ValueError("The CSV must be no larger than 1 MiB.")
    try:
        reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig")), strict=True)
        if not reader.fieldnames or reader.fieldnames.count("developer") != 1:
            raise ValueError("The CSV must contain a developer column.")
        developers: t.Dict[str, None] = {}
        for row in reader:
            developer = row.get("developer")
            if not developer or None in row:
                raise ValueError("Every CSV row must contain a non-empty developer value.")
            developers[developer] = None
            if len(developers) > MAX_DEVELOPERS:
                raise ValueError(f"The CSV may contain at most {MAX_DEVELOPERS} developers.")
        if not developers:
            raise ValueError("The CSV contains no developers.")
        return sorted(developers, key=lambda name: (name.casefold(), name))
    except (UnicodeDecodeError, csv.Error) as error:
        raise ValueError("Upload a valid UTF-8 CSV with a developer column.") from error


def member_names(member: discord.Member) -> t.Set[str]:
    names = {member.name}
    if member.discriminator != "0":
        names.add(str(member))
    return names


def match_developers(
    developers: t.List[str], members: t.List[discord.Member]
) -> t.Dict[str, t.List[discord.Member]]:
    matches: t.Dict[str, t.List[discord.Member]] = {name: [] for name in developers}
    for member in members:
        for name in member_names(member):
            if name in matches:
                matches[name].append(member)
    return matches


class ApiKeys(commands.Cog):
    def __init__(self) -> None:
        self.running_guilds: t.Set[int] = set()

    @app_commands.guild_only()  # type: ignore
    @app_commands.describe(
        developers="UTF-8 CSV containing a developer column (for example devs.csv).",
        api_consumer_role="The API Consumer role to check and assign to matched users.",
        dry_run="Preview matches without updating keys (default: True). Set False to apply updates.",
        counts_only="Show category totals instead of individual usernames (default: False).",
    )
    @app_commands.command(
        name="link-user-api-keys",
        description="[Mod 🔒]: Link Discord users to their API keys.",
    )
    async def link_user_api_keys(
        self,
        interaction: discord.Interaction[commands.Bot],
        developers: discord.Attachment,
        api_consumer_role: discord.Role,
        dry_run: bool = True,
        counts_only: bool = False,
    ) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)

        if not await utils.mod_check(interaction):
            return

        assert interaction.guild
        guild = interaction.guild
        role_id = api_consumer_role.id
        if guild.get_role(role_id) is None:
            await interaction.followup.send(
                "The selected API Consumer role is no longer available in this server.",
                ephemeral=True,
            )
            return
        if guild.id in self.running_guilds:
            await interaction.followup.send(
                "A linking run is already in progress.", ephemeral=True
            )
            return

        self.running_guilds.add(guild.id)
        try:
            await self.link_users(interaction, developers, guild, role_id, dry_run, counts_only)
        finally:
            self.running_guilds.discard(guild.id)

    async def link_users(
        self,
        interaction: discord.Interaction[commands.Bot],
        attachment: discord.Attachment,
        guild: discord.Guild,
        role_id: int,
        dry_run: bool = True,
        counts_only: bool = False,
    ) -> None:
        try:
            if attachment.size > MAX_CSV_BYTES:
                raise ValueError("The CSV must be no larger than 1 MiB.")
            developers = read_developers(await attachment.read())
        except (ValueError, discord.HTTPException) as error:
            message = (
                str(error) if isinstance(error, ValueError) else "Could not download the CSV."
            )
            await interaction.followup.send(message, ephemeral=True)
            return

        async def fetch_members() -> t.List[discord.Member]:
            return [member async for member in guild.fetch_members(limit=None)]

        try:
            members = await asyncio.wait_for(fetch_members(), timeout=120)
        except (discord.HTTPException, discord.ClientException, asyncio.TimeoutError):
            await interaction.followup.send(
                "Could not fetch the server members. Check the bot's Server Members Intent. "
                "No API keys were changed.",
                ephemeral=True,
            )
            return

        matches = match_developers(developers, members)
        bot = t.cast(Bot, interaction.client)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["developer", "status", "developerDiscordId", "updatedCount"])
        linked = updated = skipped = 0
        role_added: t.Set[int] = set()
        role_needed: t.Set[int] = set()
        role_actions: t.Dict[str, str] = {}
        stopped = False
        deadline = time.monotonic() + 600
        for developer in developers:
            candidates = matches[developer]
            if stopped or time.monotonic() >= deadline:
                stopped = True
                writer.writerow([developer, "not_processed", "", ""])
                continue
            if len(candidates) != 1:
                skipped += 1
                status = "no_username_match" if not candidates else "ambiguous_username"
                writer.writerow([developer, status, "", ""])
                continue
            try:
                member = await guild.fetch_member(candidates[0].id)
            except discord.NotFound:
                skipped += 1
                writer.writerow([developer, "member_left", "", ""])
                continue
            except discord.HTTPException:
                stopped = True
                writer.writerow([developer, "member_fetch_failed", "", ""])
                continue
            if developer not in member_names(member):
                skipped += 1
                writer.writerow([developer, "username_changed", "", ""])
                continue
            if not any(role.id == role_id for role in member.roles):
                if member.id in role_added:
                    role_actions[developer] = "added_earlier_in_run"
                elif dry_run:
                    role_needed.add(member.id)
                    role_actions[developer] = "would_add"
                else:
                    role = guild.get_role(role_id)
                    if role is None:
                        stopped = True
                        writer.writerow([developer, "role_unavailable", member.id, ""])
                        role_actions[developer] = "failed"
                        continue
                    try:
                        await member.add_roles(role, reason="Linking API key developer from CSV")
                    except discord.HTTPException:
                        skipped += 1
                        writer.writerow([developer, "role_add_failed", member.id, ""])
                        role_actions[developer] = "failed_or_unconfirmed"
                        continue
                    role_added.add(member.id)
                    role_actions[developer] = "added"
            else:
                role_actions[developer] = "already_has_role"
            if dry_run:
                linked += 1
                writer.writerow([developer, "would_link", member.id, ""])
                continue
            count = await bot.wom.link_developer_api_keys(developer, member.id)
            if count is None:
                # A timeout may follow a committed update. Stop without blindly retrying.
                stopped = True
                writer.writerow([developer, "api_failed_or_unconfirmed", member.id, ""])
            elif count == 0:
                skipped += 1
                writer.writerow([developer, "no_api_keys_found", member.id, 0])
            else:
                linked += 1
                updated += count
                writer.writerow([developer, "linked", member.id, count])

        notice = (
            "Stopped early; see the report for failed or unprocessed rows. " if stopped else ""
        )
        if dry_run:
            summary = (
                f"**Dry run:** {linked} users would be linked; {skipped} skipped. "
                f"Would add the API Consumer role to {len(role_needed)} users. "
                "No API keys were changed and no roles were added. This checks server matches; "
                "it does not check whether those developers have keys in the database."
            )
        else:
            summary = (
                f"Linked {linked} developers ({updated} API key rows); skipped {skipped}. "
                f"Added the API Consumer role to {len(role_added)} users. "
                "Updates include revoked keys and replace any previous developerDiscordId values."
            )
        rows = list(csv.reader(io.StringIO(output.getvalue())))
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(rows[0] + ["roleAction"])
        writer.writerows(row + [role_actions.get(row[0], "not_checked")] for row in rows[1:])
        csv_content = output.getvalue()
        skipped_lines: t.List[str] = []
        reasons = {
            "no_username_match": "not found in server (possibly renamed or left)",
            "ambiguous_username": "multiple username matches",
            "member_left": "no longer in server",
            "member_fetch_failed": "could not recheck member",
            "username_changed": "username changed during this run",
            "role_add_failed": "could not add API Consumer role; keys not updated",
            "role_unavailable": "API Consumer role no longer exists",
            "no_api_keys_found": "no API keys found for this developer",
            "api_failed_or_unconfirmed": "API update failed or could not be confirmed",
            "not_processed": "not processed because the run stopped early",
        }
        status_counts: t.Counter[str] = Counter()
        for row in csv.DictReader(io.StringIO(csv_content)):
            status_counts[row["status"]] += 1
            if row["status"] in {"linked", "would_link"}:
                continue
            if counts_only:
                continue
            name = discord.utils.escape_markdown(row["developer"][:200].replace("\n", "\\n"))
            skipped_lines.append(f"- {name}: {reasons[row['status']]}")
        if counts_only:
            summary += "\n\n**Result counts:**\n" + "\n".join(
                f"- {reason[0].upper() + reason[1:]}: {status_counts[status]}"
                for status, reason in reasons.items()
            )
        report = discord.File(
            io.BytesIO(csv_content.encode("utf-8-sig")), filename="api-key-link-results.csv"
        )
        try:
            await interaction.followup.send(
                notice + summary,
                file=report,
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        finally:
            report.close()
        if skipped_lines:
            message = "**Users not linked:**\n"
            for line in skipped_lines:
                if len(message) + len(line) + 1 > 1900:
                    await interaction.followup.send(
                        message, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
                    )
                    message = "**Users not linked (continued):**\n"
                message += line + "\n"
            await interaction.followup.send(
                message, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
            )


async def setup(bot: Bot) -> None:
    await bot.add_cog(ApiKeys())
