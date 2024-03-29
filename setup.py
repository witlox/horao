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

REQUIRES = ["connexion"]

setup(
    name=NAME,
    version=VERSION,
    description="HORAO - management engine for hybrid multi-cloud environments",
    author_email="pim@witlox.io",
    url="",
    keywords=["Swagger", "Connexion"],
    install_requires=REQUIRES,
    packages=find_packages(),
    package_data={"": ["spec/production.yaml"]},
    include_package_data=True,
    entry_points={"console_scripts": ["swagger_server=swagger_server.__main__:main"]},
    long_description="""\
    Basic example to connexion
    """,
)
