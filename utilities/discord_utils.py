import discord
import views as vw


def get_role_by_name(guild, role_name_to_find):
    roles = guild.roles
    role_name_to_find = str(role_name_to_find).lower().replace(" ", "_").replace("-", "_")
    for role in roles:
        role_name = str(role).lower().replace(" ", "_").replace("-", "_")
        if role_name == role_name_to_find:
            return role

    return None


def contains_roles(roles, accepted_roles):
    accepted_roles = accepted_roles if isinstance(accepted_roles, list) else [accepted_roles]
    if len(accepted_roles) == 0:
        return True

    for role in accepted_roles:
        if str(role).lower() in [y.name.lower() for y in roles]:
            return True

    return False


def get_category(discord_guild: discord.Guild, channel_name: str) -> discord.CategoryChannel:
    return discord.utils.find(lambda c: str(c.name).lower().replace("-", " ") == str(channel_name).lower().replace("-", " ") and str(c.type).lower() == "category", discord_guild.channels)


def get_channel_by_id(bot, discord_guild_id: int, channel_id: int, channel_type: str = 'text'):
    if discord_guild_id not in [guild.id for guild in bot.guilds]:
        return None

    return discord.utils.find(lambda c: int(c.id) == int(channel_id) and str(c.type).lower() == channel_type, bot.get_guild(int(discord_guild_id)).channels)


def get_channel_by_name(bot, discord_guild_id: int, channel_name: str, channel_type: str = 'text'):
    if discord_guild_id not in [guild.id for guild in bot.guilds]:
        return None

    return discord.utils.find(lambda c: str(c.name).lower().replace("-", " ") == str(channel_name).lower().replace("-", " ") and str(c.type).lower() == channel_type, bot.get_guild(int(discord_guild_id)).channels)


async def get_user_by_original_message(channel):
    channel_messages = [message async for message in channel.history(limit=None, oldest_first=True)]
    message_mentions = channel_messages[0].mentions if channel_messages else None
    return message_mentions[0] if message_mentions else None


def get_user_ticket_channel(guild, user):
    category = get_category(discord_guild=guild, channel_name="Tickets") # TODO: Make this channel_id?

    if not category:
        return

    for channel in category.channels:
        user_perms = channel.overwrites_for(user)
        if user_perms.view_channel:
            return channel

    return None


async def create_ticket_for_user(interaction, instructions, button_label, example_url=None):
    prevent_dupe_channels = True
    existing_ticket_channel = get_user_ticket_channel(interaction.guild, interaction.user)

    if existing_ticket_channel and prevent_dupe_channels:
        msg_content = f":envelope:  Click [here]({existing_ticket_channel.jump_url}) to view your open ticket."
        await interaction.followup.send(content=msg_content, ephemeral=True)
        return

    tickets_category = get_category(discord_guild=interaction.guild, channel_name="Tickets") # TODO: Make this channel_id?
    channel_name = f"help-{interaction.user.display_name[:15]}"

    mod_role = get_role_by_name(interaction.guild, "Moderator")
    helpful_old_man_role = get_role_by_name(interaction.guild, "Helpful Old Man")
    new_text_channel = await interaction.channel.guild.create_text_channel(
        name=channel_name,
        category=tickets_category,
        reason=f"{interaction.user.display_name} ({interaction.user.id}) has opened a ticket.",
        topic=button_label,
        overwrites={interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False,
                                                                                read_message_history=True,
                                                                                attach_files=True,
                                                                                add_reactions=True,
                                                                                embed_links=True),
                    mod_role: discord.PermissionOverwrite(read_messages=True),
                    helpful_old_man_role: discord.PermissionOverwrite(read_messages=True),
                    interaction.user: discord.PermissionOverwrite(read_messages=True),
                    }
    )

    msg_content = f":envelope:  We have created a support ticket for you, click [here]({new_text_channel.jump_url}) to view."

    embed = discord.Embed(description=instructions, title=button_label)
    embed.set_image(url=example_url) if example_url else None

    embed.set_footer(text="This channel is only visible to you and our moderators. If your question has been answered, feel free to close the ticket.")
    await interaction.followup.send(content=msg_content, ephemeral=True)
    await new_text_channel.send(content=f"{interaction.user.mention}", embed=embed, view=vw.PViewSupport_Message())

    await send_log_message(interaction=interaction,
                           content=f"({new_text_channel.topic}) Ticket opened for user:\n``{interaction.user.display_name}`` - {interaction.user.mention}",
                           mod=interaction.client.user)

    return new_text_channel


async def send_log_message(interaction, content, mod):
    mod_logs_channel = get_channel_by_name(interaction.client, interaction.guild.id, 'mod-logs')
    embed = discord.Embed(title=None, description=content)
    embed.set_footer(text=f"Mod: {mod.display_name}")
    await mod_logs_channel.send(embed=embed) if mod_logs_channel else None
    print(f"Message sent: {content} Footer: Mod: {mod.display_name}")
