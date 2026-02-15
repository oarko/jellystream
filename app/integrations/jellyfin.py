"""Jellyfin API client."""

import aiohttp
from typing import List, Dict, Any


class JellyfinClient:
    """Client for interacting with Jellyfin API."""

    def __init__(self, base_url: str, api_key: str):
        """Initialize Jellyfin client."""
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {
            "X-Emby-Token": api_key,
            "Content-Type": "application/json"
        }

    async def get_libraries(self) -> List[Dict[str, Any]]:
        """Get all libraries from Jellyfin."""
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/Library/VirtualFolders"
            async with session.get(url, headers=self.headers) as response:
                response.raise_for_status()
                return await response.json()

    async def get_library_items(
        self,
        library_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get items from a specific library."""
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/Items"
            params = {
                "ParentId": library_id,
                "Limit": limit,
                "Recursive": True
            }
            async with session.get(url, headers=self.headers, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get("Items", [])

    async def get_item_info(self, item_id: str) -> Dict[str, Any]:
        """Get information about a specific item."""
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/Items/{item_id}"
            async with session.get(url, headers=self.headers) as response:
                response.raise_for_status()
                return await response.json()

    async def get_stream_url(self, item_id: str) -> str:
        """Get streaming URL for an item."""
        return f"{self.base_url}/Videos/{item_id}/stream?api_key={self.api_key}"
