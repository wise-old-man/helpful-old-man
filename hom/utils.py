import datetime
import io
import traceback
import typing as t

import discord
from discord.ext import commands

from hom.cogs import views


def normalize(obj: t.Any) -> str:
    return str(obj).lower().replace(" ", "_").replace("-", "_")


def get_role_by_name(
    guild: discord.Guild, target_role: discord.Role | str
) -> t.Optional[discord.Role]:
    role_name_to_find = normalize(target_role)

    for role in guild.roles:
        if normalize(role) == role_name_to_find:
            return role

    return None


def contains_roles(roles: t.List[discord.Role], *accepted_roles: discord.Role | str) -> bool:
    lower_roles = [normalize(r) for r in roles]
    return any(normalize(r) in lower_roles for r in accepted_roles) or not accepted_roles


def get_category(guild: discord.Guild, channel_name: str) -> t.Optional[discord.CategoryChannel]:
    channel_name = normalize(channel_name)
    return discord.utils.find(
        lambda c: normalize(c.name) == channel_name,
        guild.categories,  # TODO: Changed this to categories, is that right?
    )


def get_channel_by_id(
    bot: commands.Bot, guild_id: int, channel_id: int, channel_type: str = "text"
) -> t.Optional[discord.TextChannel]:
    if guild_id not in [guild.id for guild in bot.guilds]:
        return None

    if not (guild := bot.get_guild(guild_id)):
        return None

    channel = discord.utils.find(
        lambda c: c.id == channel_id and str(c.type).lower() == channel_type,
        guild.channels,
    )

    return t.cast(discord.TextChannel, channel) if channel else None


def get_channel_by_name(
    bot: commands.Bot | discord.Client,
    guild_id: int,
    channel_name: str,
    channel_type: str = "text",
) -> t.Optional[discord.TextChannel]:
    if not any(guild_id == guild.id for guild in bot.guilds):
        return None

    if not (guild := bot.get_guild(guild_id)):
        return None

    channel = discord.utils.find(
        lambda c: normalize(c.name) == normalize(channel_name)
        and str(c.type).lower() == channel_type,
        guild.channels,
    )

    return t.cast(discord.TextChannel, channel) if channel else None


async def get_user_by_original_message(
    channel: discord.TextChannel,
) -> t.Optional[discord.Member | discord.User]:
    messages = [message async for message in channel.history(limit=1, oldest_first=True)]
    mentions = messages[0].mentions if messages else None
    return mentions[0] if mentions else None


def get_user_ticket_channel(
    guild: discord.Guild, user: discord.User | discord.Member
) -> t.Optional[discord.TextChannel]:
    if category := get_category(guild, "Tickets"):  # TODO: Make this channel_id?
        for channel in category.channels:
            user_perms = channel.overwrites_for(user)

            if user_perms.view_channel:
                return t.cast(discord.TextChannel, channel)

    return None


async def create_ticket_for_user(
    interaction: discord.Interaction[commands.Bot],
    instructions: str,
    button_label: t.Optional[str],
    example_url: t.Optional[str] = None,
) -> discord.TextChannel:
    assert interaction.guild
    assert isinstance(interaction.user, discord.Member)
    existing_ticket_channel = get_user_ticket_channel(interaction.guild, interaction.user)

    if existing_ticket_channel:
        msg_content = f":envelope:  Click [here]({existing_ticket_channel.jump_url}) to view your open ticket."
        await interaction.followup.send(content=msg_content, ephemeral=True)
        return existing_ticket_channel

    channel_name = f"help-{interaction.user.display_name[:15]}"
    tickets_category = get_category(interaction.guild, "Tickets")  # TODO: Make this channel_id?
    mod_role = get_role_by_name(interaction.guild, "Moderator")
    helpful_old_man_role = get_role_by_name(interaction.guild, "Helpful Old Man")
    assert helpful_old_man_role
    assert mod_role

    new_text_channel = await interaction.guild.create_text_channel(
        name=channel_name,
        category=tickets_category,
        reason=f"{interaction.user.display_name} ({interaction.user.id}) has opened a ticket.",
        topic=button_label or "Unknown (This is a bug)",
        overwrites={
            interaction.guild.default_role: discord.PermissionOverwrite(
                read_messages=False,
                read_message_history=True,
                attach_files=True,
                add_reactions=True,
                embed_links=True,
            ),
            mod_role: discord.PermissionOverwrite(read_messages=True),
            helpful_old_man_role: discord.PermissionOverwrite(read_messages=True),
            interaction.user: discord.PermissionOverwrite(read_messages=True),
        },
    )

    content = (
        ":envelope:  We have created a support ticket for you, click [here]"
        f"({new_text_channel.jump_url}) to view."
    )

    embed = discord.Embed(description=instructions, title=button_label)
    embed.set_footer(
        text=(
            "This channel is only visible to you and our moderators. If your question has been "
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
    await send_log_message(interaction, log_content, interaction.client.user)
    return new_text_channel


async def send_log_message(
    interaction: discord.Interaction[commands.Bot],
    content: str,
    mod: discord.User | discord.ClientUser | discord.Member,
    channel: t.Optional[discord.TextChannel] = None,
) -> t.Optional[discord.Message]:
    assert interaction.guild
    mod_logs_channel = get_channel_by_name(interaction.client, interaction.guild.id, "mod-logs")
    embed = discord.Embed(title=None, description=content)
    embed.set_footer(text=f"Mod: {mod.display_name}")

    if channel and mod_logs_channel:
        archived_data = await archive_channel_messages(channel)
        timestamp = datetime.datetime.now().strftime("_%Y_%m_%d_%Hh_%Mm_%Ss")
        file_name = f"{channel}" + timestamp + ".txt"
        buf = io.BytesIO(bytes(archived_data, "utf-8"))
        f = discord.File(buf, filename=file_name)

        assert isinstance(mod_logs_channel, discord.TextChannel)
        return await mod_logs_channel.send(embed=embed, file=f)

    return None


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

    finally:
        return data
