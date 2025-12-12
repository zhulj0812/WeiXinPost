# -*- coding: utf-8 -*-
import json
import time
import re
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
    """
    返回：(weather, temp_min, temp_max)
    """
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
        # 兜底：不让程序炸，也能继续发消息（但内容是未知）
        return "未知", "", ""

    weather = weatherinfo.get("weather", "")
    temp_max = weatherinfo.get("temp", "")   # 最高温
    temp_min = weatherinfo.get("tempn", "")  # 最低温
    return weather, temp_min, temp_max


def send_weather_template(openid: str, access_token: str, city: str, weather: str, temp_min: str, temp_max: str):
    """
    这里的 key 名必须和你微信模板里的变量名一致：
    {{city.DATA}} / {{weather.DATA}} / {{min_temperature.DATA}} / {{max_temperature.DATA}}
    """
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}"

    payload = {
        "touser": openid,
        "template_id": config.template_id2,  # 你新建“早安/天气”那个模板ID
        "data": {
            "city": {"value": city},
            "weather": {"value": weather},
            "min_temperature": {"value": temp_min},
            "max_temperature": {"value": temp_max},
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

    print("final weather:", {
        "province": province,
        "city": city,
        "weather": weather,
        "temp_min": temp_min,
        "temp_max": temp_max
    })

    for openid in config.user:
        send_weather_template(openid, access_token, city, weather, temp_min, temp_max)

    print("DONE")
