import time
import typing as t
from datetime import datetime

import discord
import jwt
import requests
from discord import AppCommandType
from discord import app_commands
from discord.ext import commands

from hom import utils
from hom.bot import Bot
from hom.config import Config
from hom.config import Constants

__all__ = ("GitHub",)

HAS_MODAL_LABEL = hasattr(discord.ui, "Label")
HAS_MODAL_FILE_UPLOAD = HAS_MODAL_LABEL and hasattr(discord.ui, "FileUpload")
GITHUB_REPOSITORY_OPTIONS: t.Final[t.List[discord.SelectOption]] = [
    discord.SelectOption(label=repository, value=repository)
    for repository in Config.HOM_GITHUB_REPOSITORIES
]
GITHUB_REPOSITORY_CHOICES: t.Final[t.List[app_commands.Choice[str]]] = [
    app_commands.Choice(name=repository, value=repository)
    for repository in Config.HOM_GITHUB_REPOSITORIES
]
GITHUB_API_VERSION: t.Final[str] = "2022-11-28"
GITHUB_APP_CONFIGURATION_MESSAGE: t.Final[str] = (
    "GitHub issue creation is not configured yet. Set `HOM_GITHUB_APP_ID` and "
    "`HOM_GITHUB_PRIVATE_KEY` first."
)
_INSTALLATION_IDS_BY_REPOSITORY: t.Dict[str, int] = {}
_INSTALLATION_TOKENS_BY_ID: t.Dict[int, t.Tuple[str, float]] = {}


class GitHubAppAuthError(RuntimeError):
    pass


def _load_github_private_key() -> str:
    raw_value = Config.HOM_GITHUB_PRIVATE_KEY
    if raw_value:
        stripped = raw_value.strip()
        if stripped:
            return stripped.replace("\\n", "\n")

    raise GitHubAppAuthError(GITHUB_APP_CONFIGURATION_MESSAGE)


def _get_app_jwt() -> str:
    if not Config.HOM_GITHUB_APP_ID:
        raise GitHubAppAuthError(GITHUB_APP_CONFIGURATION_MESSAGE)

    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + 600,
        "iss": Config.HOM_GITHUB_APP_ID,
    }

    try:
        return jwt.encode(
            payload,
            _load_github_private_key(),
            algorithm="RS256",
        )
    except Exception as exc:
        raise GitHubAppAuthError(
            "GitHub App authentication could not generate a JWT from the configured "
            "private key.\n"
            f"```{str(exc)[:1800]}```"
        ) from exc


def _parse_github_timestamp(value: str) -> t.Optional[float]:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _get_installation_id(repository: str, app_jwt: str) -> int:
    cached_installation_id = _INSTALLATION_IDS_BY_REPOSITORY.get(repository)
    if cached_installation_id is not None:
        return cached_installation_id

    try:
        response = requests.get(
            url=f"https://api.github.com/repos/{repository}/installation",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {app_jwt}",
                "User-Agent": "Helpful Old Man Discord Bot",
                "X-GitHub-Api-Version": GITHUB_API_VERSION,
            },
            timeout=15,
        )
    except requests.RequestException as exc:
        raise GitHubAppAuthError(
            "GitHub App authentication could not reach GitHub while looking up the "
            "repository installation.\n"
            f"```{str(exc)[:1800]}```"
        ) from exc

    if response.status_code != 200:
        error_message = _get_error_message(response)
        raise GitHubAppAuthError(
            "Could not find a GitHub App installation for the selected repository. "
            "Make sure the app is installed on that repository.\n"
            f"```{error_message[:1800]}```"
        )

    payload_obj = response.json()
    if not isinstance(payload_obj, dict):
        raise GitHubAppAuthError("GitHub returned an unexpected installation lookup response.")

    installation_payload = t.cast(t.Dict[str, t.Any], payload_obj)
    installation_id = installation_payload.get("id")
    if not isinstance(installation_id, int):
        raise GitHubAppAuthError("GitHub returned an unexpected installation lookup response.")

    _INSTALLATION_IDS_BY_REPOSITORY[repository] = installation_id
    return installation_id


def _get_installation_token(repository: str) -> str:
    app_jwt = _get_app_jwt()
    installation_id = _get_installation_id(repository, app_jwt)

    cached_token = _INSTALLATION_TOKENS_BY_ID.get(installation_id)
    if cached_token is not None:
        cached_token_value, cached_expiry_timestamp = cached_token
        if time.time() < cached_expiry_timestamp - 60:
            return cached_token_value

    try:
        response = requests.post(
            url=f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {app_jwt}",
                "User-Agent": "Helpful Old Man Discord Bot",
                "X-GitHub-Api-Version": GITHUB_API_VERSION,
            },
            timeout=15,
        )
    except requests.RequestException as exc:
        raise GitHubAppAuthError(
            "GitHub App authentication could not reach GitHub while requesting an "
            "installation token.\n"
            f"```{str(exc)[:1800]}```"
        ) from exc

    if response.status_code != 201:
        error_message = _get_error_message(response)
        raise GitHubAppAuthError(
            "GitHub rejected the installation token request.\n" f"```{error_message[:1800]}```"
        )

    payload_obj = response.json()
    if not isinstance(payload_obj, dict):
        raise GitHubAppAuthError("GitHub returned an unexpected installation token response.")

    token_payload = t.cast(t.Dict[str, t.Any], payload_obj)
    token_value = token_payload.get("token")
    expires_at_value = token_payload.get("expires_at")
    if not isinstance(token_value, str) or not isinstance(expires_at_value, str):
        raise GitHubAppAuthError("GitHub returned an unexpected installation token response.")

    expiry_timestamp = _parse_github_timestamp(expires_at_value)
    if expiry_timestamp is None:
        expiry_timestamp = time.time() + 3600

    _INSTALLATION_TOKENS_BY_ID[installation_id] = (token_value, expiry_timestamp)
    return token_value


def _truncate(value: str, max_length: int) -> str:
    stripped = value.strip()
    if len(stripped) <= max_length:
        return stripped

    return stripped[: max_length - 3].rstrip() + "..."


def _is_mod(interaction: discord.Interaction[t.Any]) -> bool:
    return isinstance(interaction.user, discord.Member) and any(
        role.id == Config.HOM_MOD_ROLE for role in interaction.user.roles
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
    issue_body = body.strip()

    if image is None:
        return f"{issue_body}\n\n---\nCreated by: {created_by_display_name}"

    attachment_lines = [
        "---",
        f"Attachment: [{image.filename}]({image.url})",
    ]

    if image.content_type and image.content_type.startswith("image/"):
        attachment_lines.extend(("", f"![{image.filename}]({image.url})"))

    return (
        f"{issue_body}\n\n"
        + "\n".join(attachment_lines)
        + f"\n\n---\nCreated by: {created_by_display_name}"
    )


def _get_error_message(response: requests.Response) -> str:
    try:
        payload_obj = response.json()
    except ValueError:
        text = response.text.strip()
        return text or f"GitHub returned HTTP {response.status_code}."

    if not isinstance(payload_obj, dict):
        return f"GitHub returned HTTP {response.status_code}."

    payload: t.Mapping[str, t.Any] = payload_obj
    message = payload.get("message")
    if isinstance(message, str) and message.strip():
        return message

    errors = payload.get("errors")
    if isinstance(errors, list) and errors:
        typed_errors = t.cast(t.Sequence[t.Any], errors)
        details = ", ".join(str(error) for error in typed_errors[:3])
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

        self.issue_repository: discord.ui.Select[t.Any] = discord.ui.Select(
            placeholder="Select a repository...",
            options=GITHUB_REPOSITORY_OPTIONS,
            min_values=1,
            max_values=1,
            required=True,
        )
        self.issue_title: discord.ui.TextInput[t.Any] = discord.ui.TextInput(
            label="Issue title",
            default=default_title,
            min_length=1,
            max_length=256,
        )
        self.issue_body: discord.ui.TextInput[t.Any] = discord.ui.TextInput(
            label="Issue body",
            default=default_body,
            style=discord.TextStyle.paragraph,
            min_length=1,
            max_length=4000,
        )
        self.issue_attachment: t.Optional[t.Any] = None

        self.add_item(
            discord.ui.Label(
                text="Repository",
                description="Required repository for this issue.",
                component=self.issue_repository,
            )
        )
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
            repository=self.issue_repository.values[0],
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
    def _is_allowed_repository(repository: str) -> bool:
        return repository in Config.HOM_GITHUB_REPOSITORIES

    async def create_issue_from_values(
        self,
        interaction: discord.Interaction[commands.Bot],
        *,
        repository: str,
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

        if not Config.HOM_GITHUB_REPOSITORIES:
            await send_error(
                "GitHub issue creation is not configured yet. Set `HOM_GITHUB_REPOSITORIES` first."
            )
            return

        if not self._is_allowed_repository(repository):
            await send_error("Please select one of the configured GitHub repositories.")
            return

        cleaned_title = title.strip()
        cleaned_body = body.strip()

        if not cleaned_title or not cleaned_body:
            await send_error("The title and body cannot be blank.")
            return

        try:
            token = _get_installation_token(repository)
        except GitHubAppAuthError as exc:
            await send_error(str(exc))
            return

        try:
            response = requests.post(
                url=f"https://api.github.com/repos/{repository}/issues",
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {token}",
                    "User-Agent": "Helpful Old Man Discord Bot",
                    "X-GitHub-Api-Version": GITHUB_API_VERSION,
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
        repository="The GitHub repository to create the issue in.",
        title="Issue title.",
        body="Issue details.",
        image="Optional image attachment to include in the issue body.",
    )
    @app_commands.choices(repository=GITHUB_REPOSITORY_CHOICES)
    @app_commands.command(
        name="create",
        description="[Mod]: Create a GitHub issue.",
    )
    async def create(
        self,
        interaction: discord.Interaction[commands.Bot],
        repository: str,
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
            repository=repository,
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

        try:
            _get_app_jwt()
        except GitHubAppAuthError as exc:
            await interaction.response.send_message(
                str(exc),
                ephemeral=True,
            )
            return

        if not Config.HOM_GITHUB_REPOSITORIES:
            await interaction.response.send_message(
                "GitHub issue creation is not configured yet. Set `HOM_GITHUB_REPOSITORIES` first.",
                ephemeral=True,
            )
            return

        if not HAS_MODAL_LABEL or not HAS_MODAL_FILE_UPLOAD:
            await interaction.response.send_message(
                "This bot runtime needs `discord.py 2.7.0+` to show the repository dropdown and "
                "attachment upload in the modal. Refresh dependencies and restart the bot first.",
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
