import datetime
import functools
import io
import traceback
import typing as t

import discord
import requests
from discord import app_commands
from discord.ext import commands

from hom.cogs import views
from hom.config import Config
from hom.config import Constants

__all__ = (
    "archive_channel_messages",
    "build_support_embed",
    "create_ticket_for_user",
    "get_category",
    "get_channel",
    "get_country_name",
    "get_flag_emoji",
    "get_original_message",
    "get_role",
    "get_user_by_original_message",
    "get_user_ticket_channel",
    "send_log_message",
    "set_flag_autocomplete",
    "set_flag",
)


async def archive_channel_messages(channel: discord.TextChannel) -> str:
    data = ""

    try:
        async for message in channel.history(limit=None, oldest_first=True):
            datetime_info = datetime.datetime.strftime(message.created_at, "%b %d, %Y at %I:%M%p")
            datetime_info_timestamp = f"<t:{str(message.created_at.timestamp()).split('.')[0]}:F>"
            data += (
                f"{datetime_info} {datetime_info_timestamp}\n"
                f"{message.author.display_name.split('/')[0].strip()} - "
                f"{message.author.id}\n{message.clean_content}\n\n"
            )

    except:
        traceback.print_exc()
        pass

    return data


def build_support_embed(guild: discord.Guild) -> discord.Embed:
    questions_message = ""

    if questions_channel := get_channel(guild, Config.QUESTIONS_CHANNEL):
        questions_message = (
            "\n\nIf you'd like to ask a quick question, you may do so in the "
            f"{questions_channel.mention} channel."
        )

    button_synopsis = (
        f"\n\n**Groups** {Constants.ARROW} Help with group related things\n- Verify my group "
        "(for groups with 50+ members)\n- Reset my verification code\n- Remove me from a group\n"
        f"- Other\n\n**Competitions** {Constants.ARROW} Help with competition related things\n"
        "- Reset my verification code\n- Remove me from a competition\n- Other\n\n"
        f"**Players** {Constants.ARROW} Help with player related things\n- Approve a "
        "pending name change\n- Delete name change history\n- Opt out of tracking, new groups, "
        "and new competitions\n- Opt out of new groups\n- Opt out of new competitions\n- "
        f"Delete profile\n- Other\n\n**Patreon** {Constants.ARROW} Request help with Patreon "
        f"benefits\n\n**API Key** {Constants.ARROW} Request an API key for development\n\n"
        f"**Other** {Constants.ARROW} Request assistance for all other inquiries"
    )

    footer = (
        "As a reminder, all moderators and admins in this server volunteer to help in their "
        "free time.\nWe appreciate your patience."
    )

    suffix = f"{button_synopsis}{questions_message}"
    embed = discord.Embed(
        title="Need help from one of our moderators?",
        color=Constants.BLUE,
        description=f"Select a support category below to request assistance.{suffix}",
    )

    embed.set_footer(text=footer)
    return embed


async def create_ticket_for_user(
    interaction: discord.Interaction[commands.Bot],
    instructions: str,
    button_label: t.Optional[str],
    example_url: t.Optional[str] = None,
) -> discord.TextChannel:
    assert interaction.guild

    existing_ticket_channel = get_user_ticket_channel(interaction.guild, interaction.user)
    if existing_ticket_channel:
        msg_content = f":envelope:  Click [here]({existing_ticket_channel.jump_url}) to view your open ticket."
        await interaction.followup.send(content=msg_content, ephemeral=True)
        return existing_ticket_channel

    channel_name = f"help-{interaction.user.display_name[:15]}"
    tickets_category = get_category(interaction.guild, Config.TICKET_CATEGORY)
    if not (mod_role := get_role(interaction.guild, Config.MOD_ROLE)):
        await interaction.followup.send("The moderator role is missing from the server.")
        raise RuntimeError(f"Couldn't find mod role with ID: {Config.MOD_ROLE}")

    new_text_channel = await interaction.guild.create_text_channel(
        name=channel_name,
        category=tickets_category,
        reason=f"{interaction.user.display_name} ({interaction.user.id}) has opened a ticket.",
        topic=button_label or "Unknown (This is a bug)",
        overwrites={
            mod_role: discord.PermissionOverwrite(read_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True),
            t.cast(discord.Member, interaction.user): discord.PermissionOverwrite(
                read_messages=True
            ),
            interaction.guild.default_role: discord.PermissionOverwrite(
                read_messages=False,
                read_message_history=True,
                attach_files=True,
                add_reactions=True,
                embed_links=True,
            ),
        },
    )

    content = (
        ":envelope:  We have created a support ticket for you, click [here]"
        f"({new_text_channel.jump_url}) to view."
    )

    embed = discord.Embed(description=instructions, title=button_label)
    embed.set_footer(
        text=(
            "This channel is only visible to you and our moderators. If your questions have been "
            "answered, feel free to close the ticket."
        )
    )

    if example_url:
        embed.set_image(url=example_url)

    await interaction.followup.send(content, ephemeral=True)
    await new_text_channel.send(
        f"{interaction.user.mention}", embed=embed, view=views.SupportMessage()
    )

    log_content = (
        f"({new_text_channel.topic}) Ticket opened for user:\n``{interaction.user.display_name}`` "
        f"- {interaction.user.mention}"
    )

    assert interaction.client.user
    await send_log_message(interaction, log_content, mod=interaction.client.user)
    return new_text_channel


def get_category(guild: discord.Guild, category_id: int) -> t.Optional[discord.CategoryChannel]:
    # The builtin `next` short circuits as soon as it finds a match reducing iterations
    return next((c for c in guild.categories if c.id == category_id), None)


def get_channel(
    guild: t.Optional[discord.Guild], channel_id: int
) -> t.Optional[discord.TextChannel]:
    return (
        t.cast(
            discord.TextChannel,
            next((c for c in guild.channels if c.id == channel_id), None),
        )
        if guild
        else None
    )


def get_country_name(country: str) -> t.Optional[str]:
    for key, val in Constants.COUNTRIES.items():
        if val == country:
            return key

    return None


def get_flag_emoji(country: str) -> str:
    if country == "null":
        flag_emoji = ":flag_white:"
    elif country == "GB_ENG":
        flag_emoji = ":england:"
    elif country == "GB_NIR":
        flag_emoji = ":flag_gb:"
    elif country == "GB_SCT":
        flag_emoji = ":scotland:"
    elif country == "GB_WLS":
        flag_emoji = ":wales:"
    else:
        flag_emoji = f":flag_{country.lower()}:"

    return flag_emoji


async def get_original_message(
    channel: discord.TextChannel,
) -> t.Optional[discord.Message]:
    messages = [message async for message in channel.history(limit=1, oldest_first=True)]
    return messages[0] if messages else None


def get_role(guild: discord.Guild, role_id: int) -> t.Optional[discord.Role]:
    return next((r for r in guild.roles if r.id == role_id), None)


async def get_user_by_original_message(
    channel: discord.TextChannel,
) -> t.Optional[t.Union[discord.Member, discord.User]]:
    messages = [message async for message in channel.history(limit=1, oldest_first=True)]
    mentions = messages[0].mentions if messages else None
    return mentions[0] if mentions else None


def get_user_ticket_channel(
    guild: discord.Guild, user: t.Union[discord.User, discord.Member]
) -> t.Optional[discord.TextChannel]:
    if category := get_category(guild, Config.TICKET_CATEGORY):
        for channel in category.channels:
            user_perms = channel.overwrites_for(user)

            if user_perms.view_channel:
                return t.cast(discord.TextChannel, channel)

    return None


async def update_ticket_for_user(
    interaction: discord.Interaction[commands.Bot],
    instructions: str,
    button_label: t.Optional[str],
    example_url: t.Optional[str] = None,
) -> t.Optional[discord.Message]:
    assert interaction.guild
    assert isinstance(interaction.channel, discord.TextChannel)

    if not (message := await get_original_message(interaction.channel)):
        await interaction.followup.send(
            f"{Constants.DENIED} Could not get original message.", ephemeral=True
        )
        return None

    og_user = message.mentions[0]
    await interaction.channel.edit(topic=button_label or "Unknown (This is a bug)")
    embed = discord.Embed(description=instructions, title=button_label)
    embed.set_footer(
        text=(
            "This channel is only visible to you and our moderators. If your questions have been "
            "answered, feel free to close the ticket."
        )
    )

    if example_url:
        embed.set_image(url=example_url)

    await message.edit(embed=embed)
    await interaction.edit_original_response(content="Updated ticket for user.", view=None)
    await interaction.channel.send(
        (f"Hey {og_user.mention}, please check the updated instructions."), embed=embed
    )

    log_content = (
        f"({interaction.channel.topic}) Ticket updated for user:\n``{interaction.user.display_name}`` "
        f"- {interaction.user.mention}"
    )

    assert interaction.client.user
    await send_log_message(interaction, log_content, mod=interaction.client.user)
    return message


async def send_log_message(
    interaction: discord.Interaction[commands.Bot],
    content: str,
    mod: t.Union[discord.User, discord.ClientUser, discord.Member, None] = None,
    channel: t.Optional[discord.TextChannel] = None,
    title: t.Optional[str] = None,
) -> t.Optional[discord.Message]:
    assert interaction.guild

    log_channel = get_channel(interaction.guild, Config.MOD_LOG_CHANNEL)
    embed = discord.Embed(title=title, description=content)
    if mod:
        embed.set_footer(text=f"Mod: {mod.display_name}")

    file: t.Optional[discord.File] = None

    if channel:
        archived_data = await archive_channel_messages(channel)
        timestamp = datetime.datetime.now().strftime("_%Y_%m_%d_%Hh_%Mm_%Ss")
        file_name = f"{channel}" + timestamp + ".txt"
        buf = io.BytesIO(bytes(archived_data, "utf-8"))
        file = discord.File(buf, filename=file_name)

    if log_channel:
        send = functools.partial(log_channel.send, embed=embed)
        return await (send(file=file) if file else send())

    return None


async def set_flag_autocomplete(
    interaction: discord.Interaction[commands.Bot], current: str
) -> t.List[app_commands.Choice[str]]:
    countries = [
        app_commands.Choice(name=country, value=Constants.COUNTRIES[country])
        for country in Constants.COUNTRIES.keys()
        if current.lower() in country.lower()
    ]
    return countries[:25]


def set_flag(username: str, country: str) -> requests.models.Response:
    url = f"{Config.DISCORD_BOT_BASE_API_URL}/players/{username}/country"
    headers = {"userAgent": "Helpful Old Man Discord Bot"}
    json = {
        "country": country if country != "null" else None,
        "adminPassword": Config.SHARED_ADMIN_PASSWORD,
    }
    response = requests.put(url, headers=headers, json=json)
    return response
