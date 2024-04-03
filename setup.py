# coding: utf-8

from setuptools import setup, find_packages

NAME = "horao"
VERSION = "1.0.0"

# To install the library, run the following
#
# python setup.py install
#
# prerequisite: setuptools
# http://pypi.python.org/pypi/setuptools

REQUIRES = ["Starlette"]

setup(
    name=NAME,
    version=VERSION,
    description="HORAO - management engine for hybrid multi-cloud environments",
    author_email="pim@witlox.io",
    url="",
    keywords=["OpenAPI", "Starlette"],
    install_requires=REQUIRES,
    packages=find_packages(),
    long_description="""\
    Management engine for hybrid multi-cloud environments
    """,
)
