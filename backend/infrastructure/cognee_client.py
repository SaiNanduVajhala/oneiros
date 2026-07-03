"""
Oneiros Infrastructure Layer - Cognee Cloud Client

Handles connection lifecycle, authentication, and direct interaction with the Cognee Cloud SDK/APIs.
"""

import logging
from typing import List, Dict, Any, Tuple
import cognee

logger = logging.getLogger("oneiros.infrastructure.cognee_client")

class CogneeClient:
    """
    Client managing connectivity, authentication, and SDK wrapping for Cognee Cloud.
    """
    def __init__(self, api_key: str, base_url: str = None):
        self.api_key = api_key
        self.base_url = base_url
        self._connected = False

    async def connect(self):
        """
        Initializes connection to Cognee Cloud or tenant server.
        """
        if not self._connected:
            try:
                if self.base_url:
                    await cognee.serve(url=self.base_url, api_key=self.api_key)
                else:
                    await cognee.serve(api_key=self.api_key)
                self._connected = True
                logger.info("Successfully connected to Cognee Cloud.")
            except Exception as e:
                logger.error(f"Failed to connect to Cognee: {e}")
                raise

    async def disconnect(self):
        """
        Closes current Cognee session connections.
        """
        if self._connected:
            try:
                await cognee.disconnect()
                self._connected = False
                logger.info("Successfully disconnected from Cognee Cloud.")
            except Exception as e:
                logger.error(f"Error disconnecting from Cognee: {e}")

    async def remember(self, content: str, dataset_name: str) -> None:
        await self.connect()
        await cognee.remember(content, dataset_name=dataset_name)

    async def recall(self, query: str, dataset_name: str) -> List[Any]:
        await self.connect()
        return await cognee.recall(query, datasets=[dataset_name])

    async def improve(self, dataset_name: str) -> None:
        await self.connect()
        await cognee.cognify(datasets=[dataset_name])

    async def forget(self, data_id: Any, dataset_name: str) -> None:
        await self.connect()
        await cognee.forget(data_id=data_id, dataset=dataset_name)

    async def clear_all(self, dataset_name: str) -> None:
        await self.connect()
        await cognee.forget(everything=True, dataset=dataset_name)

    async def get_provenance_graph(self) -> Tuple[List[Any], List[Any]]:
        await self.connect()
        return await cognee.get_memory_provenance_graph(include_memory=True)
