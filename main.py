# -*- coding: utf-8 -*-
import json
import time
import re
import cityinfo
import config
from requests import get


def _extract_json_object(text: str) -> dict:
    """
    从 weather.com.cn 返回内容里尽量提取出 JSON 对象：
    - 可能是 "var data= {...};"
    - 可能是 "var dataSK= {...};"
    - 也可能是直接 "{...}"
    - 也可能是 HTML/空/反爬内容
    """
    if not text:
        return {}

    # 1) 优先截取第一段（你原来就是这么做的）
    first = text.split(";", 1)[0].strip()

    # 2) 去掉 "var xxx=" 前缀（如果有）
    if "=" in first:
        first = first.split("=", 1)[1].strip()

    # 3) 如果不是以 { 开头，尝试在全文里找第一个 {...}
    if not first.startswith("{"):
        m = re.search(r"\{.*\}", text, flags=re.S)
        if m:
            first = m.group(0).strip()
        else:
            return {}

    # 4) 尝试 json 解析
    try:
        return json.loads(first)
    except Exception:
        return {}


def get_weather(province: str, city: str):
    """
    返回：(weather, temp_max, temp_min)
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

    # ✅ 调试：如果你还遇到 KeyError/空数据，就看这里打印的内容
    print("weather raw resp head:", resp.text[:200])

    data = _extract_json_object(resp.text)

    # ✅ 兼容：有时接口不叫 weatherinfo，或者直接返回空对象
    weatherinfo = data.get("weatherinfo") or data.get("data") or {}

    # 如果还是拿不到，直接兜底，不让程序炸
    if not weatherinfo:
        return "未知", "", ""

    weather = weatherinfo.get("weather", "")
    temp_max = weatherinfo.get("temp", "")   # 接口字段 temp
    temp_min = weatherinfo.get("tempn", "")  # 接口字段 tempn

    return weather, temp_max, temp_min


if __name__ == "__main__":
    province, city = config.province, config.city
    weather, temp_max, temp_min = get_weather(province, city)

    result = {
        "province": province,
        "city": city,
        "weather": weather,
        "temp_max": temp_max,
        "temp_min": temp_min
    }

    print(json.dumps(result, ensure_ascii=False))
