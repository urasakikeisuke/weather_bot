"""weather_bot.py"""

import os
import json
import datetime
import random
from dateutil import parser as dateparser
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib import request, error
from pprint import pprint
from itertools import zip_longest

import jpholiday # type: ignore
from slack_sdk import WebClient
from slack_sdk.web.slack_response import SlackResponse
from constants import *


class DatetimeRelated():
    def __init__(self, treat_holiday_as_weekday: bool = False) -> None:
        self.treat_holiday_as_weekday = treat_holiday_as_weekday

    def _is_weekend(self, date: datetime.date) -> bool:
        if date.weekday() > 4:
            return True
        else:
            return False

    def _is_holiday(self, date: datetime.date) -> bool:
        return jpholiday.is_holiday(date)

    def is_weekend(self, date: datetime.date) -> bool:
        if self.treat_holiday_as_weekday:
            return (self._is_weekend(date) or self._is_holiday(date))
        else:
            return self._is_weekend(date)

    def get_datedelta(
        self, 
        date1: datetime.date, 
        date2: datetime.date,
    ) -> int:
        return (date1 - date2).days

    def get_am_pm(self, date: datetime.datetime) -> str:
        return date.strftime("%p")


class ForecastParser():
    def __init__(self) -> None:
        super().__init__()
    
        self.publishing_office: str
        self.report_datetime: datetime.datetime
        self.weathers: List[Tuple[str, str, str]]
        self.pops: List[str]
        self.temps: List[Tuple[str, str]]

    def _zip_contents(self, *contents: list) -> list:
        return list(zip(*contents))
    
    def parse(
        self,
        forecast: Dict[str, Any], 
        area_index: int = 0 # 0: west, 1: east
    ) -> None:
        self.publishing_office = forecast["publishingOffice"]
        self.report_datetime = dateparser.parse(forecast["reportDatetime"])

        _time_series_weather: Dict[str, Any] = forecast["timeSeries"][0]
        _time_series_pop: Dict[str, Any] = forecast["timeSeries"][1]
        _time_series_temp: Dict[str, Any] = forecast["timeSeries"][2]

        _weather_area: Dict[str, Any] = _time_series_weather["areas"][area_index]
        _weather_area_weather_codes: List[str] = _weather_area["weatherCodes"]
        _weather_area_weathers: List[str] = _weather_area["weathers"]
        _weather_time_defines: List[datetime.datetime] = [dateparser.parse(dst) for dst in _time_series_weather["timeDefines"]]

        self.weathers = self._zip_contents(
            _weather_area_weather_codes, _weather_area_weathers, _weather_time_defines)

        _pop_area: Dict[str, Any] = _time_series_pop["areas"][area_index]
        self.pops = _pop_area["pops"]

        _temp_area: Dict[str, Any] = _time_series_temp["areas"][area_index]
        self.temps = _temp_area["temps"]


class MessageGenerator():
    def __init__(
        self,
        publishing_office: str,
        report_datetime: datetime.datetime,
        weathers: List[Tuple[str, str, str]],
        pops: Dict[str, tuple],
        temps: Dict[str, tuple],
        dt_now: datetime.datetime = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))),
        dt_tomorrow: datetime.datetime = datetime.datetime.now() + datetime.timedelta(days=1)
    ) -> None:
        self.publishing_office = publishing_office
        self.report_datetime = report_datetime
        self.weathers = weathers
        self.pops = pops
        self.temps = temps

        self.dt_now = dt_now
        self.dt_tomorrow = dt_tomorrow

    def generate_text(self, type: str) -> str:
        if type == "AM":
            text_header = f"*今日({self.dt_now.month}/{self.dt_now.day})の名古屋の天気* {wc_emoji_map[self.weathers[0][0]]}\n"
            text_body_weather = f"{self.weathers[0][1]}\n"
            text_body_temp = f"*気温* 最低: -℃ 最高: {self.temps['0-highest']}℃\n"
            text_body_pop = f"*降水確率* 午前: {self.pops['0-06-12']}% 午後: {self.pops['0-12-18']}% 夜: {self.pops['0-18-24']}%"
        else:
            text_header = f"*明日({self.dt_tomorrow.month}/{self.dt_tomorrow.day})の名古屋の天気* {wc_emoji_map[self.weathers[1][0]]}\n"
            text_body_weather = f"{self.weathers[1][1]}\n"
            text_body_temp = f"*気温* 最低: {self.temps['1-lowest']}℃ 最高: {self.temps['1-highest']}℃\n"
            text_body_pop = f"*降水確率* 午前: {self.pops['1-06-12']}% 午後: {self.pops['1-12-18']}% 夜: {self.pops['1-18-24']}%"

        return f"{text_header}{text_body_weather}{text_body_temp}{text_body_pop}"

    def generate_blocks(self, type: str) -> List[dict]:
        if type == "AM":
            blocks_header = {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"おはようございます {random.choice(random_emoji_map)} 天気予報です\n",
                    "emoji": True
                }
            }

            blocks_body_0_1 = {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*今日の天気* {wc_emoji_map[self.weathers[0][0]]}\n{self.weathers[0][1]}"
                    },
                ]
            }

            blocks_body_0_2 = {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text":f"降水確率: \n午前: {self.pops['0-06-12']}% 午後: {self.pops['0-12-18']}% 夜: {self.pops['0-18-24']}%"
                    },
                ]
            }

            blocks_body_0_3 = {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text":f"気温: \n最低: -℃ 最高: {self.temps['0-highest']}℃"
                    },
                ]
            }

            blocks_body_1_1 = {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*明日の天気* {wc_emoji_map[self.weathers[1][0]]}\n{self.weathers[1][1]}"
                    },
                ]
            }

        else:
            blocks_header = {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"こんばんは {random.choice(random_emoji_map)} 天気予報です\n",
                    "emoji": True
                }
            }

            blocks_body_0_1 = {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*今夜の天気* {wc_emoji_map[self.weathers[0][0]]}\n{self.weathers[0][1]}"
                    },
                ]
            }

            blocks_body_1_1 = {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*明日の天気* {wc_emoji_map[self.weathers[1][0]]}\n{self.weathers[1][1]}"
                    },
                ]
            }

            blocks_body_1_2 = {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text":f"降水確率: \n午前: {self.pops['1-06-12']}% 午後: {self.pops['1-12-18']}% 夜: {self.pops['1-18-24']}%"
                    },
                ]
            }

            blocks_body_1_3 = {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text":f"気温: \n最低: {self.temps['1-lowest']}℃ 最高: {self.temps['1-highest']}℃"
                    },
                ]
            }

        blocks_divider: Dict[str, str] = {
            "type": "divider"
        }

        blocks_pre_footer: Dict[str, Any] = {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"{self.publishing_office} {self.report_datetime.strftime('%m月%d日 %H時')}発表\n"
                },
            ]
        }

        blocks_footer: Dict[str, Any] = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "<https://tenki.jp/lite/forecast/5/26/5110/23100/1hour.html|詳しい天気を見る>"
            }
        }

        blocks: List[dict]

        if type == "AM":
            blocks = [
                blocks_header,
                blocks_body_0_1, blocks_body_0_2, blocks_body_0_3,
                blocks_divider,
                blocks_body_1_1,
                blocks_divider,
                blocks_pre_footer, blocks_footer,
            ]
        else:
            blocks = [
                blocks_header,
                blocks_body_0_1,
                blocks_divider,
                blocks_body_1_1, blocks_body_1_2, blocks_body_1_3,
                blocks_divider,
                blocks_pre_footer, blocks_footer,
            ]

        return blocks


class WeatherForecast():
    def __init__(self) -> None:
        self.jma_url: str = "https://www.jma.go.jp/bosai/forecast/data/forecast/230000.json"

        self.dt_now: datetime.datetime = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        self.datetime = DatetimeRelated()
        self.forecast_parser = ForecastParser()
        self.slack_client = WebClient(token=self._get_environ("SLACK_BOT_TOKEN"))

        self.pop_keys: List[str] = ["0-00-06", "0-06-12", "0-12-18", "0-18-24", "1-00-06", "1-06-12", "1-12-18", "1-18-24"]
        self.temp_keys: List[str] = ["0-lowest", "0-highest", "1-lowest", "1-highest"]

    def _get_environ(self, key: str) -> str:
        target: Optional[str] = os.getenv(key)

        if target is None:
            raise KeyError(f"Cannot get environ: {key}")

        return target

    def _get_forecast(self) -> Dict[str, Any]:
        req: request.Request = request.Request(self.jma_url)
        with request.urlopen(req) as res:
            forecast: Dict[str, Any] = json.loads(res.read().decode().replace("\u3000", ""))[0]

        return forecast

    def main(self) -> None:
        if self.datetime.is_weekend(self.dt_now.date()):
            print("Skipped forecast because today is hoiday! Yahoo!")
            return
    
        forecast: Dict[str, Any] = self._get_forecast()
        self.forecast_parser.parse(forecast)

        publishing_office = self.forecast_parser.publishing_office
        report_datetime = self.forecast_parser.report_datetime
        weathers = self.forecast_parser.weathers
        pops: Dict[str, tuple] = dict(zip_longest(reversed(self.pop_keys), reversed(self.forecast_parser.pops), fillvalue="-"))
        temps: Dict[str, tuple] = dict(zip_longest(reversed(self.temp_keys), reversed(self.forecast_parser.temps), fillvalue="-"))

        message_generator = MessageGenerator(publishing_office, report_datetime, weathers, pops, temps)

        am_pm: str = self.datetime.get_am_pm(self.dt_now)

        text: str = message_generator.generate_text(type=am_pm)
        blocks: List[dict] = message_generator.generate_blocks(type=am_pm)

        icon_emoji: Optional[str] = None
        if (am_pm == "AM" and "雨" in weathers[0][1]) or (am_pm == "PM" and "雨" in weathers[1][1]):
            icon_emoji = ":umbrella:"

        response: SlackResponse = self.slack_client.chat_postMessage(
            channel="C02LZ68NS9H",
            text=text,
            blocks=blocks,
            icon_emoji=icon_emoji
        )

        pprint(response.status_code)


if __name__ == "__main__":
    app = WeatherForecast()
    app.main()
