import discord
from discord.ext import commands

from hom import utils, config
from hom.bot import Bot
from hom.config import Config, Constants
from hom.utils import ViewT

class GroupIdModal(discord.ui.Modal, title="Group Lookup"):
    group_id = discord.ui.TextInput(
        label="Group ID",
        placeholder="Enter a group ID...",
        min_length=1,
        max_length=6,
    )

    async def on_submit(self, interaction: discord.Interaction[commands.Bot]) -> None:
        await interaction.response.defer(ephemeral=True)

        data = await interaction.client.wom.get_group(self.group_id)
        if data is None:
            embed = discord.Embed(
                title=f"Group Lookup Failed",
                colour=discord.Colour.red(),
                url=f"{Config.DISCORD_BOT_BASE_WEBSITE_URL}/groups/{self.group_id.value}"
            )
            embed.add_field(name="Not Found", value=f"This group ({self.group_id.value}) does not exist.", inline=False)
            await interaction.followup.send(embed=embed)
            return



        embed = discord.Embed(
            title=f"Group Lookup",
            colour=discord.Colour.blue(),
            url=f"{Config.DISCORD_BOT_BASE_WEBSITE_URL}/groups/{self.group_id.value}"
        )
        embed.add_field(name="ID", value=data["id"])
        embed.add_field(name="Name", value=data["name"])
        embed.add_field(name="Total Members", value=data["memberCount"])
        leaders = [data["player"]["displayName"] for data in data["memberships"] if data["role"] in ("owner", "deputy_owner")]

        embed.add_field(name="Leaders", value="\n ".join(leaders), inline=False)
        og_user = await utils.get_user_by_original_message(interaction.channel)
        embed.add_field(name="Requested By", value=og_user.mention)
        embed.add_field(name="Requested By ID", value=og_user.id, inline=True)
        embed.add_field(name="Requested By Name", value=og_user.name, inline=True)


        await interaction.followup.send(embed=embed, view=ApproveDenyGroupRequest(self.group_id.value))


class PlayerGroupModal(discord.ui.Modal, title="Player Lookup"):
    rsn = discord.ui.TextInput(
        label="Runescape Name",
        placeholder="Enter a username...",
        default="PhyrWall",
        min_length=1,
        max_length=12,
    )
    group_id = discord.ui.TextInput(
        label="Group ID (listed on group's page)",
        placeholder="ex. 123",
        default="1",
        min_length=1,
        max_length=6,
    )

    async def on_submit(self, interaction: discord.Interaction[commands.Bot]) -> None:
        await interaction.response.defer(ephemeral=True)

        data = await interaction.client.wom.get_group(self.group_id)
        if data is None:
            embed = discord.Embed(
                title=f"Group Lookup Failed",
                colour=discord.Colour.red(),
                url=f"{Config.DISCORD_BOT_BASE_WEBSITE_URL}/groups/{self.group_id.value}"
            )
            embed.add_field(name="Not Found", value=f"This group ({self.group_id.value}) does not exist.", inline=False)
            await interaction.followup.send(embed=embed)
            return

        usernames = [m["player"]["username"] for m in data['memberships']]
        if (self.rsn.value).lower() in str(usernames).lower():

            embed = discord.Embed(
                title="Player Group Lookup",
                colour=discord.Colour.green(),
                url=f"{Config.DISCORD_BOT_BASE_WEBSITE_URL}/players/{self.rsn.value}"
            )
            embed.add_field(name="Player", value=self.rsn.value)
            embed.add_field(name="Group",
                            value=data['name'])
            embed.add_field(name="Group ID",
                            value=f"[{data['id']}]({Config.DISCORD_BOT_BASE_WEBSITE_URL}/groups/{data['id']})")

            embed.set_footer(text="The buttons below are for admin use only.")

            await interaction.followup.send(embed=embed, view=ApproveDenyPlayerRemoveRequest(
                rsn=self.rsn.value, group_id=self.group_id.value, group_name=data['name']
            ))
        else:
            embed=discord.Embed(
                title=f"Player Lookup",
                colour=discord.Colour.red(),
                url=f"{Config.DISCORD_BOT_BASE_WEBSITE_URL}/players/{self.rsn.value}"
            )
            embed.add_field(name=f"{self.rsn.value} not found in group", value=f"{data['name']} ({data['id']})")
            embed.set_footer(text="Please verify you have typed the correct RSN and Group ID.")
            await interaction.channel.send(embed=embed)

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
        custom_id="persistent_view:remove_player_from_group",  # must be unique
    )
    async def remove_player_from_group(self: "ApproveDenyPlayerRemoveRequest",
                                       interaction: discord.Interaction[Bot],
                                       _: discord.ui.Button[ViewT]) -> None:
        assert isinstance(interaction.user, discord.Member)
        await interaction.response.defer(ephemeral=True)
        if not any(role.id == Config.MOD_ROLE for role in interaction.user.roles):
            await interaction.response.followup(
                f"{Constants.DENIED} You do not have the required permissions to use this.",
                ephemeral=True
            )
            return

        message = interaction.message
        group_id = message.embeds[0].fields[2].value
        rsn = message.embeds[0].fields[0].value
        print(group_id, rsn)

        removed = await interaction.client.wom.remove_player_group(rsn=rsn, group_id=group_id)

        if removed is None:
            await interaction.followup.send("Failed to remove player from group.", ephemeral=True)
            return

        embed = discord.Embed(title="Player Removed from Group")
        embed.add_field(name="Runescape Name", value=rsn)
        embed.add_field(name="Group ID", value=group_id)
        await interaction.followup.send(embed=embed)

class ApproveDenyGroupRequest(discord.ui.View):
    def __init__(self, group_id: str) -> None:
        super().__init__(timeout=None)
        self.group_id = group_id
        self.user = discord.user

    @discord.ui.button(
        emoji=f"{Constants.COMPLETE}",
        label=f"Verify Group",
        style=discord.ButtonStyle.blurple,
        custom_id="persistent_view:verify_group",
    )
    async def verify_group(
        self: "ApproveDenyGroupRequest", interaction: discord.Interaction[Bot],
        _: discord.ui.Button["ApproveDenyGroupRequest"]
    ) -> None:
        assert isinstance(interaction.user, discord.Member)
        ticket_user = await utils.get_user_by_original_message(interaction.channel)
        assert isinstance(ticket_user, discord.Member)

        await interaction.response.defer(ephemeral=True)

        if not any(role.id == Config.MOD_ROLE for role in interaction.user.roles):
            await interaction.followup.send(
                f"{Constants.DENIED} You do not have the required permissions to use this.",
                ephemeral=True
            )
            return

        message = interaction.message
        group_id = message.embeds[0].fields[0].value if message and message.embeds else None

        if not group_id:
            await interaction.followup.send(
                "Could not determine group ID.", ephemeral=True
            )
            return

        verified = await interaction.client.wom.verify_group(self.group_id)
        if not verified:
            await interaction.followup.send(
                f"Failed to verify group `{self.group_id}`. Check the ID and try again.",
                ephemeral=True,
            )
            return

        if role := utils.get_role(interaction.guild, Config.GROUP_LEADER_ROLE):
            await ticket_user.add_roles(role)

        data = await interaction.client.wom.get_group(self.group_id)
        if data is None:
            await interaction.followup.send(
                f"Group `{self.group_id}` verified but could not fetch details.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(title="Group Verified", colour=discord.Colour.green())
        embed.add_field(name="ID", value=group_id)
        embed.add_field(name="Group Name", value=data["name"])
        if role := utils.get_role(interaction.guild, Config.GROUP_LEADER_ROLE):
            await ticket_user.add_roles(role)
        await utils.send_log_message(
            interaction,
            f"Group: [{group_id}]({Config.DISCORD_BOT_BASE_WEBSITE_URL}/groups/{group_id})\n"
            f"Verified by: {ticket_user.mention}, `{ticket_user.id}`, `{ticket_user.name}`",
            title="Verified Group",
            mod=interaction.user,
        )
        await interaction.followup.send(embed=embed)

    @discord.ui.button(
        emoji="\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}",
        label="Reset Group Code",
        style=discord.ButtonStyle.blurple,
        custom_id="persistent_view:reset_group_code",  # must be unique
    )
    async def reset_group_code(
        self: ViewT, interaction: discord.Interaction[Bot], _: discord.ui.Button[ViewT]
    ) -> None:
        assert isinstance(interaction.user, discord.Member)

        await interaction.response.defer(ephemeral=True)

        if not any(role.id == Config.MOD_ROLE for role in interaction.user.roles):
            await interaction.followup.send(
                f"{Constants.DENIED} You do not have the required permissions to use this.",
                ephemeral=True
            )
            return

        message = interaction.message
        group_id = message.embeds[0].fields[0].value if message and message.embeds else None

        data = await interaction.client.wom.get_group(group_id)
        if data is None:
            await interaction.followup.send(f"Could not find group...")
            return
        reset_code = await interaction.client.wom.reset_group_code(group_id)

        ticket_user = await utils.get_user_by_original_message(interaction.channel)
        await ticket_user.send(
            f"Your verification code for group [{group_id}]({config.Config.DISCORD_BOT_BASE_WEBSITE_URL}/groups/{group_id}) has been reset.\n"
            f"```{reset_code['newCode']}```"
            f"Keep this code secret — it can be used to edit or delete your group."
        )
        embed = discord.Embed(title="Reset Group Code", colour=discord.Colour.green())
        embed.add_field(name="Group ID", value=group_id)
        embed.add_field(name="Group Name", value=data["name"])
        embed.description = f"Verification code successfully reset. A DM has been sent to {ticket_user.mention}."
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    bot.add_view(ApproveDenyGroupRequest(group_id=""))
    bot.add_view(ApproveDenyPlayerRemoveRequest(rsn="", group_id="", group_name=""))
