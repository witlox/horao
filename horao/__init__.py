#!/usr/bin/env python
# -*- coding: utf-8 -*-#

import horao.controllers
import horao.models

from connexion import AsyncApp  # type: ignore


def init_api():
    app = AsyncApp(__name__)
    app.add_api("./swagger/swagger.yaml")
    return app
