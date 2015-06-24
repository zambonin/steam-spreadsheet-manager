#!/usr/bin/env python

import csv
import datetime
import glob
import json
import math
import re
import requests
import sys

import matplotlib.pyplot as plt

private_data = json.load(open('config.json'))
api_key = private_data['api_key']
steamid = private_data['steamid']

if "--update" in sys.argv:
    before = datetime.datetime.now()
    url = "http://api.steampowered.com/IPlayerService/GetOwnedGames/v1/" + \
        "?key="+api_key+"&steamid=" + steamid + \
        "&include_appinfo=1&include_played_free_games=1"

    my_games = requests.get(url).json()['response']
    game_count = my_games['game_count']

    with open(steamid + ".json", 'w') as file:
        json.dump(my_games['games'], file)

    for game, count in zip(my_games['games'], range(game_count)):
        with open('temp/' + str(game['appid']) + ".in", 'w') as file:
            print("[{:2.1%}] Writing to local storage"
                  .format(float(count / game_count)), end="\r")
            json.dump(requests.get("http://store.steampowered.com/api/" +
                      "appdetails/?appids=" + str(game['appid'])).json(), file)

    print("Time spent on storing files: %s" %
          str(datetime.datetime.now() - before))

with open(steamid + ".json", 'r') as file:
    my_games = json.load(file)


def list_games():
    def numericalSort(value):
        parts = re.compile(r'(\d+)').split(value)
        parts[1::2] = map(int, parts[1::2])
        return parts

    store_info = []
    for file in sorted(glob.glob("temp/*.in"), key=numericalSort):
        with open(file) as game:
            store_info.append(json.loads(game.read()))
    return store_info

with open('prices.csv') as file:
    prices = dict(filter(None, csv.reader(file)))

with open('packages.csv') as file:
    packages = dict(filter(None, csv.reader(file)))


def icon(game):
    for any_game in my_games:
        if appid(game) == any_game['appid']:
            url = any_game['img_icon_url']
            return "http://media.steampowered.com/steamcommunity/public/" + \
                   "images/apps/"+str(appid(game))+"/"+url+".jpg"


def appid(game):
    return int(list(game.keys())[0])


def subid(game):
    return int(packages[str(appid(game))])


def name(appid):
    for game in my_games:
        if appid == game['appid']:
            return game['name']


def price(game):
    return float(prices[list(game.keys())[0]])


def time(game):
    for any_game in my_games:
        if appid(game) == any_game['appid']:
            return float("{0:.2f}".format(any_game['playtime_forever'] / 60))


def pph(game):
    spent = time(game)
    if not spent:
        return 0
    if spent < 1:
        return spent
    return price(game) / spent


def discount(game):
    game = game[list(game.keys())[0]]
    if game['success'] and "price_overview" in list(game['data'].keys()):
        return math.fabs(float(prices[str(game['data']['steam_appid'])]) /
                         (game['data']['price_overview']['initial']/100) - 1)
    return 0


def achiev(game):
    data = requests.get("http://api.steampowered.com/ISteamUserStats/" +
                        "GetPlayerAchievements/v0001/?appid=" +
                        str(appid(game)) +
                        "&key="+api_key+"&steamid=" +
                        steamid).json()
    data = data['playerstats']
    if data['success'] and 'achievements' in data.keys():
        cont = 0
        for ach in data['achievements']:
            if ach['achieved']:
                cont += 1
        return cont / len(data['achievements'])
    else:
        return ""

if "--plot" in sys.argv:
    hours_played, price_paid, price_per_hour, game_name = [], [], [], []

    fig = plt.figure()
    ax = fig.add_subplot(111)

    for game in list_games():
        its_name = name(appid(game))
        its_time = time(game)
        its_price = price(game)
        its_cost = pph(game)

        if its_price and its_time:
            game_name.append(its_name)
            hours_played.append(its_time)
            price_paid.append(its_price)
            price_per_hour.append(its_cost)

            if(its_cost >= 1):
                ax.text(its_time, its_price, its_name, fontsize=6,
                        horizontalalignment='left', verticalalignment='bottom')

    sct = ax.scatter(hours_played, price_paid, c=price_per_hour, s=75,
                     edgecolor='w').set_alpha(0.75)
    ax.axis([0, 15, 0, 20])
    plt.savefig('bubble_chart.png')
