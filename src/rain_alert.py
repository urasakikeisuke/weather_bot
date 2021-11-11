"""rain_alert.py"""

import os
import json
import math
import datetime
from dateutil import parser
from typing import Any, Dict, Final, List, Optional
from urllib import request, parse, error
from pprint import pprint

import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from constants import *


YAHOO_APPID: Final = os.getenv("YAHOO_APPID")
BOT_TOKEN: Final = os.getenv("SLACK_BOT_TOKEN")
WORKSPACE_URL: Final = os.getenv("SLACK_WORKSPACE_URL")
if WORKSPACE_URL is None:
    raise KeyError


def _get_strength(rainfall: float) -> str:
    strength: str
    if rainfall < 3.0:
        strength = "小"
    elif 3.0 <= rainfall < 5.0:
        strength = "弱い"
    elif 5.0 <= rainfall < 10.0:
        strength = "中"
    elif 10.0 <= rainfall < 20.0:
        strength = "やや強い"
    elif 20.0 <= rainfall < 30.0:
        strength = "強い"
    elif 30.0 <= rainfall < 50.0:
        strength = "激しい"
    elif 50.0 <= rainfall < 80.0:
        strength = "非常に激しい"
    else:
        strength = "猛烈な"

    return strength


def _render_img(plot_x: List[int], plot_y: List[float]):
    plt.rcParams['figure.subplot.bottom'] = 0.17
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.bar(plot_x, plot_y, width=3, color='lightblue', zorder=2, align='center')
    ax.set_xlim(0, 60)
    ax.set_xlabel("minutes after", color='gray')
    ax.set_ylabel("Rainfall [mm/h]", color='gray')
    # ax.yaxis.set_major_locator(MultipleLocator(500))
    ax.tick_params(bottom=False, left=False)
    ax.tick_params(axis='x', colors='dimgray')
    ax.tick_params(axis='y', colors='gray')
    ax.grid(axis='y')
    ax.spines['left'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['bottom'].set_color('dimgray')
    plt.savefig('plot.png')



def main() -> None:
    url = 'https://map.yahooapis.jp/weather/V1/place'
    params = {
        'appid': YAHOO_APPID,
        'coordinates': f"{TARGET_LONGITUDE},{TARGET_LATITUDE}",
        'output': "json",
        'interval': 5,
    }

    req = request.Request(f'{url}?{parse.urlencode(params)}')
    with request.urlopen(req) as res:
        body = res.read()

    response = json.loads(body)

    weather_list = response["Feature"][0]["Property"]["WeatherList"]["Weather"]
    weather_list = [{'Date': '202111112315', 'Rainfall': 0.0, 'Type': 'observation'},
                    {'Date': '202111112320', 'Rainfall': 1.0, 'Type': 'forecast'},
                    {'Date': '202111112325', 'Rainfall': 3.0, 'Type': 'forecast'},
                    {'Date': '202111112330', 'Rainfall': 5.0, 'Type': 'forecast'},
                    {'Date': '202111112335', 'Rainfall': 10.0, 'Type': 'forecast'},
                    {'Date': '202111112340', 'Rainfall': 20.0, 'Type': 'forecast'},
                    {'Date': '202111112345', 'Rainfall': 10.0, 'Type': 'forecast'},
                    {'Date': '202111112350', 'Rainfall': 3.0, 'Type': 'forecast'},
                    {'Date': '202111112355', 'Rainfall': 2.0, 'Type': 'forecast'},
                    {'Date': '202111120000', 'Rainfall': 1.0, 'Type': 'forecast'},
                    {'Date': '202111120005', 'Rainfall': 0.5, 'Type': 'forecast'},
                    {'Date': '202111120010', 'Rainfall': 0.3, 'Type': 'forecast'},
                    {'Date': '202111120015', 'Rainfall': 0.1, 'Type': 'forecast'}]
    # pprint(weather_list)

    current_time: datetime.datetime
    bgn_rain_fall: float = 0.0
    bgn_rain_time: datetime.datetime
    stg_rain_fall: float = 0.0
    stg_rain_time: datetime.datetime
    end_rain_fall: float = 999.9
    end_rain_time: datetime.datetime

    plot_x: List[int] = []
    plot_y: List[float] = []
    for i, weather in enumerate(weather_list):
        time: datetime.datetime = parser.parse(weather["Date"])
        rain_fall: float = weather["Rainfall"]

        plot_x.append(i * 5)
        plot_y.append(rain_fall)

        if weather["Type"] == "observation":
            current_time = time
        else:
            if rain_fall > 0.0 and bgn_rain_fall <= 0.0:
                bgn_rain_fall = rain_fall
                bgn_rain_time = time

            if rain_fall > stg_rain_fall:
                stg_rain_fall = rain_fall
                stg_rain_time = time

            if (bgn_rain_fall > 0.0) and (end_rain_fall == 999.9) and (rain_fall <= 0.5):
                end_rain_fall = rain_fall
                end_rain_time = time

    if bgn_rain_fall > 0.0:
        _render_img(plot_x, plot_y)

        pre_send_data = {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "<!here>"
                    }
                }
            ]
        }

        pre_req_header = {
            'Content-Type': 'application/json',
        }
        pre_req_data = json.dumps(pre_send_data)
        pre_req = request.Request(
            WORKSPACE_URL, data=pre_req_data.encode(), method='POST', headers=pre_req_header)
        try:
            with request.urlopen(pre_req) as response:
                pass
        except error.URLError as e:
            print(e.reason)

        bgn_strength: str = _get_strength(bgn_rain_fall)
        bgn_delta: datetime.timedelta = bgn_rain_time - current_time
        bgn_delta_min: int = math.floor(bgn_delta.total_seconds() / 60)

        stg_strength: str = _get_strength(stg_rain_fall)
        stg_delta: datetime.timedelta = stg_rain_time - current_time
        stg_delta_min: int = math.floor(stg_delta.total_seconds() / 60)

        end_delta: datetime.timedelta = end_rain_time - current_time
        end_delta_min: int = math.floor(end_delta.total_seconds() / 60)

        body_message: str
        if 0.0 < bgn_delta_min <= 5.0:
            body_message = f"まもなく{bgn_strength}雨が降り始めます。"
        else:
            body_message = f"{bgn_delta_min}分後に{bgn_strength}雨が降り始めます。"

        if (bgn_delta_min > 0.0) and (bgn_delta_min < stg_delta_min):
            body_message += f"\n\n{stg_delta_min}分後には{stg_strength}雨になります。"

        if end_rain_fall < 999.9:
            body_message += f"\n\n{end_delta_min}分後に弱くなります。"

        send_message_head: str = f"🌧雨雲が接近しています🌧\n"
        head_block: Dict[str, Any] = {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": send_message_head,
                "emoji": True
            }
        }

        body_block: Dict[str, Any] = {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"{body_message}"
                },
            ]
        }

        foot_block: Dict[str, Any] = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "<https://weather.yahoo.co.jp/weather/zoomradar/|雨雲レーダーを見る>"
            }
        }

        blocks: List[dict] = []
        blocks.append(head_block)
        blocks.append(body_block)
        blocks.append(foot_block)

        send_data: Dict[str, Any] = {
            "blocks": blocks
        }

        req_header = {
            'Content-Type': 'application/json',
        }
        req_data = json.dumps(send_data)
        req = request.Request(
            WORKSPACE_URL, data=req_data.encode(), method='POST', headers=req_header)
        try:
            with request.urlopen(req) as response:
                pass
        except error.URLError as e:
            print(e.reason)

        client = WebClient(token=BOT_TOKEN)
        file_name = "./plot.png"
        channel_id = "C02LZ68NS9H"
        try:
            result = client.files_upload(
                channels=channel_id,
                title="60分後までの降水量のグラフ",
                file=file_name,
            )

        except SlackApiError as e:
            print("Error uploading file: {}".format(e))

        


if __name__ == "__main__":
    main()
