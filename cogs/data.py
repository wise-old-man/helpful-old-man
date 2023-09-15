import discord
import views as vw
from discord import app_commands, AppCommandType
from discord.ext import commands, tasks
from utilities import discord_utils as du
from data import constant_data as cd
from collections import defaultdict


class Data(commands.GroupCog, name="data"):
    def __init__(self, bot: commands.Bot) -> None:
        bot.tree.add_command(app_commands.ContextMenu(name='Support Redirect',
                                                      callback=self.support_redirect,
                                                      type=AppCommandType.message,
                                                      guild_ids=cd.SUPPORTED_GUILD_IDS))

        bot.tree.add_command(app_commands.ContextMenu(name='Awaiting Response',
                                                      callback=self.awaiting_response,
                                                      type=AppCommandType.message,
                                                      guild_ids=cd.SUPPORTED_GUILD_IDS))

        self.bot = bot
        super().__init__()

        self.cooldowns = defaultdict(lambda: 0)
        self.cooldown_value = 5
        self.decrement_cooldown.start()

        self.support_title = "Need help from one of our moderators?"
        self.support_message_color = discord.Colour.dark_blue()
        self.support_footer = "As a reminder, all moderators and admins in this server volunteer to help in their free time.\nWe appreciate your patience."

    @tasks.loop(seconds=1, count=None)
    async def decrement_cooldown(self):
        await self.bot.wait_until_ready()

        for cooldown in list(self.cooldowns):
            if self.cooldowns[cooldown] < 1:
                del self.cooldowns[cooldown]
            else:
                self.cooldowns[cooldown] -= 1

    async def awaiting_response(self, interaction: discord.Interaction, message: discord.Message):
        await interaction.response.defer(ephemeral=True)
        if not du.contains_roles(interaction.user.roles, ['Moderator']):
            return await interaction.followup.send(content=f'{cd.status_emoji_denied} You do not have the required permissions to use this option.', ephemeral=True)

        if interaction.channel.category.id != cd.ticket_category_id[interaction.guild.id]:
            return await interaction.followup.send(content=f'{cd.status_emoji_denied} This option can only be used within a help channel.', ephemeral=True)

        if self.cooldowns[message.channel.id] > 0:
            return await interaction.followup.send(
                content=f"{cd.status_emoji_denied} The remaining cooldown for this command is ``{self.cooldowns[message.channel.id]}`` second{'s' if self.cooldowns[message.channel.id] != 1 else ''}.",
                ephemeral=False)

        self.cooldowns[message.channel.id] = self.cooldown_value

        ticket_user = await du.get_user_by_original_message(interaction.channel)
        if ticket_user is None:
            return await interaction.followup.send(
                content=f'{cd.status_emoji_denied} Could not determine ticket owner.', ephemeral=True)

        await interaction.followup.send(content=f'Pinging user to check the channel.', ephemeral=True)
        await interaction.channel.send(content=f"Hey {ticket_user.mention}, just checking to see if you still need assistance.\n\n*If you no longer need assistance or the question/concern was resolved, feel free to close the ticket.*", view=vw.PViewSupport_Message())

    async def support_redirect(self, interaction: discord.Interaction, message: discord.Message):
        await interaction.response.defer(ephemeral=True)
        if not du.contains_roles(interaction.user.roles, ['Moderator']):
            return await interaction.followup.send(content=f'{cd.status_emoji_denied} You do not have the required permissions to use this option.', ephemeral=True)

        if interaction.channel.category.id == cd.ticket_category_id[interaction.guild.id]:
            return await interaction.followup.send(content=f'{cd.status_emoji_denied} Please continue using this channel to assist the user.', ephemeral=True)

        if self.cooldowns[message.id] > 0:
            return await interaction.followup.send(
                content=f"{cd.status_emoji_denied} The remaining cooldown for this command is ``{self.cooldowns[message.id]}`` second{'s' if self.cooldowns[message.id] != 1 else ''}.",
                ephemeral=False)

        channel = du.get_channel_by_id(self.bot, discord_guild_id=interaction.guild.id, channel_id=cd.stickied_channel[interaction.guild.id])
        await message.reply(content=f"{message.author.mention} To allow us to assist you as soon as possible, please check out {channel.mention}")
        await interaction.followup.send(content=f'{message.author.mention} has been redirected to {channel.mention}.', ephemeral=True)

    @app_commands.command(name="sync", description="(Admin) Sync the things.")
    async def sync(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        if not du.contains_roles(interaction.user.roles, ['Moderator']):
            return await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)

        await self.bot.tree.sync(guild=discord.Object(id=interaction.guild.id))
        await interaction.edit_original_response(content="Sync completed.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Data(bot), guilds=[discord.Object(id=cd.WOM_TEST_GUILD_ID), discord.Object(id=cd.WOM_GUILD_ID)])
