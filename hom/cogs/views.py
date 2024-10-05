import typing as t

import discord
from discord.ext import commands

from hom import utils
from hom.config import Config
from hom.config import Constants

__all__ = (
    "Support",
    "SupportCompetition",
    "SupportGroup",
    "SupportMessage",
    "SupportMessageCloseChannel",
    "SupportNames",
    "Verify",
)

ViewT = t.TypeVar("ViewT", bound=discord.ui.View)


class Support(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Groups",
        style=discord.ButtonStyle.green,
        custom_id="persistent_view:groups_instructions",
    )
    async def groups_instructions(
        self: ViewT, interaction: discord.Interaction[commands.Bot], _: discord.ui.Button[ViewT]
    ) -> None:
        await interaction.response.send_message(
            view=SupportGroup(),
            content="What do you need assistance with?",
            ephemeral=True,
        )

    @discord.ui.button(
        label="Competitions",
        style=discord.ButtonStyle.green,
        custom_id="persistent_view:competitions_instructions",
    )
    async def competitions_instructions(
        self: ViewT, interaction: discord.Interaction[commands.Bot], _: discord.ui.Button[ViewT]
    ) -> None:
        await interaction.response.send_message(
            view=SupportCompetition(),
            content="What do you need assistance with?",
            ephemeral=True,
        )

    @discord.ui.button(
        label="Name Changes",
        style=discord.ButtonStyle.green,
        custom_id="persistent_view:names_instructions",
    )
    async def names_instructions(
        self: ViewT, interaction: discord.Interaction[commands.Bot], _: discord.ui.Button[ViewT]
    ) -> None:
        await interaction.response.send_message(
            view=SupportNames(),
            content="What do you need assistance with?",
            ephemeral=True,
        )

    @discord.ui.button(
        label="Patreon", style=discord.ButtonStyle.green, custom_id="persistent_view:patreon"
    )
    async def patreon(
        self: ViewT,
        interaction: discord.Interaction[commands.Bot],
        button: discord.ui.Button[ViewT],
    ) -> None:
        instructions = (
            "If you are interested in claiming or signing up for patreon benefits, check out "
            f"<#{Config.PATREON_CHANNEL}> for more information.\n\nIf you've already signed up, "
            "**thanks so much for your support**! It means a lot to us that you enjoy using "
            f"Wise Old Man. Feel free to ask any questions you have here.\n\n{Constants.FOOTER}"
        )

        await interaction.response.defer()
        await utils.create_ticket_for_user(interaction, instructions, button.label)

    @discord.ui.button(
        label="API Key",
        style=discord.ButtonStyle.green,
        custom_id="persistent_view:api_key",
    )
    async def api_key(
        self: ViewT,
        interaction: discord.Interaction[commands.Bot],
        button: discord.ui.Button[ViewT],
    ) -> None:
        instructions = (
            "If you'd like to get an API Key, please tell us your project's name and we'll create "
            f"you a new API key.\n\n{Constants.FOOTER}"
        )

        await interaction.response.defer()
        await utils.create_ticket_for_user(interaction, instructions, button.label)

    @discord.ui.button(
        label="Other",
        style=discord.ButtonStyle.green,
        custom_id="persistent_view:other_instructions",
    )
    async def other_instructions(
        self: ViewT, interaction: discord.Interaction[commands.Bot], _: discord.ui.Button[ViewT]
    ) -> None:
        await interaction.response.defer()
        instructions = f"Explain what you require assistance with below.\n\n{Constants.FOOTER}"
        await utils.create_ticket_for_user(interaction, instructions, f"Other")


class Verify(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Yes",
        style=discord.ButtonStyle.red,
        custom_id="persistent_view:verify_yes",
    )
    async def verify_yes(
        self: ViewT, interaction: discord.Interaction[commands.Bot], _: discord.ui.Button[ViewT]
    ) -> None:
        await interaction.response.send_message(
            f"{Constants.COMPLETE} Closing this ticket.", ephemeral=True
        )

        assert isinstance(interaction.channel, discord.TextChannel)
        await interaction.channel.delete()


class SupportGroup(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Verify my group",
        style=discord.ButtonStyle.blurple,
        custom_id="persistent_view:group_verify",
    )
    async def group_verify(
        self: ViewT,
        interaction: discord.Interaction[commands.Bot],
        button: discord.ui.Button[ViewT],
    ) -> None:
        instructions = (
            "To verify your group, please provide a screenshot to prove ownership. We have "
            "attached an example of what we need to see below. The screenshot must "
            "contain:\n\n- Your Wise Old Man group ID (found in that group's page URL), "
            "your Discord ID, and today's date typed into your in-game chatbox.\n- Your Clan "
            "tab open showing your username and rank. For clans, you must be Owner or Deputy "
            "Owner to verify the group. For the old clan chat, you must be Owner or General "
            f"(gold star).\n\n{Constants.FOOTER}"
        )

        await interaction.response.defer()
        await utils.create_ticket_for_user(
            interaction,
            instructions,
            f"Groups {Constants.ARROW} {button.label}",
            "https://cdn.discordapp.com/attachments/696219254076342312/1200157429283962880/group.jpg",
        )

    @discord.ui.button(
        label="Reset my verification code",
        style=discord.ButtonStyle.blurple,
        custom_id="persistent_view:group_reset_code",
    )
    async def group_reset_code(
        self: ViewT,
        interaction: discord.Interaction[commands.Bot],
        button: discord.ui.Button[ViewT],
    ) -> None:
        instructions = (
            "To reset your verification code, please provide a screenshot to prove ownership. "
            "We have attached an example of what we need to see below. The screenshot must "
            "contain:\n\n- Your Wise Old Man group ID (found in that group's page URL), your "
            "Discord ID, and today's date typed into your in-game chatbox.\n- Your Clan tab "
            "open showing your username and rank. For clans, you must be Owner or Deputy Owner "
            "to verify the group. For the old clan chat, you must be Owner or General (gold star)."
            "\n\nKeep in mind that verification codes should be secret, they can be used to edit "
            "or delete a group, so please be mindful of who you choose to share it with.\n\n"
            f"{Constants.FOOTER}"
        )

        await interaction.response.defer()
        await utils.create_ticket_for_user(
            interaction,
            instructions,
            f"Groups {Constants.ARROW} {button.label}",
            "https://cdn.discordapp.com/attachments/696219254076342312/1200157429283962880/group.jpg",
        )

    @discord.ui.button(
        label="Remove me from a group",
        style=discord.ButtonStyle.blurple,
        custom_id="persistent_view:group_remove",
    )
    async def group_remove(
        self: ViewT,
        interaction: discord.Interaction[commands.Bot],
        button: discord.ui.Button[ViewT],
    ) -> None:
        instructions = (
            "To remove yourself from a group, please provide us with a screenshot containing:"
            "\n\n- Your in-game username\n- Your Discord username/ID\n- Today's date\n\n"
            f"{Constants.FOOTER}"
        )

        await interaction.response.defer()
        await utils.create_ticket_for_user(
            interaction,
            instructions,
            f"Groups {Constants.ARROW} {button.label}",
            "https://cdn.discordapp.com/attachments/696219254076342312/1200157428981977229/player.jpg",
        )

    @discord.ui.button(
        label="Other",
        style=discord.ButtonStyle.blurple,
        custom_id="persistent_view:group_other",
    )
    async def group_other(
        self: ViewT,
        interaction: discord.Interaction[commands.Bot],
        button: discord.ui.Button[ViewT],
    ) -> None:
        instructions = f"Explain what you require assistance with below.\n\n{Constants.FOOTER}"

        await interaction.response.defer()
        await utils.create_ticket_for_user(
            interaction, instructions, f"Groups {Constants.ARROW} {button.label}"
        )


class SupportCompetition(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Reset my verification code",
        style=discord.ButtonStyle.blurple,
        custom_id="persistent_view:competition_reset_code",
    )
    async def competition_reset_code(
        self: ViewT,
        interaction: discord.Interaction[commands.Bot],
        button: discord.ui.Button[ViewT],
    ) -> None:
        instructions = (
            "To reset your verification code, please provide us with a screenshot containing:"
            "\n\n- Your in-game username\n- Your Discord username/ID\n- Today's date\n\n"
            "Keep in mind that verification codes should be secret, they can be used to edit "
            "or delete a competition, so please be mindful of who you choose to share it with.\n\n"
            "Note: If this competition was created through a group, then the verification code is "
            f"the same as your group's verification code.\n\n{Constants.FOOTER}"
        )

        await interaction.response.defer()
        await utils.create_ticket_for_user(
            interaction,
            instructions,
            f"Competitions {Constants.ARROW} {button.label}",
            "https://cdn.discordapp.com/attachments/696219254076342312/1200157428981977229/player.jpg",
        )

    @discord.ui.button(
        label="Remove me from a competition",
        style=discord.ButtonStyle.blurple,
        custom_id="persistent_view:competition_remove",
    )
    async def competition_remove(
        self: ViewT,
        interaction: discord.Interaction[commands.Bot],
        button: discord.ui.Button[ViewT],
    ) -> None:
        instructions = (
            "To remove yourself from a competition, please provide us with a screenshot containing:"
            "\n\n- Your in-game username\n- Your Discord username/ID\n- Today's date\n\n"
            f"{Constants.FOOTER}"
        )

        await interaction.response.defer()
        await utils.create_ticket_for_user(
            interaction,
            instructions,
            f"Competitions {Constants.ARROW} {button.label}",
            "https://cdn.discordapp.com/attachments/696219254076342312/1200157428981977229/player.jpg",
        )

    @discord.ui.button(
        label="Other",
        style=discord.ButtonStyle.blurple,
        custom_id="persistent_view:competition_other",
    )
    async def competition_other(
        self: ViewT,
        interaction: discord.Interaction[commands.Bot],
        button: discord.ui.Button[ViewT],
    ) -> None:
        instructions = f"Explain what you require assistance with below.\n\n{Constants.FOOTER}"

        await interaction.response.defer()
        await utils.create_ticket_for_user(
            interaction, instructions, f"Competitions {Constants.ARROW} {button.label}"
        )


class SupportNames(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Approve a pending name change",
        style=discord.ButtonStyle.blurple,
        custom_id="persistent_view:names_approve",
    )
    async def names_approve(
        self: ViewT,
        interaction: discord.Interaction[commands.Bot],
        button: discord.ui.Button[ViewT],
    ) -> None:
        instructions = (
            "Some name changes get skipped, as they can't be auto-approved by our system and "
            "require manual approval.\n\nIf yours hasn't been auto-approved, please tell us the "
            "name change ID and we'll manually review it for you.\n\nNote: If you'd like to know "
            "why your name change has been skipped you can visit our website at "
            "https://wiseoldman.net/names and hover your cursor over your "
            f"name change's ℹ️ icon.\n\n{Constants.FOOTER}"
        )

        await interaction.response.defer()
        await utils.create_ticket_for_user(
            interaction, instructions, f"Name Changes {Constants.ARROW} {button.label}"
        )

    @discord.ui.button(
        label="Delete name change history",
        style=discord.ButtonStyle.blurple,
        custom_id="persistent_view:names_delete",
    )
    async def names_delete(
        self: ViewT,
        interaction: discord.Interaction[commands.Bot],
        button: discord.ui.Button[ViewT],
    ) -> None:
        instructions = (
            "To request a name change history deletion, please provide us with:\n\n- Your in-game "
            f"username\n- Your Discord username/ID\n- Today's date\n\n{Constants.FOOTER}"
        )

        await interaction.response.defer()
        await utils.create_ticket_for_user(
            interaction,
            instructions,
            f"Name Changes {Constants.ARROW} {button.label}",
            "https://cdn.discordapp.com/attachments/696219254076342312/1200157428981977229/player.jpg",
        )

    @discord.ui.button(
        label="Other",
        style=discord.ButtonStyle.blurple,
        custom_id="persistent_view:names_other",
    )
    async def names_other(
        self: ViewT,
        interaction: discord.Interaction[commands.Bot],
        button: discord.ui.Button[ViewT],
    ) -> None:
        instructions = f"Explain what you require assistance with below.\n\n{Constants.FOOTER}"

        await interaction.response.defer()
        await utils.create_ticket_for_user(
            interaction, instructions, f"Name Changes {Constants.ARROW} {button.label}"
        )


class SupportMessage(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        emoji="\N{LOCK}",
        label="Close",
        style=discord.ButtonStyle.blurple,
        custom_id="persistent_view:message_close",
    )
    async def message_close(
        self: ViewT, interaction: discord.Interaction[commands.Bot], _: discord.ui.Button[ViewT]
    ) -> None:
        assert isinstance(interaction.channel, discord.TextChannel)
        assert isinstance(interaction.user, discord.Member)

        embed = discord.Embed(description=f"{interaction.user.mention} has closed the ticket.")
        await interaction.response.defer()
        await interaction.channel.set_permissions(interaction.user, overwrite=None)
        await interaction.followup.send(
            ephemeral=False, embed=embed, view=SupportMessageCloseChannel()
        )


class SupportMessageCloseChannel(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        emoji=Constants.DENIED,
        label="Close Channel",
        style=discord.ButtonStyle.blurple,
        custom_id="persistent_view:message_close_channel",
    )
    async def message_close_channel(
        self: ViewT, interaction: discord.Interaction[commands.Bot], _: discord.ui.Button[ViewT]
    ) -> None:
        await interaction.response.defer()
        assert isinstance(interaction.channel, discord.channel.TextChannel)
        assert isinstance(interaction.user, discord.Member)

        if not any(r.id == Config.MOD_ROLE for r in interaction.user.roles):
            await interaction.followup.send(
                ephemeral=True,
                content="You do not have the required permissions to delete the channel.",
            )

            return None

        content = f"({interaction.channel.topic}) Ticket channel closed for user:\n"
        if user := await utils.get_user_by_original_message(interaction.channel):
            content += f"{user.display_name} - {user.mention}"

        await utils.send_log_message(
            interaction=interaction,
            content=content,
            mod=interaction.user,
            channel=interaction.channel,
        )
        await interaction.channel.delete()


async def setup(bot: commands.Bot) -> None:
    bot.add_view(Support())
    bot.add_view(SupportCompetition())
    bot.add_view(SupportGroup())
    bot.add_view(SupportMessage())
    bot.add_view(SupportMessageCloseChannel())
    bot.add_view(SupportNames())
    bot.add_view(Verify())
