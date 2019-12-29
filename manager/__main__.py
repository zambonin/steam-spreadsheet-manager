#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""__main__.py

The main file for a Python module that outputs detailed information about a
Steam library to a JSON file.
"""

from __future__ import absolute_import
from json import load, decoder, dump
from sys import argv
from .data_composer import shape

try:
    PRIVATE_DATA = load(open(argv[1]))
    dump(
        shape(
            PRIVATE_DATA["steam_api_key"],
            PRIVATE_DATA["steamid"],
            PRIVATE_DATA["steam_login"],
            PRIVATE_DATA["itad_api_key"],
            PRIVATE_DATA["itad_region"],
            PRIVATE_DATA["itad_country"],
        ),
        open(PRIVATE_DATA["output_file"], "w"),
        indent=2,
    )
except (IndexError, FileNotFoundError, decoder.JSONDecodeError):
    raise SystemExit("Valid configuration file needed!")
