#!/usr/bin/env python
# -*- coding: utf-8 -*-#
"""Main module for the HORAO API, for testing only!"""
import os

import uvicorn  # type: ignore

from horao import init_api

app = init_api()


def main():
    os.environ["ENVIRONMENT"] = "development"
    os.environ["DEBUG"] = "True"
    uvicorn.run(
        "__main__:app",
        host="127.0.0.1",
        port=8081,
        log_level="debug",
        reload=True,
    )


if __name__ == "__main__":
    main()
