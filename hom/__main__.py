import importlib
import os

from hom.bot import Bot
from hom.config import Config

if __name__ == "__main__":
    if os.name != "nt":
        # Faster drop in replacement for the asyncio event loop
        # Only works on unix-like systems
        uvloop = importlib.import_module("uvloop")
        uvloop.install()

    bot = Bot()
    bot.run(Config.HOM_DISCORD_TOKEN)
