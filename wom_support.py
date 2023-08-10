import discord
import os
import views as vw
from discord.ext import commands
from dotenv import load_dotenv
from data import constant_data as cd


class MyBot(commands.Bot):

    def __init__(self):
        super().__init__(command_prefix=cd.BOT_PREFIX,
                         intents=discord.Intents.all(),
                         application_id=os.getenv('APP_ID'))
        self.initial_extensions = cd.COGS

    async def setup_hook(self):
        for cog in self.initial_extensions:
            await self.load_extension(cog)

        self.add_view(vw.PViewSupport())
        self.add_view(vw.PViewVerify())
        self.add_view(vw.PViewSupport_Group())
        self.add_view(vw.PViewSupport_Names())
        self.add_view(vw.PViewSupport_Message())
        self.add_view(vw.PViewSupport_Message_Close_Channel())

    async def on_ready(self):
        print(f'{self.user.display_name} has connected to Discord!')

load_dotenv()
client = discord.Client(intents=discord.Intents.all())
bot = MyBot()
bot.run(os.getenv('DISCORD_TOKEN'))


@bot.command()
@commands.is_owner()
async def first_sync(ctx: commands.Context):
    await bot.tree.sync(guild=discord.Object(id=ctx.guild.id))
    await ctx.channel.send(content="Original Sync Completed.")



