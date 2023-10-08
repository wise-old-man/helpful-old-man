import asyncio
import typing as t

import discord
from discord import AppCommandType
from discord import app_commands
from discord.ext import commands

from hom import utils
from hom.bot import Bot
from hom.cogs import views
from hom.config import Config
from hom.config import Constants


class Support(commands.GroupCog, name="support"):
    def __init__(self, bot: Bot) -> None:
        super().__init__()
        self.bot = bot
        self.ratelimit = 5
        self.ratelimits: t.Dict[int, bool] = {}
        self.support_footer = (
            "As a reminder, all moderators and admins in this server volunteer to help in their "
            "free time.\nWe appreciate your patience."
        )

        self.bot.tree.add_command(
            app_commands.ContextMenu(
                name="Support Redirect",
                callback=self.support_redirect,
                type=AppCommandType.message,
            )
        )

        self.bot.tree.add_command(
            app_commands.ContextMenu(
                name="Awaiting Response",
                callback=self.awaiting_response,
                type=AppCommandType.message,
            )
        )

    @commands.has_role("Moderator")
    @commands.command(name="sync")
    async def sync(self, ctx: commands.Context[commands.Bot]) -> None:
        await self.bot.sync()
        await ctx.channel.send("Commands synced!")

    @app_commands.guild_only()  # type: ignore
    @app_commands.describe(channel="The channel to send the embed to.")
    @app_commands.command(
        name="send", description="Send the support embed to a channel (Admin only)."
    )
    async def send(
        self, interaction: discord.Interaction[commands.Bot], channel: discord.TextChannel
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        assert interaction.guild

        if not await self.mod_check(interaction):
            return None

        embed = utils.build_support_embed(self.bot, interaction.guild.id)
        message = await channel.send(embed=embed, view=views.Support())
        await interaction.followup.send(f"Done! {message.jump_url}", ephemeral=True)

    async def clear_ratelimit(self, user_id: int) -> None:
        await asyncio.sleep(self.ratelimit)
        # del schedules deletion but does not guarantee the GC will remove the
        # entry immediately so we set the value to False until then
        self.ratelimits[user_id] = False
        del self.ratelimits[user_id]

    async def mod_check(self, interaction: discord.Interaction[commands.Bot]) -> bool:
        assert isinstance(interaction.user, discord.Member)

        if not (is_mod := utils.contains_roles(interaction.user.roles, "Moderator")):
            await interaction.followup.send(
                f"{Constants.DENIED} You are not allowed to do that.",
                ephemeral=True,
            )

        return is_mod

    async def category_check(
        self, interaction: discord.Interaction[commands.Bot], message: str, *, invert: bool = False
    ) -> bool:
        assert isinstance(interaction.channel, discord.TextChannel)
        if not interaction.channel.category:
            return False

        category_match = interaction.channel.category.id == Config.TICKET_CATEGORY
        if invert:
            category_match = not category_match

        if not category_match:
            await interaction.followup.send(f"{Constants.DENIED} {message}", ephemeral=True)

        return category_match

    async def concurrency_check(self, interaction: discord.Interaction[commands.Bot]) -> bool:
        if not self.ratelimits.get(interaction.user.id):
            self.ratelimits[interaction.user.id] = True
            await asyncio.create_task(self.clear_ratelimit(interaction.user.id))
            return True

        await interaction.followup.send(
            f"{Constants.DENIED} The command was used for this user in the past {self.ratelimit} seconds.",
            ephemeral=True,
        )

        return False

    async def get_og_user(
        self, interaction: discord.Interaction[commands.Bot]
    ) -> t.Optional[t.Union[discord.User, discord.Member]]:
        assert isinstance(interaction.channel, discord.TextChannel)

        if not (user := await utils.get_user_by_original_message(interaction.channel)):
            await interaction.followup.send(
                f"{Constants.DENIED} Could not determine ticket owner.", ephemeral=True
            )

        return user

    async def guard_mods_channels_and_concurrency(
        self,
        interaction: discord.Interaction[commands.Bot],
        category_message: str,
        *,
        invert: bool = False,
    ) -> bool:
        if not await self.mod_check(interaction):
            return False

        if not await self.category_check(interaction, category_message, invert=invert):
            return False

        if not await self.concurrency_check(interaction):
            return False

        return True

    async def awaiting_response(
        self, interaction: discord.Interaction[commands.Bot], message: discord.Message
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        if not await self.guard_mods_channels_and_concurrency(
            interaction, "This option can only be used within a help channel."
        ):
            return None

        if not (og_user := await self.get_og_user(interaction)):
            return None

        await interaction.followup.send(f"Pinging user to check the channel.", ephemeral=True)
        await message.channel.send(
            (
                f"Hey {og_user.mention}, just checking to see if you still need assistance.\n\n"
                "*If you no longer need assistance or the question/concern was resolved, feel "
                "free to close the ticket.*"
            ),
            view=views.SupportMessage(),
        )

    async def support_redirect(
        self, interaction: discord.Interaction[commands.Bot], message: discord.Message
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        assert interaction.guild

        if not await self.guard_mods_channels_and_concurrency(
            interaction, "Please continue using this channel to assist the user.", invert=True
        ):
            return None

        channel = utils.get_channel_by_id(self.bot, interaction.guild.id, Config.STICKY_CHANNEL)
        if not channel:
            await interaction.followup.send("Couldn't find sticky channel, this is a bug.")
            return None

        await message.reply(
            f"{message.author.mention} To allow us to assist you as soon as possible, please "
            f"check out {channel.mention}"
        )

        await interaction.followup.send(
            f"{message.author.mention} has been redirected to {channel.mention}.",
            ephemeral=True,
        )


async def setup(bot: Bot) -> None:
    await bot.add_cog(Support(bot))
