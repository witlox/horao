# -*- coding: utf-8 -*-#
import logging


def is_alive():
    logging.info("Calling Keep Alive")
    return "is alive", 200
