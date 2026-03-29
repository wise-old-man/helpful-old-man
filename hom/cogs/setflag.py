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
            country = country if country != "null" else None
            response = utils.set_flag(username, country)
            flag_emoji = utils.get_flag_emoji(country)
            if response.status_code == 200:
                title = f"{flag_emoji} Player flag updated!"
                color = Constants.GREEN
                if country == "null" or country is None:
                    description = f"{interaction.user.mention} unset `{username}`'s country"
                else:
                    description = (
                        f"{interaction.user.mention} changed `{username}`'s country to {country}"
                    )

            else:
                title = "Failed to update flag."
                color = Constants.RED
                description = "Failed to update flag"

            embed = discord.Embed(
                title=title,
                color=color,
                description=description,
            )
            embed.add_field(name="Username", value=username)
            embed.add_field(name="Country Code", value=country)
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f"This command can only be used in {channel.mention}.")


async def setup(bot: Bot) -> None:
    await bot.add_cog(SetFlag(bot))
