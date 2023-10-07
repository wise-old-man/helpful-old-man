import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from hom.bot import Bot
from hom.config import Config

load_dotenv()

if __name__ == "__main__":
    if os.name != "nt":
        import uvloop

        # Faster asyncio event loop on unix-like systems
        uvloop.install()

    bot = Bot()

    @bot.command()
    @commands.is_owner()
    async def first_sync(ctx: commands.Context[commands.Bot]):
        if ctx.guild:
            await bot.tree.sync(guild=discord.Object(ctx.guild.id))
            await ctx.channel.send("Original Sync Completed.")
        else:
            await ctx.channel.send("This command can only be run in a guild.")

    bot.run(Config.DISCORD_TOKEN)
