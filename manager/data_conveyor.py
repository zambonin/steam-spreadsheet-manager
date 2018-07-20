#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""data_conveyor.py

Aggregates all functions related to communication with external entities, such
as Google and Steam services.

    * `gspread.authorize` logins to Google API using OAuth2 credentials.
    * `oauth2client.service_account.ServiceAccountCredentials` handles the
      creation of the object containing the credentials.
    * `requests.get` issues a simple HTTP request to a web page.
"""

import asyncio
from subprocess import Popen, PIPE

from gspread import authorize
from oauth2client.service_account import ServiceAccountCredentials
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


def get_original_price(appid, c_code):
    """
    Gets the original price for a game through Steam store's open API.

    Args:
        appid:  unique identifier for any product on Steam's store.
        c_code: a string representing a two-letter country code.

    Returns:
        A non-negative float representing the original price for a game on
        Steam's store if it is still available.
    """
    url = "http://store.steampowered.com/api/appdetails"
    output = get(url, params={"appids": appid, "cc": c_code}).json()

    try:
        return output[appid]['data']['price_overview']['initial'] / 100
    except KeyError:
        return 0.0


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
        return {_id : get(url.format(api_key, steamid, _id)).json()}

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


def upload(game_list, keyfile, ss_key):
    """
    Performs authentication using OAuth2 and updates all cells at once,
    resizing the spreadsheet if needed.

    Args:
        game_list:  a list of strings containing information to be written to
                    spreadsheet cells.
        keyfile:    a file path pointing to a JSON file with the private key
                    used for authentication on Google's services.
        ss_key:     a string representing the unique key for a spreadsheet.
    """
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        keyfile, ['https://spreadsheets.google.com/feeds'])
    worksheet = authorize(credentials).open_by_key(ss_key).sheet1

    index, length = 2, int(len(game_list) / (ord('L') - ord('A') + 1))
    worksheet.resize(length + (index - 1))

    cell_list = worksheet.range('A{}:L{}'.format(index, length + (index - 1)))

    for cell, value in zip(cell_list, game_list):
        cell.value = value
    worksheet.update_cells(cell_list, 'USER_ENTERED')
