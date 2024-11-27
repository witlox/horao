# -*- coding: utf-8 -*-#
"""Controller for synchronization calls to peers.
There are 2 mechanisms for synchronization:
- Time based: a preset interval to synchronize with all peers
- Event based: a preset number of changes to synchronize with all peers
"""
from __future__ import annotations

import json
import logging
import os
import platform
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import httpx
import jwt

from horao.logical.infrastructure import LogicalInfrastructure
from horao.persistance import HoraoEncoder, init_session


class SynchronizePeers:
    """
    Synchronize with all peers.
    """

    def __init__(
        self,
        infrastructure: LogicalInfrastructure,
        peers: Optional[List[str]] = None,
        max_changes: Optional[int] = None,
        sync_delta: Optional[int] = None,
    ) -> None:
        """
        Create instance
        :param infrastructure: LogicalInfrastructure
        :param peers: list of peers
        :param max_changes: number of changes to synchronize
        :param sync_delta: interval in seconds between synchronizations
        """
        self.logger = logging.getLogger(__name__)
        self.infrastructure = infrastructure
        self.peers = (
            peers
            if not os.getenv("PEERS", None)
            else peers + os.getenv("PEERS", "").split(",")  # type: ignore
        )
        self.max_changes = (
            max_changes if max_changes else int(os.getenv("MAX_CHANGES", 100))
        )
        self.sync_delta = (
            sync_delta if sync_delta else int(os.getenv("SYNC_DELTA", 300))
        )
        self.session = init_session()
        # note that the event handler should support async
        for dc, dcs in self.infrastructure.items():
            dc.add_listeners(self.synchronize)

    async def synchronize(self) -> None:
        """
        Synchronize with all peers.
        :return: Dict of Peer:Exception for each peer that failed to synchronize
        """
        timedelta_exceeded = False
        last_sync = await self.session.load("last_sync")
        if last_sync and datetime.now() - last_sync < timedelta(
            seconds=self.sync_delta
        ):
            timedelta_exceeded = True
        max_changes_exceeded = False
        if self.infrastructure.change_count() > self.max_changes:
            max_changes_exceeded = True
        if not timedelta_exceeded and not max_changes_exceeded:
            return None
        for peer in self.peers:  # type: ignore
            token = jwt.encode(
                dict(peer=os.getenv("HOST_ID", platform.node())),
                os.environ["PEER_SECRET"],
                algorithm="HS256",
            )
            try:
                lg = httpx.post(
                    "/synchronize",
                    headers={"Peer": "true", "Authorization": f"Bearer {token}"},
                    json=json.dumps(await self.session.items(), cls=HoraoEncoder),
                )
                lg.raise_for_status()
            except httpx.HTTPError as e:
                self.logger.error(f"Error synchronizing with {peer}: {e}")
        await self.session.save("last_sync", datetime.now())
