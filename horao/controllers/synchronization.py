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
from typing import List, Optional

import httpx  # type: ignore
import jwt  # type: ignore

from horao.logical.infrastructure import LogicalInfrastructure
from horao.persistance import HoraoEncoder, init_session


class SynchronizePeers:
    """
    Synchronize with all peers.
    """

    def __init__(
        self,
        logical_infrastructure: LogicalInfrastructure,
        peers: Optional[List[str]] = None,
        max_changes: Optional[int] = None,
        sync_delta: Optional[int] = None,
    ) -> None:
        """
        Create instance
        :param logical_infrastructure: LogicalInfrastructure
        :param peers: list of peers
        :param max_changes: number of changes to synchronize
        :param sync_delta: interval in seconds between synchronizations
        """
        self.logger = logging.getLogger(__name__)
        self.logical_infrastructure = logical_infrastructure
        self.peers = peers if peers else []
        self.peers = self.peers + os.getenv("PEERS", "").split(",")  # type: ignore
        self.max_changes = (
            max_changes if max_changes else int(os.getenv("MAX_CHANGES", 100))
        )
        self.sync_delta = (
            sync_delta if sync_delta else int(os.getenv("SYNC_DELTA", 300))
        )
        self.session = init_session()
        for dc in self.logical_infrastructure.infrastructure.keys():
            dc.add_listeners(self.synchronize)

    def synchronize(self, changes: Optional[List] = None) -> datetime | None:
        """
        Synchronize with all peers, if one of the following conditions is met:
        - there was no previous synchronization time stamp.
        - the timedelta between previous synchronization and now is greater than set bound
        - the amount of changes on the stack exceed the threshold that was set
        will only call synchronize if there are any changes if the timer expires
        note: currently only the infrastructure is tracked, changes to claims and constraints are not tracked
        :param changes: optional list of changes
        :return: None (if nothing happened) or datetime if synchronized
        """
        if not self.peers:
            return None
        sync_time = datetime.now()
        timedelta_exceeded = False
        last_sync = self.session.load("last_sync")
        if not last_sync or sync_time - datetime.fromisoformat(last_sync) > timedelta(
            seconds=self.sync_delta
        ):
            timedelta_exceeded = True
        max_changes_exceeded = False
        if changes and len(changes) > self.max_changes:
            max_changes_exceeded = True
        if not timedelta_exceeded and not max_changes_exceeded:
            return None
        self.logger.debug("Synchronizing with peers")
        for peer in self.peers:  # type: ignore
            token = jwt.encode(
                dict(peer=os.getenv("HOST_ID", platform.node())),
                os.environ["PEER_SECRET"],
                algorithm="HS256",
            )
            try:
                lg = httpx.post(
                    f"{peer}/synchronize",
                    headers={"Peer": "true", "Authorization": f"Bearer {token}"},
                    json=json.dumps(self.logical_infrastructure, cls=HoraoEncoder),
                )
                lg.raise_for_status()
            except httpx.HTTPError as e:
                self.logger.error(f"Error synchronizing with {peer}: {e}")
        self.session.save("last_sync", sync_time)
        self.logical_infrastructure.clear_changes()
        return sync_time
