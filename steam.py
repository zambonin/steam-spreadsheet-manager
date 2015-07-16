#!/usr/bin/env python

import csv
import datetime
import glob
import json
import os
import re
import requests
import subprocess
import sys

import matplotlib.pyplot as plt

private_data = json.load(open('config.json'))
api_key = private_data['api_key']
steamid = private_data['steamid']
steam_login = private_data['steam_login']

with open('prices.csv') as file:
    prices = dict(filter(None, csv.reader(file)))

with open(steamid + ".json", 'r') as file:
    my_games = json.load(file)


def exclude_free_games(games):
    cont = 1
    for game in games:
        if appid(game) not in list(prices.keys()):
            cont += 1

    freeless = games[:len(games) - cont] + [games[-1]]
    return sorted(freeless, key=lambda k: k['appid'])


def icon(game):
    return "http://media.steampowered.com/steamcommunity/public/" + \
            "images/apps/"+appid(game)+"/"+game['img_icon_url']+".jpg"


def appid(game):
    return str(game['appid'])


def name(game):
    return game['name']


def price(game):
    return float(prices[appid(game)])


def time(game):
    return float("{0:.2f}".format(game['playtime_forever'] / 60))


def pph(game):
    spent = time(game)
    if not spent:
        return 0
    if spent < 1:
        return spent
    return price(game) / spent


def read_games():
    def numericalSort(value):
        parts = re.compile(r'(\d+)').split(value)
        parts[1::2] = map(int, parts[1::2])
        return parts

    store_info = []
    for file in sorted(glob.glob("temp/*.in"), key=numericalSort):
        with open(file) as game:
            store_info.append(json.loads(game.read()))
    return store_info


def discount(game):
    app = appid(game)
    for any_game in read_games():
        if app in list(any_game.keys()):
            game = any_game[list(any_game.keys())[0]]

    if game['success'] and "price_overview" in list(game['data'].keys()):
        return abs(float(prices[str(game['data']['steam_appid'])]) /
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


if "--update" in sys.argv:
    bashcmd = "steamcmd +login " + steam_login + \
              " +licenses_print +quit > licenses.txt"
    process = subprocess.Popen(bashcmd, shell=True, stdout=subprocess.PIPE)

    before = datetime.datetime.now()
    url = "http://api.steampowered.com/IPlayerService/GetOwnedGames/v1/" + \
        "?key="+api_key+"&steamid=" + steamid + \
        "&include_appinfo=1&include_played_free_games=1"

    response = requests.get(url).json()['response']
    game_count = response['game_count']
    freeless = exclude_free_games(response['games'])

    with open(steamid + ".json", 'w') as file:
        json.dump(freeless, file)

    for game, count in zip(freeless, range(game_count)):
        n = str(game['appid']) + ".in"
        os.makedirs("temp", exist_ok=True)

        with open("temp/" + n, 'w') as file:
            print("[{:2.1%}] ".format(count / game_count) + "Writing " + n,
                  end="\r")
            json.dump(requests.get("http://store.steampowered.com/api/" +
                                   "appdetails/?appids=" +
                                   str(game['appid'])).json(), file)

    print("Time spent on storing files: %s" %
          str(datetime.datetime.now() - before))

if "--plot" in sys.argv:
    hours_played, price_paid, price_per_hour, game_name = [], [], [], []
    games = exclude_free_games(my_games)

    fig = plt.figure()
    ax = fig.add_subplot(111)

    for game in games:
        its_name = name(game)
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
