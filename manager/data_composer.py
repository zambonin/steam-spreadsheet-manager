#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""data_composer.py

Aggregates all functions related to transforming and organizing data into
standardized dictionary objects.
"""

import asyncio
from collections import ChainMap
from datetime import datetime
from re import findall

from .data_conveyor import (get_games, get_prices, get_achievements,
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
    return {str(game.pop('appid')): game for game in get_games(api_key, steamid)}


def parse_prices_data(app_list, itad_api_key, itad_region, itad_country):
    """
    Modifies price data returned by IsThereAnyDeal.com to create a price per
    hour metric.

    Args:
        app_list:       list of Steam appids.
        itad_api_key:   a IsThereAnyDeal.com API key.
        itad_region:    a region identifier according to [1].
        itad_country:   a two-letter country identifier according to [1].

    [1] https://api.isthereanydeal.com/v01/web/regions/

    Returns:
        A dictionary with game identifiers as keys and dictionaries with
        information about the original and lowest prices as values.
    """
    ids, current, lowest = get_prices(app_list, itad_api_key, itad_region,
                                      itad_country)

    prices = {}
    for k, v in ids['data'].items():
        app = k.split('/')[1]
        prices[app] = {'orig': 0.0, 'lowest': 0.0, 'discount': 0.0}
        try:
            price = current['data'][v]['list']
            prices[app]['orig'] = price[0]['price_old'] if price else 0.0
            prices[app]['lowest'] = lowest['data'][v]['price']
            prices[app]['discount'] = lowest['data'][v]['cut'] / 100
        except KeyError:
            continue

    return prices


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
        app: {
            'package': int(findall(r'(\d+)', content[ind])[0]),
            'date': datetime.strptime(
                findall(r'.* : (.+?) in .*', content[ind + 1])[0],
                '%a %b %d %H:%M:%S %Y'),
            'location': findall(r'"(.*?)"', content[ind + 1])[0],
            'license': findall(r'.*, (.*)', content[ind + 1])[0],
        } for app in findall(r'(\d+)', content[ind + 2])[:-1]
    } for ind in indices]

    return dict(ChainMap(*all_licenses))


def price_per_hour(game):
    """Ratio between price and playtime."""
    return (game['lowest'] / game['time']) if game['time'] else 0


def shape(steam_api_key, steamid, login, itad_api_key, itad_region="us",
          itad_country="us"):
    """
    Organizes and merges all dictionaries containing information about a game.

    Args:
        steam_api_key:  a Steam web API key.
        steamid:        a unique 17-digit identifier for a Steam account.
        login:          a Steam login username.
        itad_api_key:   a IsThereAnyDeal.com API key.
        itad_region:    a region identifier according to [1].
        itad_country:   a two-letter country identifier according to [1].

    [1] https://api.isthereanydeal.com/v01/web/regions/

    Returns:
        A JSON with all pertinent data.
    """
    games = parse_games_data(steam_api_key, steamid)
    prices = parse_prices_data(list(games), itad_api_key, itad_country,
                               itad_region)
    achievements = parse_achievements_data(steam_api_key, steamid)
    licenses = parse_licenses_data(login)

    for key, value in sorted(games.items()):
        value['time'] = value.pop('playtime_forever') / 60
        for _dict in [prices, achievements, licenses]:
            value.update(_dict[key])
        value['date'] = value['date'].strftime('%d/%m/%Y %X')
        if 'has_community_visible_stats' in value.keys():
            value.pop('has_community_visible_stats')
        if 'playtime_2weeks' in value.keys():
            value.pop('playtime_2weeks')
        value['pph'] = price_per_hour(value)

    return {steamid: games}
