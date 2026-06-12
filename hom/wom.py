from typing import Any
import aiohttp
from hom.config import Config, Constants

class WomClient:
    def __init__(self, session: aiohttp.ClientSession) -> None:
      self._session = session
      self._base = Config.DISCORD_BOT_BASE_API_URL

    async def get_group(self, group_id: str | int) -> dict[str, Any] | None:
      async with self._session.get(
          f"{self._base}/groups/{group_id}", headers=Constants.HEADERS
      ) as r:
          return await r.json() if r.status == 200 else None

    async def verify_group(self, group_id: str) -> bool:
        async with self._session.put(
            f"{self._base}/groups/{group_id}/verify",
            json={"adminPassword": Config.SHARED_ADMIN_PASSWORD},
            headers=Constants.HEADERS,
        ) as r:
            return r.status == 200

    async def reset_group_code(self, group_id: str | int) -> dict[str, Any] | None:
        try:
            async with self._session.put(
                f"{self._base}/groups/{group_id}/reset-code",
                json={"adminPassword": Config.SHARED_ADMIN_PASSWORD},
                headers=Constants.HEADERS,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as r:
                return await r.json() if r.status == 200 else None
        except (aiohttp.ClientError, TimeoutError):
            return None

    async def remove_player_group(self, rsn: str, group_id: str | int) -> dict[str, Any] | None:
        try:
            async with self._session.delete(
                f"{self._base}/groups/{group_id}/members",
                json={"members": [rsn],"adminPassword": Config.SHARED_ADMIN_PASSWORD},
                headers=Constants.HEADERS,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as r:
                return await r.json() if r.status == 200 else None
        except (aiohttp.ClientError, TimeoutError):
            return None
