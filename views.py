import discord
import data.constant_data as cd
import utilities.discord_utils as du


class PViewSupport(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Groups',
                       style=discord.ButtonStyle.green,
                       custom_id='persistent_view:groups_instructions')
    async def groups_instructions(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(view=PViewSupport_Group(),
                                                content="What do you like assistance with?",
                                                ephemeral=True)

    @discord.ui.button(label='Name Changes',
                       style=discord.ButtonStyle.green,
                       custom_id='persistent_view:names_instructions')
    async def names_instructions(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(view=PViewSupport_Names(),
                                                content="What do you like assistance with?",
                                                ephemeral=True)

    @discord.ui.button(label='API Key',
                       style=discord.ButtonStyle.green,
                       custom_id='persistent_view:api_key')
    async def api_key(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        instructions = f"If you'd like to get an API Key, please tell us your project's name and we'll create you a new API key.\n\n{cd.view_footer}"
        await du.create_ticket_for_user(interaction, instructions, button.label)

    @discord.ui.button(label='Other',
                       style=discord.ButtonStyle.green,
                       custom_id='persistent_view:other_instructions')
    async def other_instructions(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        instructions = f"Explain what you require assistance with below.\n\n{cd.view_footer}"
        await du.create_ticket_for_user(interaction, instructions, f"Other")


class PViewVerify(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Yes',
                       style=discord.ButtonStyle.red,
                       custom_id='persistent_view:verify_yes')
    async def verify_yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(content=f'{cd.status_emoji_complete} Closing this ticket.',
                                                ephemeral=True)
        await interaction.channel.delete()


class PViewSupport_Group(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Verify my group',
                       style=discord.ButtonStyle.blurple,
                       custom_id='persistent_view:group_verify')
    async def group_verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        instructions = f"To verify your group please provide a screenshot to prove ownership. We have attached an example of what we need to see below. The screenshot must contain:\n\n- Your Wise Old Man group ID (found in that group’s page URL), your Discord ID, and today’s date typed into your in-game chatbox.\n- Your Clan tab open showing your username and rank. For clans, you must be Owner or Deputy Owner to verify the group. For the old clan chat, you must be Owner or General (gold star).\n\n{cd.view_footer}"
        await du.create_ticket_for_user(interaction, instructions, f"Group {cd.ARROW} " + button.label, 'https://cdn.discordapp.com/attachments/1125434806411464867/1127741141152960542/image.png')

    @discord.ui.button(label='Reset my verification code',
                       style=discord.ButtonStyle.blurple,
                       custom_id='persistent_view:group_reset_code')
    async def group_reset_code(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        instructions = f"To reset your verification code please provide a screenshot to prove ownership. We have attached an example of what we need to see below. The screenshot must contain:\n\n- Your Wise Old Man group ID (found in that group’s page URL),  your Discord ID, and today’s date typed into your in-game chatbox.\n- Your Clan tab open showing your username and rank. For clans, you must be Owner or Deputy Owner to verify the group. For the old clan chat, you must be Owner or General (gold star).\n\nKeep in mind that verification codes should be secret, they can be used to edit or delete a group, so please be mindful of who you choose to share it with.\n\n{cd.view_footer}"
        await du.create_ticket_for_user(interaction, instructions, f"Group {cd.ARROW} " + button.label, 'https://cdn.discordapp.com/attachments/1125434806411464867/1127741141152960542/image.png')

    @discord.ui.button(label='Remove me from a group',
                       style=discord.ButtonStyle.blurple,
                       custom_id='persistent_view:group_remove')
    async def group_remove(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        instructions = f"To remove yourself from a group, please provide us with a screenshot containing:\n\n- Your in-game username\n- Your Discord username/ID\n- Today's date\n\n{cd.view_footer}"
        await du.create_ticket_for_user(interaction, instructions, f"Group {cd.ARROW} " + button.label, 'https://cdn.discordapp.com/attachments/1125434806411464867/1129178517557481585/image.png')

    @discord.ui.button(label='Other',
                       style=discord.ButtonStyle.blurple,
                       custom_id='persistent_view:group_other')
    async def group_other(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        instructions = f"Explain what you require assistance with below.\n\n{cd.view_footer}"
        await du.create_ticket_for_user(interaction, instructions, f"Group {cd.ARROW} " + button.label)


class PViewSupport_Names(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Approve a pending name change',
                       style=discord.ButtonStyle.blurple,
                       custom_id='persistent_view:names_approve')
    async def names_approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        instructions = f"Some name changes get skipped, as they can’t be auto-approved by our system and require manual approval.\n\nIf yours hasn’t been auto-approved, please tell us the name change ID and we’ll manually review it for you.\n\nNote: If you’d like to know why your name change has been skipped you can visit our beta website  (work in progress) at https://beta.wiseoldman.net/names and hover your cursor over the your name change's ℹ️ icon. \n\n{cd.view_footer}"
        await du.create_ticket_for_user(interaction, instructions, f"Names {cd.ARROW} " + button.label)

    @discord.ui.button(label='Delete name change history',
                       style=discord.ButtonStyle.blurple,
                       custom_id='persistent_view:names_delete')
    async def names_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        instructions = f"To request a name change history deletion, please provide us with:\n\n- Your in-game username\n- Your Discord username/ID\n- Today's date\n\n{cd.view_footer}"
        await du.create_ticket_for_user(interaction, instructions, f"Names {cd.ARROW} " + button.label, 'https://cdn.discordapp.com/attachments/1125434806411464867/1129178517557481585/image.png')

    @discord.ui.button(label='Other',
                       style=discord.ButtonStyle.blurple,
                       custom_id='persistent_view:names_other')
    async def names_other(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        instructions = f"Explain what you require assistance with below.\n\n{cd.view_footer}"
        await du.create_ticket_for_user(interaction, instructions, f"Names {cd.ARROW} " + button.label)


class PViewSupport_Message(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="\N{LOCK}",
                       label='Close',
                       style=discord.ButtonStyle.blurple,
                       custom_id='persistent_view:message_close')
    async def message_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await interaction.channel.set_permissions(interaction.user, overwrite=None)
        embed = discord.Embed(description=f"{interaction.user.mention} has closed the ticket.")
        await interaction.followup.send(ephemeral=False, embed=embed, view=PViewSupport_Message_Close_Channel())


class PViewSupport_Message_Close_Channel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji=cd.status_emoji_denied,
                       label='Close Channel',
                       style=discord.ButtonStyle.blurple,
                       custom_id='persistent_view:message_close_channel')
    async def message_close_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if du.contains_roles(interaction.user.roles, 'Moderator'):
            channel_user = await du.get_user_by_original_message(interaction.channel)
            await interaction.channel.delete()
            await du.send_log_message(interaction=interaction,
                                      content=f"({interaction.channel.topic}) Ticket channel closed for user:\n{channel_user.display_name if channel_user else '?'} - {channel_user.mention if channel_user else '?'}",
                                      mod=interaction.user)
        else:
            await interaction.followup.send(ephemeral=True,
                                            content="You do not have the required permissions to delete the channel.")
