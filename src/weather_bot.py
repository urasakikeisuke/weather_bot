"""weather_bot.py"""

import os
import json
import datetime
from dateutil import parser
from typing import Any, Dict, Final, List, Optional
from urllib import request, error
from pprint import pprint

from constants import *

dt_now: datetime.datetime = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))

JMA_URL: Final = "https://www.jma.go.jp/bosai/forecast/data/forecast/230000.json"
WORKSPACE_URL: Final = os.getenv("SLACK_WORKSPACE_URL")
if WORKSPACE_URL is None:
    raise KeyError


def _is_today(weekid: int) -> bool:
    if weekid <= 4:
        if dt_now.weekday() == weekid:
            return True
    
    return False


def _is_tmr(weekid: int) -> bool:
    if weekid <= 4:
        if dt_now.weekday() == weekid - 1:
            return True

    return False


def main() -> None:
    req: request.Request = request.Request(JMA_URL)
    with request.urlopen(req) as res:
        weather = json.loads(res.read().decode().replace("\u3000", ""))[0]

    publishing_office: datetime.datetime = weather["publishingOffice"]
    report_datetime: datetime.datetime = parser.parse(weather["reportDatetime"])

    time_series = weather["timeSeries"]


    main_forecast = time_series[0]
    main_west_area_forecast = main_forecast["areas"][0]

    main_weathers: List[str] = main_west_area_forecast["weathers"]
    main_weather_codes: List[str] = main_west_area_forecast["weatherCodes"]
    main_time_defines: List[str] = main_forecast["timeDefines"]

    main_forecasts: Dict[datetime.datetime, Dict[str, Any]] = {}
    for main_weather, main_weather_code, main_time_define in zip(main_weathers, main_weather_codes, main_time_defines):
        main_forecasts[parser.parse(main_time_define)] = {
            "weather": main_weather,
            "weather_code": main_weather_code,
        }


    pop_forecast = time_series[1]
    pop_west_area_forecast = pop_forecast["areas"][0]

    pop_pops: List[str] = pop_west_area_forecast["pops"]
    pop_time_defines: List[str] = pop_forecast["timeDefines"]


    pop_forecasts: Dict[datetime.datetime, Dict[str, Any]] = {}
    for pop_pop, pop_time_define in zip(pop_pops, pop_time_defines):
        pop_forecasts[parser.parse(pop_time_define)] = {
            "pop": pop_pop,
        }


    temp_forecast = time_series[2]
    temp_west_area_forecast = temp_forecast["areas"][0]

    temp_temps: List[str] = temp_west_area_forecast["temps"]
    temp_time_defines: List[str] = temp_forecast["timeDefines"]

    temp_forecasts: Dict[datetime.datetime, Dict[str, Any]] = {}
    for temp_temp, temp_time_define in zip(temp_temps, temp_time_defines):
        temp_forecasts[parser.parse(temp_time_define)] = {
            "temp": temp_temp,
        }


    send_message_head: str = f"Hola! 👻 {dt_now.month}月{dt_now.day}日({dow_map[dt_now.weekday()]})の名古屋の天気予報です\n"
    send_message_sub_head: str = f"{publishing_office} {report_datetime.hour}時発表\n"
    send_message_today_emoji: str = "今日の天気: "
    send_message_today_text: Optional[str] = None
    send_message_tmr_emoji: str = "明日の天気: "
    send_message_tmr_text: Optional[str] = None

    for time_define, values in main_forecasts.items():
        if _is_today(time_define.weekday()):
            _emoji: str = wc_emoji_map[values["weather_code"]]
            send_message_today_emoji += _emoji
            send_message_today_text = values["weather"]
        
        if _is_tmr(time_define.weekday()):
            _emoji = wc_emoji_map[values["weather_code"]]
            send_message_tmr_emoji += _emoji
            send_message_tmr_text = values["weather"]

    head_block: Dict[str, Any] = {
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": send_message_head,
            "emoji": True
        }
    }

    sub_head_block: Dict[str, Any] = {
        "type": "section",
        "fields": [
            {
                "type": "mrkdwn",
                "text": f"{send_message_sub_head}"
            },
        ]
    }

    today_weather_block: Dict[str, Any] = {
        "type": "section",
        "fields": [
            {
                "type": "mrkdwn",
                "text": f"*{send_message_today_emoji}*\n{send_message_today_text}"
            },
        ]
    }

    tmr_weather_block: Dict[str, Any] = {
        "type": "section",
        "fields": [
            {
                "type": "mrkdwn",
                "text": f"*{send_message_tmr_emoji}*\n{send_message_tmr_text}"
            },
        ]
    }

    foot_block: Dict[str, Any] = {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "<https://www.jma.go.jp/bosai/forecast/#area_type=class20s&area_code=2310000|詳しい天気を見る>"
        }
    }

    blocks: List[dict] = []
    blocks.append(head_block)
    blocks.append(sub_head_block)

    if send_message_today_text is not None:
        blocks.append(today_weather_block)

    if send_message_tmr_text is not None:
        blocks.append(tmr_weather_block)

    blocks.append(foot_block)

    send_data: Dict[str, Any] = {
        "blocks": blocks
    }

    req_header = {
        'Content-Type': 'application/json',
    }
    req_data = json.dumps(send_data)
    req = request.Request(WORKSPACE_URL, data=req_data.encode(), method='POST', headers=req_header)
    try:
        with request.urlopen(req) as response:
            print(response.getcode())
    except error.URLError as e:
        print(e.reason)


if __name__ == "__main__":
    main()
