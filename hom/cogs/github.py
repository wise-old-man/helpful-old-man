import typing as t

import discord
import requests
from discord import AppCommandType
from discord import app_commands
from discord.ext import commands

from hom import utils
from hom.bot import Bot
from hom.config import Config
from hom.config import Constants

__all__ = ("GitHub",)

HAS_MODAL_FILE_UPLOAD = hasattr(discord.ui, "FileUpload") and hasattr(discord.ui, "Label")


def _truncate(value: str, max_length: int) -> str:
    stripped = value.strip()
    if len(stripped) <= max_length:
        return stripped

    return stripped[: max_length - 3].rstrip() + "..."


def _is_mod(interaction: discord.Interaction[t.Any]) -> bool:
    return isinstance(interaction.user, discord.Member) and any(
        role.id == Config.MOD_ROLE for role in interaction.user.roles
    )


def _build_message_issue_title(message: discord.Message) -> str:
    title = f"{message.author.display_name} - Suggestion"
    return _truncate(title, 256)


def _get_actor_display_name(
    user: t.Union[discord.Member, discord.User, discord.ClientUser]
) -> str:
    if isinstance(user, discord.Member):
        return user.display_name

    return user.global_name or user.name


def _build_message_issue_body(message: discord.Message) -> str:
    lines = [f"Source message: {message.jump_url}"]

    content = message.clean_content.strip()
    if content:
        lines.extend(("", content))

    if message.attachments:
        lines.extend(("", "Attachments:"))
        lines.extend(attachment.url for attachment in message.attachments)

    return _truncate("\n".join(lines), 4000)


def _build_issue_body(
    body: str,
    image: t.Optional[discord.Attachment],
    created_by_display_name: str,
) -> str:
    issue_body = f"{body.strip()}\n\n---\nCreated by: {created_by_display_name}"

    if image is None:
        return issue_body

    attachment_lines = [
        "---",
        f"Attachment: [{image.filename}]({image.url})",
    ]

    if image.content_type and image.content_type.startswith("image/"):
        attachment_lines.extend(("", f"![{image.filename}]({image.url})"))

    return f"{issue_body}\n\n" + "\n".join(attachment_lines)


def _get_error_message(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        text = response.text.strip()
        return text or f"GitHub returned HTTP {response.status_code}."

    message = payload.get("message")
    if isinstance(message, str) and message.strip():
        return message

    errors = payload.get("errors")
    if isinstance(errors, list) and errors:
        details = ", ".join(str(error) for error in errors[:3])
        return f"GitHub returned validation errors: {details}"

    return f"GitHub returned HTTP {response.status_code}."


class CreateGitHubIssueModal(discord.ui.Modal):
    def __init__(
        self,
        cog: "GitHub",
        *,
        default_title: str,
        default_body: str,
        source_message: discord.Message,
    ) -> None:
        super().__init__(title="Create GitHub Issue")
        self.cog = cog
        self.source_message = source_message

        self.issue_title = discord.ui.TextInput(
            label="Issue title",
            default=default_title,
            min_length=1,
            max_length=256,
        )
        self.issue_body = discord.ui.TextInput(
            label="Issue body",
            default=default_body,
            style=discord.TextStyle.paragraph,
            min_length=1,
            max_length=4000,
        )
        self.issue_attachment: t.Optional[discord.ui.Item[t.Any]] = None

        self.add_item(self.issue_title)
        self.add_item(self.issue_body)

        if HAS_MODAL_FILE_UPLOAD:
            self.issue_attachment = discord.ui.FileUpload(
                required=False,
                min_values=0,
                max_values=1,
            )
            self.add_item(
                discord.ui.Label(
                    text="Attachment",
                    description="Optional file to include in the GitHub issue.",
                    component=self.issue_attachment,
                )
            )

    async def on_submit(self, interaction: discord.Interaction[t.Any]) -> None:
        if not _is_mod(interaction):
            await interaction.response.send_message(
                f"{Constants.DENIED} You are not allowed to do that.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "Creating GitHub issue...",
            ephemeral=True,
        )
        await self.cog.create_issue_from_values(
            interaction,
            title=self.issue_title.value,
            body=self.issue_body.value,
            image=(
                self.issue_attachment.values[0]
                if self.issue_attachment is not None and self.issue_attachment.values
                else None
            ),
            source_message=self.source_message,
            public_success_response=True,
        )


class GitHub(commands.GroupCog, name="github"):
    def __init__(self, bot: Bot) -> None:
        super().__init__()
        self.bot = bot
        self.bot.tree.add_command(
            app_commands.ContextMenu(
                name="Create GitHub Issue",
                callback=self.create_from_message,
                type=AppCommandType.message,
            )
        )

    @staticmethod
    def _get_repository_config() -> t.Optional[t.Tuple[str, str]]:
        repository = Config.GITHUB_REPOSITORY
        token = Config.GITHUB_TOKEN
        if not repository or not token:
            return None

        return repository, token

    async def create_issue_from_values(
        self,
        interaction: discord.Interaction[commands.Bot],
        *,
        title: str,
        body: str,
        image: t.Optional[discord.Attachment] = None,
        source_message: t.Optional[discord.Message] = None,
        public_success_response: bool = False,
    ) -> None:
        async def send_error(message: str) -> None:
            if public_success_response:
                await interaction.edit_original_response(content=message)
            else:
                await interaction.followup.send(message, ephemeral=True)

        config = self._get_repository_config()
        if config is None:
            await send_error(
                "GitHub issue creation is not configured yet. Set `HOM_GITHUB_REPOSITORY` "
                "and `HOM_GITHUB_TOKEN` first."
            )
            return

        repository, token = config
        cleaned_title = title.strip()
        cleaned_body = body.strip()

        if not cleaned_title or not cleaned_body:
            await send_error("The title and body cannot be blank.")
            return

        try:
            response = requests.post(
                url=f"https://api.github.com/repos/{repository}/issues",
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {token}",
                    "User-Agent": "Helpful Old Man Discord Bot",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                json={
                    "title": cleaned_title,
                    "body": _build_issue_body(
                        cleaned_body,
                        image,
                        _get_actor_display_name(interaction.user),
                    ),
                },
                timeout=15,
            )
        except requests.RequestException as exc:
            await send_error(f"GitHub could not be reached right now.\n```{str(exc)[:1800]}```")
            return

        if response.status_code != 201:
            error_message = _get_error_message(response)
            await send_error(
                f"Failed to create an issue in `{repository}`.\n```{error_message[:1800]}```"
            )
            return

        payload = response.json()
        issue_number = payload["number"]
        issue_url = payload["html_url"]

        embed = discord.Embed(
            title="GitHub issue created",
            color=Constants.GREEN,
            description=f"[#{issue_number}]({issue_url}) {cleaned_title}",
        )
        embed.add_field(name="Repository", value=repository, inline=False)
        if source_message is not None:
            embed.add_field(
                name="Source message",
                value=f"[Open message]({source_message.jump_url})",
                inline=False,
            )
        if image is not None:
            embed.add_field(name="Image", value=f"[{image.filename}]({image.url})", inline=False)
        embed.add_field(
            name="Created by",
            value=_get_actor_display_name(interaction.user),
            inline=False,
        )

        if public_success_response:
            if source_message is not None:
                try:
                    await source_message.reply(embed=embed, mention_author=False)
                    await interaction.delete_original_response()
                except discord.HTTPException:
                    await interaction.edit_original_response(
                        content=(
                            "GitHub issue was created, but I couldn't post the public reply.\n"
                            f"[#{issue_number}]({issue_url}) {cleaned_title}"
                        ),
                    )
            else:
                try:
                    channel = t.cast(discord.abc.Messageable, interaction.channel)
                    await channel.send(embed=embed)
                    await interaction.delete_original_response()
                except (AttributeError, discord.HTTPException):
                    await interaction.edit_original_response(
                        content=(
                            "GitHub issue was created, but I couldn't post the public message.\n"
                            f"[#{issue_number}]({issue_url}) {cleaned_title}"
                        ),
                    )
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)

        source_message_line = (
            f"\nSource message: {source_message.jump_url}" if source_message is not None else ""
        )
        await utils.send_log_message(
            interaction,
            (
                f"Issue: [#{issue_number}]({issue_url})\n"
                f"Repository: `{repository}`\n"
                f"Title: `{cleaned_title}`{source_message_line}"
            ),
            title="Created GitHub Issue",
            mod=interaction.user,
        )

    @app_commands.guild_only()  # type: ignore[arg-type]
    @app_commands.describe(
        title="Issue title.",
        body="Issue details.",
        image="Optional image attachment to include in the issue body.",
    )
    @app_commands.command(
        name="create",
        description="[Mod]: Create a GitHub issue.",
    )
    async def create(
        self,
        interaction: discord.Interaction[commands.Bot],
        title: app_commands.Range[str, 1, 256],
        body: app_commands.Range[str, 1, 4000],
        image: t.Optional[discord.Attachment] = None,
    ) -> None:
        if not _is_mod(interaction):
            await interaction.response.send_message(
                f"{Constants.DENIED} You are not allowed to do that.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "Creating GitHub issue...",
            ephemeral=True,
        )
        await self.create_issue_from_values(
            interaction,
            title=title,
            body=body,
            image=image,
            public_success_response=True,
        )

    async def create_from_message(
        self,
        interaction: discord.Interaction[commands.Bot],
        message: discord.Message,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "This action can only be used in a server.",
                ephemeral=True,
            )
            return

        if not _is_mod(interaction):
            await interaction.response.send_message(
                f"{Constants.DENIED} You are not allowed to do that.",
                ephemeral=True,
            )
            return

        if self._get_repository_config() is None:
            await interaction.response.send_message(
                "GitHub issue creation is not configured yet. Set `HOM_GITHUB_REPOSITORY` "
                "and `HOM_GITHUB_TOKEN` first.",
                ephemeral=True,
            )
            return

        await interaction.response.send_modal(
            CreateGitHubIssueModal(
                self,
                default_title=_build_message_issue_title(message),
                default_body=_build_message_issue_body(message),
                source_message=message,
            )
        )


async def setup(bot: Bot) -> None:
    await bot.add_cog(GitHub(bot))
