from typing import Optional

import discord
import requests
from discord import app_commands
from discord.ext import commands

from hom import utils
from hom.bot import Bot
from hom.config import Config
from hom.config import Constants

__all__ = ("Competition",)


class Competition(commands.GroupCog, name="competition"):
    def __init__(self, bot: Bot) -> None:
        super().__init__()
        self.bot = bot

    @app_commands.guild_only()  # type: ignore
    @app_commands.describe(
        username="The username of the player you are removing from competitions."
    )
    @app_commands.describe(
        group_id="The group id being used for removal of all group competitions."
    )
    @app_commands.describe(requester="Requester's Discord user tag.")
    @app_commands.command(
        name="remove_from_group_competitions",
        description="[Mod :lock:]: Remove a player from group competitions.",
    )
    async def remove_from_group_competitions(
        self,
        interaction: discord.Interaction[commands.Bot],
        username: str,
        group_id: int,
        requester: Optional[discord.Member] = None,
    ) -> None:
        await interaction.response.defer()
        assert interaction.guild

        if not await utils.mod_check(interaction):
            return None

        url = f"{Config.DISCORD_BOT_BASE_API_URL}/players/{username}/competitions"
        response = requests.get(
            url=url,
            headers=Constants.HEADERS,
        )

        if response.status_code != 200:
            await interaction.followup.send(
                f"Could not find any competitions related to the username: `{username}`."
            )
            return

        successful_competitions: list[str] = []
        error_competitions: list[str] = []
        for comp in response.json():
            comp_id = comp["competitionId"]
            competition_link = (
                f"[{comp_id}]({Config.DISCORD_BOT_BASE_WEBSITE_URL}/competitions/{comp_id})"
            )

            if group_id == comp["competition"]["groupId"]:
                response = requests.delete(
                    url=f"{Config.DISCORD_BOT_BASE_API_URL}/competitions/{comp_id}/participants",
                    json={
                        "participants": [username],
                        "adminPassword": Config.SHARED_ADMIN_PASSWORD,
                    },
                )

                if response.status_code != 200:
                    error_competitions.append(
                        competition_link + f" {Constants.ARROW} ```{response.text}```"
                    )
                    continue

                successful_competitions.append(competition_link)

        success_message = (
            f"Successfully removed `{username}` from the following competitions: "
            + ", ".join(successful_competitions)[:1900]
        )
        error_message = (
            f"Could not remove `{username}` from the following competitions: "
            + "\n, ".join(error_competitions)[:1900]
        )

        channel_to_send = interaction.channel

        if isinstance(
            channel_to_send,
            (
                discord.TextChannel,
                discord.VoiceChannel,
                discord.StageChannel,
                discord.Thread,
                discord.DMChannel,
                discord.GroupChannel,
            ),
        ):
            if successful_competitions:
                await channel_to_send.send(success_message)
            if error_competitions:
                await channel_to_send.send(error_message)

        await interaction.followup.send(
            f"{Constants.COMPLETE} Processed request.",
        )

        requested_by = (
            f"\nRequested by: {requester.mention}, `{requester.id}`, `{requester.name}`"
            if requester
            else ""
        )
        await utils.send_log_message(
            interaction,
            f"Username: `{username}`\nSuccess Count: `{len(successful_competitions)}`\nError Count: `{len(error_competitions)}`{requested_by}",
            title="Removed User From Group Competitions",
            mod=interaction.user,
        )


async def setup(bot: Bot) -> None:
    await bot.add_cog(Competition(bot))
