from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

import aiohttp

from hom.config import Config
from hom.config import Constants


class WomClient:
    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session
        self._base = Config.HOM_BASE_API_URL

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
