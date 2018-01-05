#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""data_composer.py

Aggregates all functions related to transforming and organizing data into
standardized dictionary objects.
"""

import asyncio
from collections import ChainMap
from datetime import datetime
from json import dump, load
from os import path
from re import findall
from .data_conveyor import (get_games, get_original_price, get_achievements,
                            read_license_data)


def parse_games_data(api_key, steamid):
    """
    Reshapes the JSON content containing games associated to an account
    returned by the Steam API.

    Args:
        api_key:    a string representing the Steam web API key.
        steamid:    a string representing the identifier for a Steam account.

    Returns:
        A dictionary with game identifiers as keys and dictionaries with
        further information, such as the game name and playtime, as values.
    """
    return {game.pop('appid'): game for game in get_games(api_key, steamid)}


def parse_prices_data(api_key, steamid, file_path, c_code):
    """
    Creates and/or updates a file containing information about how much one
    has paid for each game on their account. This file is updated only if
    there were new games added to the account.

    Args:
        api_key:    a string representing the Steam web API key.
        steamid:    a string representing the identifier for a Steam account.
        file_path:  a string representing the absolute file path for the
                    prices file to be written to.
        c_code:     a string representing a two-letter country code.

    Returns:
        A dictionary with game identifiers as keys and dictionaries with
        information about the original and paid prices as values.
    """
    prices_file = load(open(file_path)) if path.isfile(file_path) else {}
    games = {game['appid']: {'name': game['name']} for game in
             get_games(api_key, steamid)}

    apps = sorted(set(games.keys()) - set(int(i) for i in prices_file.keys()))

    for app in apps:
        prices_file[app] = {
            'paid': get_paid_price(games[app]['name']),
            'orig': get_original_price(str(app), c_code),
        }

    dump(prices_file, open(file_path, 'w', encoding='utf8'), indent=2)
    return {int(k): v for k, v in prices_file.items()}


def parse_achievements_data(api_key, steamid):
    """
    Simplifies each game's achievements JSON request returned by the Steam API
    and merges them together.

    Args:
        api_key:    a string representing the Steam web API key.
        steamid:    a string representing the identifier for a Steam account.

    Returns:
        A dictionary with game identifiers as keys and dictionaries with
        the achievement completion percentage for a game as values.
    """
    games = parse_games_data(api_key, steamid)
    achiev_dict = {appid: {'achv': ""} for appid in games.keys()}
    apps = [k for k, v in games.items()
            if 'has_community_visible_stats' in v.keys()]

    loop = asyncio.get_event_loop()
    content = loop.run_until_complete(get_achievements(api_key, steamid, apps))

    for data in content:
        try:
            app = next(iter(data))
            stats = data[app]['playerstats']['achievements']
            count = sum(ach['achieved'] for ach in stats) / len(stats)
            achiev_dict[app]['achv'] = count
        except KeyError:
            continue

    return achiev_dict


def parse_licenses_data(login):
    """
    Interprets SteamCMD's output when queried about licenses tied up to an
    account.

    Args:
        login:  a string representing the Steam login username.

    Returns:
        A dictionary with game identifiers as keys and dictionaries with
        further information, such as the date of purchase for a license and
        package identifier, as values.
    """
    content = read_license_data(login)
    indices = [i for i, line in enumerate(content) if "License" in line][1:]

    all_licenses = [{
        int(app) : {
            'package': int(findall(r'(\d+)', content[ind])[0]),
            'date': datetime.strptime(
                findall(r'.* : (.+?) in .*', content[ind + 1])[0],
                '%a %b %d %H:%M:%S %Y'),
            'location': findall(r'"(.*?)"', content[ind + 1])[0],
            'license': findall(r'.*\, (.*)', content[ind + 1])[0],
        } for app in findall(r'(\d+)', content[ind + 2])[:-1]
    } for ind in indices]

    return dict(ChainMap(*all_licenses))


def get_paid_price(game):
    """
    Input loop constraining what can be considered as a valid paid price for
    a game.

    Args:
        game:   a string with the game's name.

    Returns:
        A non-negative float number.
    """
    valid = False
    while not valid:
        try:
            paid = float(input("Price paid for {}: ".format(game)))
            if paid < 0:
                raise ValueError
            valid = True
        except ValueError:
            print("Invalid price.", end=' ')

    return paid


def show_icon(appid, icon):
    """
    Constructs a valid Google Sheets' cell containing an image.

    Args:
        appid:  unique identifier for any product on Steam's store.
        icon:   string containing the SHA-1 hash for the game's icon.

    Returns:
        A string that fits an image into a cell, maintaning aspect ratio.
    """
    return ("=IMAGE(\"http://media.steampowered.com/steamcommunity/"
            "public/images/apps/{}/{}.jpg\"; 1)").format(appid, icon)


def price_per_hour(game):
    """Ratio between paid price and playtime."""
    return (game['paid'] / game['time']) if game['time'] else 0


def discount_info(game):
    """Percentage of paid price in relation to the original value."""
    return (1 - (game['paid'] / game['orig'])) if game['orig'] else 0


def shape(api_key, steamid, login, file_path, c_code):
    """
    Organizes and merges all dictionaries containing information about a game.

    Args:
        api_key:    a string representing the Steam web API key.
        steamid:    a string representing the identifier for a Steam account.
        login:      a string representing the Steam login username.
        file_path:  a string representing the absolute file path for the
                    prices file to be written to.
        c_code:     a string representing a two-letter country code.

    Returns:
        A flattened list of the dictionaries, representing separate cells
        of a spreadsheet.
    """
    games = parse_games_data(api_key, steamid)
    prices = parse_prices_data(api_key, steamid, file_path, c_code)
    achievements = parse_achievements_data(api_key, steamid)
    licenses = parse_licenses_data(login)

    values = []
    for key, value in sorted(games.items()):
        value['time'] = value.pop('playtime_forever') / 60
        for _dict in [prices, achievements, licenses]:
            value.update(_dict[key])
        values += [
            show_icon(key, value['img_icon_url']), key, value['name'],
            value['paid'], value['time'], price_per_hour(value),
            value['achv'], discount_info(value), value['package'],
            value['date'], value['location'], value['license']
        ]

    return values
