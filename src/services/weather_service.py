"""
天氣與穿搭建議：使用 Open-Meteo (免費、免 API Key)。
- 預報：氣溫、體感、降雨機率、紫外線
- 空氣品質：US AQI / PM2.5
"""
import os
import time
import requests

DEFAULT_CITY = os.environ.get("WEATHER_DEFAULT_CITY", "台北")
TIMEOUT = 6
CACHE_TTL = 600  # 秒，同一城市 10 分鐘內不重複查詢

# 台灣常用城市 (經緯度)，免去每次地理編碼；查不到時才呼叫地理編碼 API
CITIES = {
    "台北": (25.0330, 121.5654), "新北": (25.0120, 121.4650),
    "基隆": (25.1276, 121.7392), "桃園": (24.9936, 121.3010),
    "新竹": (24.8138, 120.9675), "苗栗": (24.5602, 120.8214),
    "台中": (24.1477, 120.6736), "彰化": (24.0518, 120.5161),
    "南投": (23.9157, 120.6869), "雲林": (23.7092, 120.4313),
    "嘉義": (23.4801, 120.4491), "台南": (22.9999, 120.2270),
    "高雄": (22.6273, 120.3014), "屏東": (22.5519, 120.5488),
    "宜蘭": (24.7021, 121.7378), "花蓮": (23.9871, 121.6015),
    "台東": (22.7583, 121.1444), "澎湖": (23.5711, 119.5793),
    "金門": (24.4493, 118.3767), "馬祖": (26.1608, 119.9517),
}

_cache = {}


def _norm_city(name):
    name = (name or "").strip().replace("臺", "台")
    for suffix in ("市", "縣"):
        if name.endswith(suffix) and len(name) > 2:
            name = name[:-1]
    return name or DEFAULT_CITY


def _locate(city):
    """回傳 (顯示名稱, lat, lon)；找不到回傳 None"""
    if city in CITIES:
        lat, lon = CITIES[city]
        return city, lat, lon
    r = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1, "language": "zh"}, timeout=TIMEOUT)
    r.raise_for_status()
    results = r.json().get("results") or []
    if not results:
        return None
    g = results[0]
    return g.get("name", city), g["latitude"], g["longitude"]


def fetch_weather(city=None):
    """取得原始天氣資料 dict；城市不存在回傳 None。網路錯誤會拋出例外。"""
    city = _norm_city(city)
    hit = _cache.get(city)
    if hit and time.time() - hit[0] < CACHE_TTL:
        return hit[1]

    loc = _locate(city)
    if not loc:
        return None
    name, lat, lon = loc

    f = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat, "longitude": lon, "timezone": "Asia/Taipei", "forecast_days": 1,
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m",
            "daily": "temperature_2m_max,temperature_2m_min,apparent_temperature_max,"
                     "precipitation_probability_max,uv_index_max",
        }, timeout=TIMEOUT)
    f.raise_for_status()
    fj = f.json()

    aqi = pm25 = None
    try:  # 空氣品質失敗不影響其他資訊
        a = requests.get(
            "https://air-quality-api.open-meteo.com/v1/air-quality",
            params={"latitude": lat, "longitude": lon, "timezone": "Asia/Taipei",
                    "current": "us_aqi,pm2_5"}, timeout=TIMEOUT)
        a.raise_for_status()
        cur = a.json().get("current", {})
        aqi, pm25 = cur.get("us_aqi"), cur.get("pm2_5")
    except Exception as e:
        print(f"⚠️ 空氣品質查詢失敗: {e}")

    cur, day = fj["current"], fj["daily"]
    data = {
        "city": name,
        "temp": cur["temperature_2m"],
        "feels": cur["apparent_temperature"],
        "humidity": cur.get("relative_humidity_2m"),
        "t_max": day["temperature_2m_max"][0],
        "t_min": day["temperature_2m_min"][0],
        "feels_max": day["apparent_temperature_max"][0],
        "rain_prob": day["precipitation_probability_max"][0] or 0,
        "uv": day["uv_index_max"][0] or 0,
        "aqi": aqi,
        "pm25": pm25,
    }
    _cache[city] = (time.time(), data)
    return data


def build_advice(d):
    """依天氣資料產生穿搭與出門建議 (純函式，方便測試)。回傳 list[str]"""
    tips = []
    feels = d["feels"]
    spread = d["t_max"] - d["t_min"]

    # --- 穿著 (以體感溫度為準) ---
    if feels <= 12:
        tips.append("🥶 今天很冷，建議穿保暖一點：厚外套或羽絨衣、毛衣、長褲，可加圍巾")
    elif feels <= 17:
        tips.append("🧥 今天偏冷，建議穿保暖衣物：長袖加厚外套、長褲")
    elif feels <= 22:
        tips.append("🧥 天氣微涼，建議裡面穿短袖或薄長袖，外面加件外套，下身穿長褲")
    elif feels <= 27:
        tips.append("👕 氣溫舒適，穿短袖搭長褲或薄長袖即可")
    elif feels <= 31:
        tips.append("☀️ 天氣偏熱，建議穿透氣的短袖、短褲或薄長褲")
    else:
        tips.append("🔥 今日天氣炎熱，穿輕薄透氣的衣物，多補充水分")

    if spread >= 8 and feels > 12 and d["t_min"] <= 22:
        tips.append(f"🌗 早晚溫差大 ({d['t_min']:.0f}~{d['t_max']:.0f}°C)，隨身帶一件薄外套")

    # --- 防曬 / 降雨 ---
    hot_sun = d["uv"] >= 6 or d["feels_max"] >= 32
    if hot_sun:
        tips.append("☂️ 紫外線強，出門記得帶傘遮擋陽光，並擦防曬")
    elif d["uv"] >= 3:
        tips.append("🧴 紫外線中等，白天外出建議擦防曬")

    if d["rain_prob"] >= 50:
        tips.append(f"🌧 降雨機率 {d['rain_prob']:.0f}%，出門記得帶雨傘")
    elif d["rain_prob"] >= 30:
        tips.append(f"🌦 降雨機率 {d['rain_prob']:.0f}%，建議備一把折疊傘")

    # --- 空氣品質 (US AQI) ---
    aqi = d.get("aqi")
    if aqi is not None:
        if aqi > 150:
            tips.append(f"😷 空氣品質不良 (AQI {aqi:.0f})，出門請配戴口罩，減少戶外活動")
        elif aqi > 100:
            tips.append(f"😷 空氣品質偏差 (AQI {aqi:.0f})，出門記得配戴口罩，敏感族群尤其注意")

    return tips


def format_weather_message(d):
    lines = [
        f"📍 {d['city']} 今日天氣",
        f"🌡 目前 {d['temp']:.0f}°C，體感 {d['feels']:.0f}°C",
        f"📈 今日 {d['t_min']:.0f}~{d['t_max']:.0f}°C｜降雨機率 {d['rain_prob']:.0f}%",
    ]
    if d.get("humidity") is not None:
        lines.append(f"💧 濕度 {d['humidity']:.0f}%｜紫外線指數 {d['uv']:.0f}")
    if d.get("aqi") is not None:
        lines.append(f"🌫 空氣品質 AQI {d['aqi']:.0f}")
    lines.append("")
    lines.append("👔 穿搭建議")
    lines.extend(build_advice(d))
    return "\n".join(lines)


def get_weather_reply(city=None):
    """對外入口：回傳要傳給使用者的文字。"""
    try:
        d = fetch_weather(city)
    except Exception as e:
        print(f"⚠️ 天氣查詢失敗: {e}")
        return "天氣服務暫時連不上，請稍後再試 🙏"
    if d is None:
        return f"找不到「{city}」這個地點，請換個城市名稱試試（例如：天氣 高雄）"
    return format_weather_message(d)
