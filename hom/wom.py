import asyncio
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union
from typing import cast
from urllib.parse import quote

import aiohttp

from hom.config import Config
from hom.config import Constants


class WomClient:
    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session
        self._base = Config.HOM_BASE_API_URL

    async def link_developer_api_keys(
        self, developer: str, discord_user_id: int, created_at: Optional[str] = None
    ) -> Optional[int]:
        """Return the matching key count, zero for no match, or None on failure."""
        payload = {
            "adminPassword": Config.SHARED_ADMIN_PASSWORD,
            "developerDiscordId": str(discord_user_id),
        }
        if created_at is not None:
            payload["createdAt"] = created_at
        try:
            async with self._session.put(
                f"{self._base}/api-keys/developer/{quote(developer, safe='')}",
                json=payload,
                headers=Constants.HEADERS,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 404:
                    data = await response.json()
                    return (
                        0
                        if isinstance(data, dict)
                        and cast(Dict[str, Any], data).get("code") == "API_KEY_NOT_FOUND"
                        else None
                    )
                if response.status != 200:
                    return None
                data = await response.json()
                count = (
                    cast(Dict[str, Any], data).get("updatedCount")
                    if isinstance(data, dict)
                    else None
                )
                return count if type(count) is int and count >= 0 else None
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            return None

    async def get_group(self, group_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        async with self._session.get(
            f"{self._base}/groups/{group_id}", headers=Constants.HEADERS
        ) as r:
            return await r.json() if r.status == 200 else None

    async def get_player_competitions(self, username: str) -> Optional[List[Dict[str, Any]]]:
        try:
            async with self._session.get(
                f"{self._base}/players/{username}/competitions",
                headers=Constants.HEADERS,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as r:
                return await r.json() if r.status == 200 else None
        except (aiohttp.ClientError, TimeoutError):
            return None

    async def remove_competition_participant(
        self, competition_id: Union[str, int], rsn: str
    ) -> Tuple[int, str]:
        async with self._session.delete(
            f"{self._base}/competitions/{competition_id}/participants",
            json={"participants": [rsn], "adminPassword": Config.SHARED_ADMIN_PASSWORD},
            headers=Constants.HEADERS,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as r:
            return r.status, await r.text()

    async def verify_group(self, group_id: str) -> bool:
        async with self._session.put(
            f"{self._base}/groups/{group_id}/verify",
            json={"adminPassword": Config.SHARED_ADMIN_PASSWORD},
            headers=Constants.HEADERS,
        ) as r:
            return r.status == 200

    async def reset_group_code(self, group_id: Union[str, int]) -> Optional[Dict[str, Any]]:
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

    async def remove_player_group(
        self, rsn: str, group_id: Union[str, int]
    ) -> Optional[Dict[str, Any]]:
        try:
            async with self._session.delete(
                f"{self._base}/groups/{group_id}/members",
                json={"members": [rsn], "adminPassword": Config.SHARED_ADMIN_PASSWORD},
                headers=Constants.HEADERS,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as r:
                return await r.json() if r.status == 200 else None
        except (aiohttp.ClientError, TimeoutError):
            return None
