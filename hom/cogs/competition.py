from typing import List, Optional

import discord
import requests
from discord import app_commands
from discord.ext import commands

from hom import utils
from hom.bot import Bot
from hom.config import Config, Constants

__all__ = ("Competition",)


class Competition(commands.GroupCog, name="competition"):
    def __init__(self, bot: Bot) -> None:
        super().__init__()
        self.bot = bot

    async def competition_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[int]]:
        username = getattr(interaction.namespace, "username", None)

        if not username:
            return []

        url = f"{Config.DISCORD_BOT_BASE_API_URL}/players/{username}/competitions"

        response = requests.get(
            url=url,
            headers=Constants.HEADERS
        )

        if response.status_code != 200:
            return []

        data = response.json()
        search = current.lower().strip()
        choices: List[app_commands.Choice[int]] = []

        for competition in data:
            comp_id = competition.get("competitionId")
            comp_name = competition.get("competition", {}).get("title")

            if comp_id is None:
                continue

            comp_id_str = str(comp_id)

            if (
                not search
                or search in comp_id_str.lower()
            ):
                label = f"{comp_id} - {comp_name}"

                # Discord choice names have a max length of 100 chars
                if len(label) > 100:
                    label = label[:97] + "..."

                choices.append(
                    app_commands.Choice(name=label, value=int(comp_id))
                )

        return choices[:25]

    async def group_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[int]]:
        username = getattr(interaction.namespace, "username", None)

        if not username:
            return []

        url = f"{Config.DISCORD_BOT_BASE_API_URL}/players/{username}/groups"

        response = requests.get(
            url=url,
            headers=Constants.HEADERS,
        )

        if response.status_code != 200:
            return []

        data = response.json()
        search = current.lower().strip()
        choices: List[app_commands.Choice[int]] = []

        seen = set()

        for entry in data:
            group_id = entry.get("groupId")
            group_name = entry.get("group", {}).get("name", "")

            if group_id is None or group_id in seen:
                continue

            seen.add(group_id)

            if group_id is None:
                continue

            group_id_str = str(group_id)

            if (
                not search
                or search in group_id_str.lower()
                or search in group_name.lower()
            ):
                label = f"{group_id} - {group_name}"

                if len(label) > 100:
                    label = label[:97] + "..."

                choices.append(
                    app_commands.Choice(name=label, value=int(group_id))
                )

        return choices[:25]

    @app_commands.guild_only()
    @app_commands.describe(
        username="The username of the player you are removing from competitions.",
        group_id="The group id being used for removal of all group competitions.",
        competition_id="The competition to remove the player from.",
        requester="Requester's Discord user tag.",
    )
    @app_commands.autocomplete(
        competition_id=competition_autocomplete,
        group_id=group_autocomplete,
    )
    @app_commands.command(
        name="remove_from_competitions",
        description="[Mod 🔒]: Remove a player from group competition.",
    )
    async def remove_from_competitions(
        self,
        interaction: discord.Interaction[commands.Bot],
        username: str,
        group_id: Optional[int] = None,
        competition_id: Optional[int] = None,
        requester: Optional[discord.Member] = None,
    ) -> None:
        await interaction.response.defer()
        assert interaction.guild

        if not await utils.mod_check(interaction):
            return

        if group_id is not None and competition_id is not None:
            await interaction.followup.send(
                "Please enter only a group_id or a competition_id, not both.",
                ephemeral=True,
            )
            return

        if group_id is None and competition_id is None:
            await interaction.followup.send(
                "Please enter a Group ID or a Competition ID.",
                ephemeral=True,
            )
            return


        successful_competitions: List[str] = []
        error_competitions: List[str] = []
        skipped_competitions: List[str] = []

        if competition_id is not None:
            competition_link = (
                f"[{competition_id}]({Config.DISCORD_BOT_BASE_WEBSITE_URL}/competitions/{competition_id})"
            )
            response = requests.delete(
                url=f"{Config.DISCORD_BOT_BASE_API_URL}/competitions/{competition_id}/participants",
                json={
                    "participants": [username],
                    "adminPassword": Config.SHARED_ADMIN_PASSWORD,
                },
                headers=Constants.HEADERS,
            )

            if response.status_code != 200:
                if "cannot remove all competition participants" in response.text.lower():
                    skipped_competitions.append(competition_link)
                elif "none of the players given were competing" in response.text.lower():
                    skipped_competitions.append(competition_link + " (Player not found)")
                else:
                    error_competitions.append(
                        competition_link + f" {Constants.ARROW} ```{response.text}```"
                    )
            else:
                successful_competitions.append(competition_link)
        else:
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
                        headers=Constants.HEADERS,
                    )

                    if response.status_code != 200:
                        if "cannot remove all competition participants" in response.text.lower():
                            skipped_competitions.append(competition_link)
                        elif "none of the players given were competing" in response.text.lower():
                            skipped_competitions.append(competition_link + " (Player not found)")
                        else:
                            error_competitions.append(
                                competition_link + f" {Constants.ARROW} ```{response.text}```"
                            )
                        continue

                    successful_competitions.append(competition_link)

        if not any([successful_competitions, error_competitions, skipped_competitions]):
            await interaction.followup.send(
                f"No competitions were found for `{username}` under that group."
            )
            return

        embed = discord.Embed(
            title=f"Competition Removal: `{username}`",
            color=Constants.BLUE,
        )

        if successful_competitions:
            embed.add_field(
                name=f"{Constants.COMPLETE} Removed",
                value=", ".join(successful_competitions)[:1024],
                inline=False,
            )

        if error_competitions:
            embed.add_field(
                name=f"{Constants.DENIED} Errors",
                value="\n".join(error_competitions)[:1024],
                inline=False,
            )

        if skipped_competitions:
            embed.add_field(
                name="Skipped",
                value=", ".join(skipped_competitions)[:1024],
                inline=False,
            )

        await interaction.followup.send(embed=embed)

        requested_by = (
            f"\nRequested by: {requester.mention}, `{requester.id}`, `{requester.name}`"
            if requester
            else ""
        )
        await utils.send_log_message(
            interaction,
            f"Username: `{username}`\nSuccess Count: `{len(successful_competitions)}`\nSkipped Count: `{len(skipped_competitions)}`\nError Count: `{len(error_competitions)}`{requested_by}",
            title="Removed User From Group Competitions",
            mod=interaction.user,
        )


async def setup(bot: Bot) -> None:
    await bot.add_cog(Competition(bot))

