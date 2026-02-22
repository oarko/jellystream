"""Jellyfin API client."""

import aiohttp
import uuid
from typing import List, Dict, Any, Optional

from app.core.logging_config import get_logger

logger = get_logger(__name__)


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

        logger.debug(
            f"JellyfinClient init: base_url={self.base_url}, "
            f"user_id={self.user_id}, client={self.client_name}"
        )

    async def get_users(self) -> List[Dict[str, Any]]:
        """
        Get all users from Jellyfin.
        Useful for discovering user IDs.
        """
        logger.debug("get_users called")
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/Users"
            async with session.get(url, headers=self.headers) as response:
                response.raise_for_status()
                users = await response.json()
                logger.info(f"get_users: returned {len(users)} users")
                return users

    async def get_current_user(self) -> Optional[Dict[str, Any]]:
        """
        Get the first user (usually the admin/API key owner).
        Returns user info with Id field.
        """
        logger.debug("get_current_user called")
        users = await self.get_users()
        user = users[0] if users else None
        if user:
            logger.debug(f"get_current_user: using user '{user.get('Name')}' (id={user.get('Id')})")
        else:
            logger.warning("get_current_user: no users found on Jellyfin server")
        return user

    async def ensure_user_id(self) -> str:
        """
        Ensure we have a user ID.
        If not set, auto-detect from the first user.
        """
        if not self.user_id:
            logger.debug("ensure_user_id: user_id not set, auto-detecting")
            user = await self.get_current_user()
            if user:
                self.user_id = user['Id']
                logger.info(f"ensure_user_id: auto-detected user_id={self.user_id}")
            else:
                raise Exception("Could not auto-detect user ID and none was provided")
        return self.user_id

    async def get_libraries(self) -> List[Dict[str, Any]]:
        """
        Get all libraries (views) for the user.
        Uses /Users/{userId}/Views endpoint.
        """
        logger.debug("get_libraries called")
        user_id = await self.ensure_user_id()

        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/Users/{user_id}/Views"
            async with session.get(url, headers=self.headers) as response:
                response.raise_for_status()
                data = await response.json()
                libraries = data.get("Items", [])
                logger.info(f"get_libraries: returned {len(libraries)} libraries")
                return libraries

    async def get_library_items(
        self,
        parent_id: str,
        recursive: bool = False,
        limit: int = 50,
        start_index: int = 0,
        sort_by: str = "SortName",
        sort_order: str = "Ascending",
        include_item_types: Optional[str] = None,
        genres: Optional[List[str]] = None,
        fields: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get items from a specific parent (library, series, season).

        Args:
            parent_id: Parent ID (library, series, or season)
            recursive: If True, gets all descendants. If False, only direct children.
            limit: Number of items to return (for pagination)
            start_index: Starting index for pagination
            sort_by: Field to sort by (SortName, PremiereDate, etc.)
            sort_order: Ascending or Descending
            include_item_types: Filter by type (e.g., "Series,Season,Episode")
            genres: Optional list of genre names to filter by
            fields: Comma-separated additional fields to include in response

        Returns:
            Full response with Items, TotalRecordCount, StartIndex
        """
        logger.debug(
            f"get_library_items: parent_id={parent_id}, recursive={recursive}, "
            f"limit={limit}, start_index={start_index}, genres={genres}"
        )
        user_id = await self.ensure_user_id()

        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/Users/{user_id}/Items"
            params: Dict[str, Any] = {
                "ParentId": parent_id,
                "Recursive": str(recursive).lower(),
                "Limit": limit,
                "StartIndex": start_index,
                "SortBy": sort_by,
                "SortOrder": sort_order,
            }

            if include_item_types:
                params["IncludeItemTypes"] = include_item_types

            if genres:
                params["Genres"] = ",".join(genres)

            if fields:
                params["Fields"] = fields

            async with session.get(url, headers=self.headers, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                total = data.get("TotalRecordCount", 0)
                items = data.get("Items", [])
                logger.debug(
                    f"get_library_items: parent={parent_id}, "
                    f"returned {len(items)}/{total} items"
                )
                return data

    async def get_item_info(self, item_id: str) -> Dict[str, Any]:
        """Get information about a specific item."""
        logger.debug(f"get_item_info: item_id={item_id}")
        user_id = await self.ensure_user_id()

        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/Users/{user_id}/Items/{item_id}"
            async with session.get(url, headers=self.headers) as response:
                response.raise_for_status()
                item = await response.json()
                logger.debug(f"get_item_info: returned item '{item.get('Name')}' (id={item_id})")
                return item

    async def get_stream_url(self, item_id: str) -> str:
        """Get streaming URL for an item."""
        url = f"{self.base_url}/Videos/{item_id}/stream?api_key={self.api_key}"
        logger.debug(f"get_stream_url: item_id={item_id}")
        return url

    # Live TV Integration Methods

    async def register_tuner_host(
        self,
        url: str,
        friendly_name: str,
        tuner_type: str = "m3u",
        source: str = "JellyStream",
        enable_stream_looping: bool = True
    ) -> Dict[str, Any]:
        """
        Register a tuner host with Jellyfin Live TV.

        Args:
            url: M3U playlist URL
            friendly_name: Display name for the tuner
            tuner_type: Type of tuner (default: "m3u")
            source: Source identifier
            enable_stream_looping: Enable looping for virtual channels

        Returns:
            Tuner host response with Id
        """
        logger.debug(f"register_tuner_host: url={url}, friendly_name={friendly_name}")
        async with aiohttp.ClientSession() as session:
            api_url = f"{self.base_url}/LiveTv/TunerHosts"
            payload = {
                "Url": url,
                "Type": tuner_type,
                "FriendlyName": friendly_name,
                "Source": source,
                "EnableStreamLooping": enable_stream_looping,
                "AllowHWTranscoding": False,
                "AllowStreamSharing": True,
                "ImportFavoritesOnly": False
            }

            async with session.post(api_url, headers=self.headers, json=payload) as response:
                response.raise_for_status()
                result = await response.json()
                logger.info(f"register_tuner_host: registered tuner id={result.get('Id')}")
                return result

    async def unregister_tuner_host(self, tuner_host_id: str) -> bool:
        """
        Unregister a tuner host from Jellyfin Live TV.

        Args:
            tuner_host_id: The tuner host ID to remove

        Returns:
            True if successful
        """
        logger.debug(f"unregister_tuner_host: tuner_host_id={tuner_host_id}")
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/LiveTv/TunerHosts"
            params = {"id": tuner_host_id}

            async with session.delete(url, headers=self.headers, params=params) as response:
                response.raise_for_status()
                success = response.status == 204
                logger.info(f"unregister_tuner_host: {tuner_host_id} removed={success}")
                return success

    async def register_listing_provider(
        self,
        listing_provider_type: str,
        xmltv_url: str,
        friendly_name: str
    ) -> Dict[str, Any]:
        """
        Register an XMLTV listing provider with Jellyfin.

        Args:
            listing_provider_type: Type (usually "xmltv")
            xmltv_url: URL to XMLTV EPG data
            friendly_name: Display name

        Returns:
            Listing provider response with Id
        """
        logger.debug(
            f"register_listing_provider: type={listing_provider_type}, "
            f"xmltv_url={xmltv_url}"
        )
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/LiveTv/ListingProviders"
            payload = {
                "Type": listing_provider_type,
                "Path": xmltv_url,
                "ListingsId": friendly_name
            }

            async with session.post(url, headers=self.headers, json=payload) as response:
                response.raise_for_status()
                result = await response.json()
                logger.info(
                    f"register_listing_provider: registered provider id={result.get('Id')}"
                )
                return result

    async def unregister_listing_provider(self, provider_id: str) -> bool:
        """
        Unregister a listing provider from Jellyfin.

        Args:
            provider_id: The listing provider ID to remove

        Returns:
            True if successful
        """
        logger.debug(f"unregister_listing_provider: provider_id={provider_id}")
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/LiveTv/ListingProviders"
            params = {"id": provider_id}

            async with session.delete(url, headers=self.headers, params=params) as response:
                response.raise_for_status()
                success = response.status == 204
                logger.info(f"unregister_listing_provider: {provider_id} removed={success}")
                return success
