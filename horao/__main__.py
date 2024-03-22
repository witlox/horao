#!/usr/bin/env python
# -*- coding: utf-8 -*-#

from horao import init_api


def main():
    app = init_api()
    app.run(port=8081, debug=False)


if __name__ == "__main__":
    main()
