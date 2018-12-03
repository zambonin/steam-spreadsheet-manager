#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""__main__.py

The main file for a Python module that outputs detailed information about a
Steam library to a JSON file.
"""

from json import load, decoder
from pprint import pprint
from sys import argv
from .data_composer import shape

try:
    PRIVATE_DATA = load(open(argv[1]))
    pprint(shape(PRIVATE_DATA['steam_api_key'], PRIVATE_DATA['steamid'],
                 PRIVATE_DATA['steam_login'], PRIVATE_DATA['itad_api_key'],
                 PRIVATE_DATA['itad_region'], PRIVATE_DATA['itad_country']))
except (IndexError, FileNotFoundError, decoder.JSONDecodeError):
    raise SystemExit("Valid configuration file needed!")
