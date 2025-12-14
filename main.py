# -*- coding: utf-8 -*-
import json
import time
import re
import random
from datetime import datetime, date

import cityinfo
import config
from requests import get, post


def _extract_json_object(text: str) -> dict:
    if not text:
        return {}

    first = text.split(";", 1)[0].strip()
    if "=" in first:
        first = first.split("=", 1)[1].strip()

    if not first.startswith("{"):
        m = re.search(r"\{.*\}", text, flags=re.S)
        if m:
            first = m.group(0).strip()
        else:
            return {}

    try:
        return json.loads(first)
    except Exception:
        return {}


def get_access_token() -> str:
    url = (
        "https://api.weixin.qq.com/cgi-bin/token"
        "?grant_type=client_credential"
        f"&appid={config.app_id}"
        f"&secret={config.app_secret}"
    )
    r = get(url, timeout=10)
    print("token raw resp:", r.text)
    j = r.json()
    if "access_token" not in j:
        raise RuntimeError(f"get_access_token failed: {j}")
    return j["access_token"]


def get_weather(province: str, city: str):
    """返回：(weather, temp_min, temp_max)"""
    city_id = cityinfo.cityInfo[province][city]["AREAID"]
    t = int(round(time.time() * 1000))

    headers = {
        "Referer": f"http://www.weather.com.cn/weather1d/{city_id}.shtml",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/103.0.0.0 Safari/537.36"
        )
    }

    url = f"http://d1.weather.com.cn/dingzhi/{city_id}.html?_={t}"
    resp = get(url, headers=headers, timeout=10)
    resp.encoding = "utf-8"

    print("weather raw resp head:", resp.text[:200])

    data = _extract_json_object(resp.text)
    weatherinfo = data.get("weatherinfo") or data.get("data") or {}

    if not weatherinfo:
        return "未知", "", ""

    weather = weatherinfo.get("weather", "")
    temp_max = weatherinfo.get("temp", "")
    temp_min = weatherinfo.get("tempn", "")
    return weather, temp_min, temp_max


def get_love_day(love_date_str: str) -> int:
    """计算在一起第 N 天（从 love_date 到今天，含当天算第 1 天）"""
    y, m, d = map(int, love_date_str.split("-"))
    start = date(y, m, d)
    today = date.today()
    delta = (today - start).days
    # 含当天：同一天返回 1
    return delta + 1


def pick_morning_quote() -> str:
    quotes = getattr(config, "morning_quotes", [])
    if not quotes:
        return "早安！愿你今天一切顺利～"
    return random.choice(quotes)


def send_weather_template(openid: str, access_token: str, city: str,
                          weather: str, temp_min: str, temp_max: str,
                          morning: str, love_day: int):
    """
    模板字段必须对应：
    {{city.DATA}} / {{weather.DATA}} / {{min_temperature.DATA}} / {{max_temperature.DATA}}
    {{morning.DATA}} / {{love_day.DATA}}
    """
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}"

    payload = {
        "touser": openid,
        "template_id": config.template_id1,
        "data": {
            "city": {"value": city},
            "weather": {"value": weather},
            "min_temperature": {"value": temp_min},
            "max_temperature": {"value": temp_max},
            "morning": {"value": morning},
            "love_day": {"value": str(love_day)},
        }
    }

    r = post(url, json=payload, timeout=10)
    print(f"send to {openid} raw resp:", r.text)

    j = r.json()
    if j.get("errcode", -1) != 0:
        raise RuntimeError(f"send failed for {openid}: {j}")
    return j


if __name__ == "__main__":
    province, city = config.province, config.city

    access_token = get_access_token()
    weather, temp_min, temp_max = get_weather(province, city)

    morning = pick_morning_quote()
    love_day = get_love_day(config.love_date)

    print("final payload fields:", {
        "city": city,
        "weather": weather,
        "temp_min": temp_min,
        "temp_max": temp_max,
        "morning": morning,
        "love_day": love_day
    })

    for openid in config.user:
        send_weather_template(
            openid, access_token, city,
            weather, temp_min, temp_max,
            morning, love_day
        )

    print("DONE")
