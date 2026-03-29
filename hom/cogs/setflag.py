import discord
from discord import app_commands
from discord.ext import commands

from hom import utils
from hom.bot import Bot
from hom.config import Config
from hom.config import Constants

__all__ = ("SetFlag",)


class SetFlag(commands.Cog, name="setflag"):
    def __init__(self, bot: Bot) -> None:
        super().__init__()
        self.bot = bot

    @app_commands.guild_only()  # type: ignore
    @app_commands.describe(
        username="Your in-game username.", country="Country name. Start typing to search."
    )
    @app_commands.autocomplete(country=utils.set_flag_autocomplete)
    @app_commands.command(description="Set your country/flag")
    async def setflag(
        self, interaction: discord.Interaction[commands.Bot], username: str, country: str
    ) -> None:
        await interaction.response.defer()
        assert interaction.guild

        channel = utils.get_channel(interaction.guild, Config.FLAG_CHANNEL)
        if not channel:
            await interaction.followup.send("Couldn't find change-flag channel, this is a bug.")
        elif interaction.channel == channel:
            country_name = utils.get_country_name(country)
            if country_name is None:
                embed = discord.Embed(
                    color=Constants.RED,
                    description="Invalid country. You must supply a valid country name or code, according to the ISO 3166-1 standard. Please see: https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2",
                )
                return None

            response = utils.set_flag(username, country)
            flag_emoji = utils.get_flag_emoji(country)
            if response.status_code == 200:
                title = f"{flag_emoji} Player flag updated!"
                if country == "null":
                    description = f"{interaction.user.mention} unset `{username}`'s country"
                else:
                    description = f"{interaction.user.mention} changed `{username}`'s country to `{country_name}`"

                embed = discord.Embed(title=title, color=Constants.GREEN, description=description)
                embed.add_field(name="Username", value=username)
                if country == "null":
                    value = "None"
                else:
                    value = country

                embed.add_field(name="Country Code", value=value)
            else:
                title = "Failed to update flag."
                description = "Failed to update flag"
                embed = discord.Embed(title=title, color=Constants.RED, description=description)

            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f"This command can only be used in {channel.mention}.")


async def setup(bot: Bot) -> None:
    await bot.add_cog(SetFlag(bot))
