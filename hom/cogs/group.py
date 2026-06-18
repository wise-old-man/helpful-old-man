import re
import typing as t

import discord

from hom import utils
from hom.bot import Bot
from hom.config import Config
from hom.config import Constants
from hom.utils import ViewT

_GROUP_ID_LINK_PATTERN = re.compile(r"\[(?P<group_id>\d+)\]\(")


def _get_bot(interaction: discord.Interaction[t.Any]) -> Bot:
    client = interaction.client
    if not isinstance(client, Bot):
        raise RuntimeError("Unexpected interaction client type.")

    return client


def _get_embed_field_value(message: t.Optional[discord.Message], index: int) -> t.Optional[str]:
    if message is None or not message.embeds:
        return None

    fields = message.embeds[0].fields
    if len(fields) <= index:
        return None

    value = fields[index].value
    return str(value) if value else None


def _parse_group_id(value: t.Optional[str]) -> t.Optional[str]:
    if not value:
        return None

    if match := _GROUP_ID_LINK_PATTERN.search(value):
        return match.group("group_id")

    return value


async def _get_ticket_channel(
    interaction: discord.Interaction[t.Any],
) -> t.Optional[discord.TextChannel]:
    if isinstance(interaction.channel, discord.TextChannel):
        return interaction.channel

    await interaction.followup.send(
        "This action can only be used within a support ticket channel.",
        ephemeral=True,
    )
    return None


async def _build_group_lookup_permission_message(
    interaction: discord.Interaction[Bot],
) -> str:
    message = f"{Constants.DENIED} You do not have the required permissions to use this."

    if not isinstance(interaction.channel, discord.TextChannel):
        return message

    if interaction.client.user is None:
        return message

    async for channel_message in interaction.channel.history(limit=None):
        if channel_message.author.id != interaction.client.user.id:
            continue

        if not channel_message.embeds:
            continue

        if not any(
            mentioned_user.id == interaction.user.id for mentioned_user in channel_message.mentions
        ):
            continue

        return (
            f"{message}\n"
            f"If you haven't already, please follow these instructions: {channel_message.jump_url}"
        )

    return message


class GroupIdModal(discord.ui.Modal, title="Group Lookup"):
    group_id: discord.ui.TextInput["GroupIdModal"] = discord.ui.TextInput(
        label="Group ID",
        placeholder="Enter a group ID...",
        min_length=1,
        max_length=6,
    )

    async def on_submit(self, interaction: discord.Interaction[t.Any]) -> None:
        await interaction.response.defer(ephemeral=True)

        bot = _get_bot(interaction)
        group_id = self.group_id.value
        data = await bot.wom.get_group(group_id)
        if data is None:
            embed = discord.Embed(
                title="Group Lookup Failed",
                colour=discord.Colour.red(),
                url=f"{Config.DISCORD_BOT_BASE_WEBSITE_URL}/groups/{group_id}",
            )
            embed.add_field(
                name="Not Found",
                value=f"This group ({group_id}) does not exist.",
                inline=False,
            )
            await interaction.followup.send(embed=embed)
            return

        embed = discord.Embed(
            title="Group Lookup",
            colour=discord.Colour.blue(),
            url=f"{Config.DISCORD_BOT_BASE_WEBSITE_URL}/groups/{group_id}",
        )
        embed.add_field(name="ID", value=str(data["id"]))
        embed.add_field(name="Name", value=str(data["name"]))
        embed.add_field(name="Total Members", value=str(data["memberCount"]))
        leaders = [
            membership["player"]["displayName"]
            for membership in data["memberships"]
            if membership["role"] in ("owner", "deputy_owner")
        ]

        embed.add_field(name="Leaders", value="\n".join(leaders), inline=False)

        requested_by = "Unknown"
        requested_by_id = "Unknown"
        requested_by_name = "Unknown"
        if channel := await _get_ticket_channel(interaction):
            if og_user := await utils.get_user_by_original_message(channel):
                requested_by = og_user.mention
                requested_by_id = str(og_user.id)
                requested_by_name = og_user.name

        embed.add_field(name="Requested By", value=requested_by)
        embed.add_field(name="Requested By ID", value=requested_by_id, inline=True)
        embed.add_field(name="Requested By Name", value=requested_by_name, inline=True)
        embed.add_field(
            name="\u200b",
            value=(
                "-# Not your group? You can find your group id on the "
                f"[website]({Config.DISCORD_BOT_BASE_WEBSITE_URL}/groups) just below the group "
                "name and description."
            ),
            inline=False,
        )

        await interaction.followup.send(embed=embed, view=ApproveDenyGroupRequest(group_id))


class PlayerGroupModal(discord.ui.Modal, title="Player Lookup"):
    rsn: discord.ui.TextInput["PlayerGroupModal"] = discord.ui.TextInput(
        label="Runescape Name",
        placeholder="Enter a username...",
        default="",
        min_length=1,
        max_length=12,
    )
    group_id: discord.ui.TextInput["PlayerGroupModal"] = discord.ui.TextInput(
        label="Group ID (listed on group's page)",
        placeholder="ex. 123",
        default="",
        min_length=1,
        max_length=6,
    )

    async def on_submit(self, interaction: discord.Interaction[t.Any]) -> None:
        await interaction.response.defer(ephemeral=True)

        bot = _get_bot(interaction)
        rsn = self.rsn.value
        group_id = self.group_id.value
        data = await bot.wom.get_group(group_id)
        if data is None:
            embed = discord.Embed(
                title="Group Lookup Failed",
                colour=discord.Colour.red(),
                url=f"{Config.DISCORD_BOT_BASE_WEBSITE_URL}/groups/{group_id}",
            )
            embed.add_field(
                name="Not Found",
                value=f"This group ({group_id}) does not exist.",
                inline=False,
            )
            await interaction.followup.send(embed=embed)
            return

        usernames = [membership["player"]["username"] for membership in data["memberships"]]
        if any(username.lower() == rsn.lower() for username in usernames):
            embed = discord.Embed(
                title="Player Group Lookup",
                colour=discord.Colour.green(),
                url=f"{Config.DISCORD_BOT_BASE_WEBSITE_URL}/players/{rsn}",
            )
            embed.add_field(name="Player", value=rsn)
            embed.add_field(name="Group", value=str(data["name"]))
            embed.add_field(
                name="Group ID",
                value=(
                    f"[{data['id']}]"
                    f"({Config.DISCORD_BOT_BASE_WEBSITE_URL}/groups/{data['id']})"
                ),
            )
            embed.set_footer(text="The buttons below are for admin use only.")

            await interaction.followup.send(
                embed=embed,
                view=ApproveDenyPlayerRemoveRequest(
                    rsn=rsn,
                    group_id=group_id,
                    group_name=str(data["name"]),
                ),
            )
            return

        embed = discord.Embed(
            title="Player Lookup",
            colour=discord.Colour.red(),
            url=f"{Config.DISCORD_BOT_BASE_WEBSITE_URL}/players/{rsn}",
        )
        embed.add_field(
            name=f"{rsn} not found in group",
            value=f"{data['name']} ({data['id']})",
        )
        embed.set_footer(text="Please verify you have typed the correct RSN and Group ID.")
        await interaction.followup.send(embed=embed)


class ApproveDenyPlayerRemoveRequest(discord.ui.View):
    def __init__(self, rsn: str, group_id: str, group_name: str) -> None:
        super().__init__(timeout=None)
        self.rsn = rsn
        self.group_id = group_id
        self.group_name = group_name

    @discord.ui.button(
        emoji="\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}",
        label="Remove Player From Group",
        style=discord.ButtonStyle.blurple,
        custom_id="persistent_view:remove_player_from_group",
    )
    async def remove_player_from_group(
        self: "ApproveDenyPlayerRemoveRequest",
        interaction: discord.Interaction[Bot],
        _: discord.ui.Button[ViewT],
    ) -> None:
        assert isinstance(interaction.user, discord.Member)
        await interaction.response.defer(ephemeral=True)

        if not any(role.id == Config.MOD_ROLE for role in interaction.user.roles):
            await interaction.followup.send(
                f"{Constants.DENIED} You do not have the required permissions to use this.",
                ephemeral=True,
            )
            return

        rsn = self.rsn or _get_embed_field_value(interaction.message, 0)
        group_id = self.group_id or _parse_group_id(_get_embed_field_value(interaction.message, 2))
        group_name = self.group_name or _get_embed_field_value(interaction.message, 1) or "Unknown"
        if rsn is None or group_id is None:
            await interaction.followup.send(
                "Could not determine the player or group to update.",
                ephemeral=True,
            )
            return

        removed = await interaction.client.wom.remove_player_group(rsn=rsn, group_id=group_id)
        if removed is None:
            await interaction.followup.send(
                "Failed to remove player from group.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(title="Player Removed from Group")
        embed.add_field(name="Runescape Name", value=rsn)
        embed.add_field(name="Group ID", value=group_id)
        embed.add_field(name="Group Name", value=group_name)
        await interaction.followup.send(embed=embed)


class ApproveDenyGroupRequest(discord.ui.View):
    def __init__(self, group_id: str) -> None:
        super().__init__(timeout=None)
        self.group_id = group_id

    @discord.ui.button(
        emoji=Constants.COMPLETE,
        label="Verify Group",
        style=discord.ButtonStyle.blurple,
        custom_id="persistent_view:verify_group",
    )
    async def verify_group(
        self: "ApproveDenyGroupRequest",
        interaction: discord.Interaction[Bot],
        _: discord.ui.Button["ApproveDenyGroupRequest"],
    ) -> None:
        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None
        await interaction.response.defer(ephemeral=True)

        if not any(role.id == Config.MOD_ROLE for role in interaction.user.roles):
            await interaction.followup.send(
                await _build_group_lookup_permission_message(interaction),
                ephemeral=True,
            )
            return

        channel = await _get_ticket_channel(interaction)
        if channel is None:
            return

        ticket_user = await utils.get_user_by_original_message(channel)
        if not isinstance(ticket_user, discord.Member):
            await interaction.followup.send(
                "Could not determine the ticket owner.",
                ephemeral=True,
            )
            return

        group_id = self.group_id or _parse_group_id(_get_embed_field_value(interaction.message, 0))
        if not group_id:
            await interaction.followup.send("Could not determine group ID.", ephemeral=True)
            return

        verified = await interaction.client.wom.verify_group(group_id)
        if not verified:
            await interaction.followup.send(
                f"Failed to verify group `{group_id}`. Check the ID and try again.",
                ephemeral=True,
            )
            return

        if role := utils.get_role(interaction.guild, Config.GROUP_LEADER_ROLE):
            await ticket_user.add_roles(role)

        data = await interaction.client.wom.get_group(group_id)
        if data is None:
            await interaction.followup.send(
                f"Group `{group_id}` verified but could not fetch details.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(title="Group Verified", colour=discord.Colour.green())
        embed.add_field(name="ID", value=group_id)
        embed.add_field(name="Group Name", value=str(data["name"]))
        await utils.send_log_message(
            interaction,
            f"Group: [{group_id}]({Config.DISCORD_BOT_BASE_WEBSITE_URL}/groups/{group_id})\n"
            f"Verified by: {ticket_user.mention}, `{ticket_user.id}`, `{ticket_user.name}`",
            title="Verified Group",
            mod=interaction.user,
        )
        await interaction.followup.send(embed=embed)
        self.stop()

    @discord.ui.button(
        emoji="\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}",
        label="Reset Group Code",
        style=discord.ButtonStyle.blurple,
        custom_id="persistent_view:reset_group_code",
    )
    async def reset_group_code(
        self: "ApproveDenyGroupRequest",
        interaction: discord.Interaction[Bot],
        _: discord.ui.Button["ApproveDenyGroupRequest"],
    ) -> None:
        assert isinstance(interaction.user, discord.Member)
        await interaction.response.defer(ephemeral=True)

        if not any(role.id == Config.MOD_ROLE for role in interaction.user.roles):
            await interaction.followup.send(
                await _build_group_lookup_permission_message(interaction),
                ephemeral=True,
            )
            return

        group_id = self.group_id or _parse_group_id(_get_embed_field_value(interaction.message, 0))
        if group_id is None:
            await interaction.followup.send("Could not determine group ID.", ephemeral=True)
            return

        data = await interaction.client.wom.get_group(group_id)
        if data is None:
            await interaction.followup.send("Could not find group...", ephemeral=True)
            return

        reset_code = await interaction.client.wom.reset_group_code(group_id)
        new_code = reset_code.get("newCode") if reset_code is not None else None
        if not isinstance(new_code, str):
            await interaction.followup.send(
                "Could not reset the group verification code.",
                ephemeral=True,
            )
            return

        channel = await _get_ticket_channel(interaction)
        if channel is None:
            return

        ticket_user = await utils.get_user_by_original_message(channel)
        if ticket_user is None:
            await interaction.followup.send(
                "Could not determine the ticket owner.",
                ephemeral=True,
            )
            return

        await ticket_user.send(
            f"Your verification code for group [{group_id}]"
            f"({Config.DISCORD_BOT_BASE_WEBSITE_URL}/groups/{group_id}) has been reset.\n"
            f"```{new_code}```"
            "Keep this code secret - it can be used to edit or delete your group."
        )
        embed = discord.Embed(title="Reset Group Code", colour=discord.Colour.green())
        embed.add_field(name="Group ID", value=group_id)
        embed.add_field(name="Group Name", value=str(data["name"]))
        embed.description = (
            "Verification code successfully reset. "
            f"A DM has been sent to {ticket_user.mention}."
        )
        await interaction.followup.send(embed=embed)

    @discord.ui.button(
        emoji=Constants.PEN,
        label="Group Lookup",
        style=discord.ButtonStyle.blurple,
        custom_id="persistent_view:approve_deny_group_lookup",
    )
    async def group_lookup(
        self: ViewT,
        interaction: discord.Interaction[Bot],
        _: discord.ui.Button[ViewT],
    ) -> None:
        await interaction.response.send_modal(GroupIdModal())


async def setup(bot: Bot) -> None:
    bot.add_view(ApproveDenyGroupRequest(group_id=""))
    bot.add_view(ApproveDenyPlayerRemoveRequest(rsn="", group_id="", group_name=""))
