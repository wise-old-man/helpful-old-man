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

        self.sticky_message.start()

        self.support_title = "Need help from one of our moderators?"
        self.support_message_color = discord.Colour.dark_blue()
        self.support_footer = "As a reminder, all moderators and admins in this server volunteer to help in their free time.\nWe appreciate your patience."

    async def set_latest_support_message(self, guild_id):
        channel = du.get_channel_by_id(self.bot, discord_guild_id=guild_id, channel_id=cd.stickied_channel[guild_id])

        if channel is None:
            return

        channel_messages = [message async for message in channel.history(limit=None, oldest_first=False)]
        for message in channel_messages:
            if message.embeds:
                embed = message.embeds[0]
                if embed.title == self.support_title:
                    cd.latest_support_message[guild_id] = message.id
                    return

    @tasks.loop(seconds=5, count=None)
    async def sticky_message(self):
        await self.bot.wait_until_ready()

        for guild_id in cd.SUPPORTED_GUILD_IDS:
            await self.set_latest_support_message(guild_id)

            channel = du.get_channel_by_id(self.bot, discord_guild_id=guild_id, channel_id=cd.stickied_channel[guild_id])

            if channel is None:
                return

            channel_messages = [message async for message in channel.history(limit=None, oldest_first=False)]
            questions_channel = du.get_channel_by_name(self.bot, discord_guild_id=guild_id, channel_name='questions')
            questions_channel_mention_str = f"\n\nIf you'd like to ask a quick question, you may do so in the {questions_channel.mention} channel." if questions_channel else ''

            button_breakdown = f'\n\n**Groups** {cd.ARROW} Assistance on group related things\n- Verify my group\n- Reset my verification code\n- Remove me from a group\n- Other\n\n**Name Changes** {cd.ARROW} Help with name related things\n- Approve a pending name change\n- Delete name change history\n- Other\n\n**API Key** {cd.ARROW} Request an API key for development\n\n**Other** {cd.ARROW} Request assistance for all other inquiries'
            support_description = f"Select a support category below to request assistance.{button_breakdown}{questions_channel_mention_str}"

            if len(channel_messages) == 0:
                embed = discord.Embed(title=self.support_title, color=self.support_message_color)
                embed.description = support_description
                support_message = await channel.send(embed=embed, view=vw.PViewSupport())
                cd.latest_support_message = support_message.id
                return

            if channel_messages[0].id != cd.latest_support_message[guild_id]:
                if cd.latest_support_message[guild_id] is not None:
                    for message in channel_messages:
                        if message.id == cd.latest_support_message[guild_id]:
                            await message.delete()
                            break

                embed = discord.Embed(title=self.support_title, color=self.support_message_color)
                embed.description = support_description
                embed.set_footer(text=self.support_footer)
                support_message = await channel.send(embed=embed, view=vw.PViewSupport())
                cd.latest_support_message[guild_id] = support_message.id

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
