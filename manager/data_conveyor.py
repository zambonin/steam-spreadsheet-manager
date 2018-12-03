#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""data_conveyor.py

Aggregates all functions related to communication with external entities, such
as Steam services.

    * `requests.get` issues a simple HTTP request to a web page.
"""

import asyncio
from subprocess import Popen, PIPE

from requests import get


def get_games(api_key, steamid):
    """
    Requests which games an user owns on Steam.

    Args:
        api_key:    a string representing the Steam web API key.
        steamid:    a string representing the identifier for a Steam account.

    Returns:
        A dictionary file containing information about games associated to
        an user's account.
    """
    url = "http://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
    return get(url, params={
        "key": api_key, "steamid": steamid,
        "include_played_free_games": 1, "include_appinfo": 1,
    }).json()['response']['games']


def get_prices(app_list, api_key, region, country):
    """
    Queries IsThereAnyDeal.com the current and historic prices for a list of
    games.

    Args:
        app_list:   list of Steam appids.
        api_key:    a IsThereAnyDeal.com API key.
        region:     a region identifier according to [1].
        country:    a two-letter country identifier according to [1].

    [1] https://api.isthereanydeal.com/v01/web/regions/

    Returns:
        A triple of raw dictionaries with site-specific identifiers, current
        and lowest price data.
    """
    itad_url = "https://api.isthereanydeal.com/v01/game"

    raw_plains = get(f'{itad_url}/plain/id', params={
        "key": api_key, "shop": "steam",
        "ids": ",".join(f'app/{g}' for g in app_list)
    }).json()

    plains = list(raw_plains['data'].values())
    bundles = [plains[(i * 150):(i + 1) * 150]
               for i in range(int(len(plains) / 150) + 1)]

    prices, lowest = {'data': {}}, {'data': {}}
    for bundle in bundles:
        param_prices = {
            "key": api_key, "shops": "steam", "region": region,
            "country": country, "plains": ",".join(bundle)
        }

        prices['data'].update(get(f'{itad_url}/prices', params=param_prices).json()['data'])
        # accurate description would consider time when license was acquired,
        # but no need to hammer the api like that
        lowest['data'].update(get(f'{itad_url}/lowest', params=param_prices).json()['data'])

    return raw_plains, prices, lowest


async def get_achievements(api_key, steamid, appids):
    """
    Gets achievements asynchronously for multiple games through Steam's API.

    Args:
        api_key:    a string representing the Steam web API key.
        steamid:    a string representing the identifier for a Steam account.
        appids:     a list with unique identifier of games that may have stats.

    Returns:
        A list of JSON pre-formatted responses for all game identifiers.
    """

    def get_game_achievs(_id):
        """Requests a raw JSON containing info about a game's achievements,
        identified by a unique identifier."""
        return {_id: get(url.format(api_key, steamid, _id)).json()}

    url = ("http://api.steampowered.com/ISteamUserStats/"
           "GetPlayerAchievements/v0001/?key={}&steamid={}&appid={}")
    loop = asyncio.get_event_loop()
    return await asyncio.gather(*[
        loop.run_in_executor(None, get_game_achievs, _id) for _id in appids])


def read_license_data(login):
    """
    Queries about licenses by executing the SteamCMD binary.

    Args:
        login:  a string representing the Steam login username.

    Returns:
        A list of strings containing the called command's stdout lines.
    """
    cmd = "steamcmd +login {} +licenses_print +quit".format(login).split()
    return [i.decode() for i in Popen(cmd, stdout=PIPE).stdout]
