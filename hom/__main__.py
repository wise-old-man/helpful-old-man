import os

from hom.bot import Bot
from hom.config import Config

if __name__ == "__main__":
    if os.name != "nt":
        import uvloop

        # Faster asyncio event loop on unix-like systems
        uvloop.install()

    bot = Bot()
    bot.run(Config.DISCORD_TOKEN)
