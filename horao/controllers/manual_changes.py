# -*- coding: utf-8 -*-#
"""Controllers for manually changing the state of the hardware.
This should not be used outside of testing and development.
"""
from __future__ import annotations


from horao.conceptual.crdt import CRDTList
from horao.physical.hardware import Hardware


def apply_changes_to_infrastructure(
    origin: CRDTList[Hardware], updates: CRDTList[Hardware]
) -> None:
    """
    Apply a list of changes to the infrastructure.
    These lists need to be symmetric, i.e. the same length and the same order.
    :param origin: original state
    :param updates: updated state
    :return: None
    """
    pass
