#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
from subprocess import Popen, PIPE

from gspread import authorize
from oauth2client.service_account import ServiceAccountCredentials
from requests import get

def get_games(api_key, steamid):
    url = "http://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
    return get(url, params={
        "key": api_key, "steamid": steamid,
        "include_played_free_games": 1, "include_appinfo": 1,
        }).json()['response']['games']


def get_original_price(game):
    url = "http://store.steampowered.com/api/appdetails"
    output = get(url, params={"appids": game, "cc": "br"}).json()

    try:
        return output[game]['data']['price_overview']['initial'] / 100
    except KeyError:
        return 0.0


async def get_achievements(api_key, steamid, appids):
    def get_game_achievs(_id):
        url = ("http://api.steampowered.com/ISteamUserStats/"
               "GetPlayerAchievements/v0001/?key={}&steamid={}&appid={}")
        return {_id : get(url.format(api_key, steamid, _id)).json()}

    loop = asyncio.get_event_loop()
    return await asyncio.gather(*[
        loop.run_in_executor(None, get_game_achievs, _id) for _id in appids])


def read_license_data(login):
    cmd = "steamcmd +login {} +licenses_print +quit".format(login).split()
    return [i.decode() for i in Popen(cmd, stdout=PIPE).stdout]


def upload(game_list, keyfile, ss_key):
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        keyfile, ['https://spreadsheets.google.com/feeds'])
    worksheet = authorize(credentials).open_by_key(ss_key).sheet1

    index, length = 2, int(len(game_list) / (ord('L') - ord('A') + 1))
    worksheet.resize(length + (index - 1))

    cell_list = worksheet.range('A{}:L{}'.format(index, length + (index - 1)))

    for cell, value in zip(cell_list, game_list):
        cell.value = value
    worksheet.update_cells(cell_list)
