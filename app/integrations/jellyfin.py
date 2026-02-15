"""Jellyfin API client."""

import aiohttp
import uuid
from typing import List, Dict, Any, Optional


class JellyfinClient:
    """Client for interacting with Jellyfin API."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        client_name: str = "JellyStream",
        device_name: str = "JellyStream Server",
        device_id: Optional[str] = None,
        version: str = "0.1.0"
    ):
        """
        Initialize Jellyfin client.

        Args:
            base_url: Jellyfin server URL
            api_key: API key for authentication
            client_name: Client application name
            device_name: Device name
            device_id: Unique device identifier (generated if not provided)
            version: Application version
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client_name = client_name
        self.device_name = device_name
        self.device_id = device_id or str(uuid.uuid4())
        self.version = version

        # Build authentication header in Jellyfin format
        auth_header = (
            f'MediaBrowser Token="{api_key}", '
            f'Client="{client_name}", '
            f'Device="{device_name}", '
            f'DeviceId="{self.device_id}", '
            f'Version="{version}"'
        )

        self.headers = {
            "Authorization": auth_header,
            "Accept": "application/json",
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
