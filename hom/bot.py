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

    async def sync(self, guild_id: int) -> None:
        await self.tree.sync()
