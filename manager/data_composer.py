#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
from collections import ChainMap
from datetime import datetime
from json import dump, load
from os import path
from re import findall
from .data_conveyor import (get_games, get_original_price, get_achievements,
                            read_license_data)


def parse_games_data(api_key, steamid):
    return {game.pop('appid'): game for game in get_games(api_key, steamid)}


def parse_prices_data(api_key, steamid, file_path):
    prices_file = load(open(file_path)) if path.isfile(file_path) else {}
    games = {game['appid']: {'name': game['name']} for game in
             get_games(api_key, steamid)}

    apps = sorted(set(games.keys()) - set(int(i) for i in prices_file.keys()))

    for app in apps:
        prices_file[app] = {
            'paid': get_paid_price(games[app]['name']),
            'orig': get_original_price(str(app)),
        }

    dump(prices_file, open(file_path, 'w', encoding='utf8'), indent=2)
    return {int(k): v for k, v in prices_file.items()}


def parse_achievements_data(api_key, steamid):
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
    return ("=IMAGE(\"http://media.steampowered.com/steamcommunity/"
            "public/images/apps/{}/{}.jpg\"; 1)").format(appid, icon)


def price_per_hour(game):
    return (game['paid'] / game['time']) if game['time'] else 0


def discount_info(game):
    return (1 - (game['paid'] / game['orig'])) if game['orig'] else 0


def shape(api_key, steamid, login, prices_file):
    games = parse_games_data(api_key, steamid)
    prices = parse_prices_data(api_key, steamid, prices_file)
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
