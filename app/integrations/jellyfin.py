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
        user_id: Optional[str] = None,
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
            user_id: User ID for API requests (auto-detected if not provided)
            client_name: Client application name
            device_name: Device name
            device_id: Unique device identifier (generated if not provided)
            version: Application version
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.user_id = user_id
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

    async def get_users(self) -> List[Dict[str, Any]]:
        """
        Get all users from Jellyfin.
        Useful for discovering user IDs.
        """
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/Users"
            async with session.get(url, headers=self.headers) as response:
                response.raise_for_status()
                return await response.json()

    async def get_current_user(self) -> Optional[Dict[str, Any]]:
        """
        Get the first user (usually the admin/API key owner).
        Returns user info with Id field.
        """
        users = await self.get_users()
        return users[0] if users else None

    async def ensure_user_id(self) -> str:
        """
        Ensure we have a user ID.
        If not set, auto-detect from the first user.
        """
        if not self.user_id:
            user = await self.get_current_user()
            if user:
                self.user_id = user['Id']
            else:
                raise Exception("Could not auto-detect user ID and none was provided")
        return self.user_id

    async def get_libraries(self) -> List[Dict[str, Any]]:
        """
        Get all libraries (views) for the user.
        Uses /Users/{userId}/Views endpoint.
        """
        user_id = await self.ensure_user_id()

        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/Users/{user_id}/Views"
            async with session.get(url, headers=self.headers) as response:
                response.raise_for_status()
                data = await response.json()
                # Return the Items array which contains the libraries
                return data.get("Items", [])

    async def get_library_items(
        self,
        library_id: str,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get items from a specific library.
        Returns the full response including Items array.
        """
        user_id = await self.ensure_user_id()

        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/Users/{user_id}/Items"
            params = {
                "ParentId": library_id,
                "Limit": limit,
                "Recursive": True
            }
            async with session.get(url, headers=self.headers, params=params) as response:
                response.raise_for_status()
                return await response.json()

    async def get_item_info(self, item_id: str) -> Dict[str, Any]:
        """Get information about a specific item."""
        user_id = await self.ensure_user_id()

        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/Users/{user_id}/Items/{item_id}"
            async with session.get(url, headers=self.headers) as response:
                response.raise_for_status()
                return await response.json()

    async def get_stream_url(self, item_id: str) -> str:
        """Get streaming URL for an item."""
        return f"{self.base_url}/Videos/{item_id}/stream?api_key={self.api_key}"
