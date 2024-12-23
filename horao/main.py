#!/usr/bin/env python
# -*- coding: utf-8 -*-#
"""Main entrypoint for running HORAO in development mode, for testing only!"""
import os

import uvicorn  # type: ignore


def main():
    os.environ["DEBUG"] = "True"
    os.environ["UI"] = "True"
    uvicorn.run(
        "horao:init",
        host="127.0.0.1",
        port=8081,
        log_level="debug",
        reload=True,
        factory=True,
    )


if __name__ == "__main__":
    main()
