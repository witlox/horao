#!/usr/bin/env python
# -*- coding: utf-8 -*-#
"""Main module for the HORAO API."""
from horao import init_api


def main():
    app = init_api()
    app.run(port=8081)


if __name__ == "__main__":
    main()
