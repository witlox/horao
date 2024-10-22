from __future__ import annotations

from hashlib import sha256
from typing import Type

from horao.crdts.protocols import CRDT, Update


def get_merkle_tree(
    crdt: CRDT, /, *, update_class: Type[Update] = Update
) -> list[bytes | list[bytes] | dict[bytes, bytes]]:
    """
    Get a Merkle tree of the history of Updates of the form
    [root, [content_id for update in crdt.history()], {
    content_id: packed for update in crdt.history()}] where
    packed is the result of update.pack() and content_id is the
    sha256 of the packed update.
    :param crdt: CRDT to get the Merkle tree from
    :param update_class: type of update to use
    :return: list[bytes | list[bytes] | dict[bytes, bytes
    """
    history = crdt.history(update_class=update_class)
    leaves = [update.pack() for update in history]
    leaf_ids = [sha256(leaf).digest() for leaf in leaves]
    history = {leaf_id: leaf for leaf_id, leaf in zip(leaf_ids, leaves)}
    leaf_ids.sort()
    root = sha256(b"".join(leaf_ids)).digest()
    return [root, leaf_ids, history]


def resolve_merkle_tree(crdt: CRDT, tree: list[bytes, list[bytes]]) -> list[bytes]:
    """
    Accept a merkle tree of form [root, leaves] from another node.
    Return the leaves that need to be resolved and merged for
    synchronization.
    :param crdt: CRDT to resolve the tree for
    :param tree: tree to resolve
    :return: list[bytes]
    :raises ValueError: invalid tree
    """
    if len(tree) < 2:
        raise ValueError("tree has no (or only one) leaves")
    local_history = get_merkle_tree(crdt)
    if local_history[0] == tree[0]:
        return []
    return [leaf for leaf in tree[1] if leaf not in local_history[1]]
