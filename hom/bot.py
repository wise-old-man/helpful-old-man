from pathlib import Path

import discord
from discord.ext import commands

from hom.config import Constants

__all__ = ("Bot",)


class Bot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(Constants.PREFIX, intents=discord.Intents.all())

    async def setup_hook(self) -> None:
        for path in Path("./hom/cogs").glob("[!_]*.py"):
            await self.load_extension(f"hom.cogs.{path.stem}")

    async def on_ready(self) -> None:
        user = self.user.display_name if self.user else "Bot"
        print(f"{user} has connected to Discord!")

    async def sync(self) -> None:
        await self.tree.sync()

    async def on_command_error(  # type: ignore
        self, ctx: commands.Context[commands.Bot], exc: commands.CommandError
    ) -> None:
        if any(isinstance(exc, e) for e in (commands.CommandNotFound, commands.BadArgument)):
            return

        if isinstance(exc, (commands.MissingRole, commands.CheckFailure)):
            await ctx.reply("You are not allowed to do that.")
        elif isinstance(exc, commands.BotMissingPermissions):
            await ctx.reply("I don't have the permissions necessary for that.")
        else:
            raise exc
