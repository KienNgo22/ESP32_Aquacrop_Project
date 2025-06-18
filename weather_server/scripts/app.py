import requests
import os

from datetime import date
from dotenv import load_dotenv
from pathlib import Path

# import our DB helpers
from db import init_db, get_weather_range

# OpenWeather/AIO config
if os.getenv("GITHUB_ACTIONS") != "true":
    # load Adafruit credentials
    root = Path(__file__).resolve().parent
    load_dotenv(dotenv_path=root / 'env' / 'adafruit.env')

ADAFRUIT_IO_USERNAME = os.getenv("ADAFRUIT_IO_USERNAME")
ADAFRUIT_IO_KEY      = os.getenv("ADAFRUIT_IO_KEY")
RAIN_FEED            = os.getenv("RAIN_FEED")
TEMP_FEED            = os.getenv("TEMP_FEED")
AIO_BASE_URL         = f"https://io.adafruit.com/api/v2/{ADAFRUIT_IO_USERNAME}/feeds"


def send_to_adafruit(feed_key: str, value: float):
    url = f"{AIO_BASE_URL}/{feed_key}/data"
    headers = {"X-AIO-Key": ADAFRUIT_IO_KEY, "Content-Type": "application/json"}
    payload = {"value": value}

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        r.raise_for_status()
        print(f"Updated {feed_key}: {value}")
    except Exception as e:
        print(f"Error sending to {feed_key}: {e}")


def main():
    # Ensure DB/table exists
    init_db()

    today = date.today()
    # grab exactly one row (today)
    rows = get_weather_range(today, days=1)
    if not rows:
        print("No weather data for today in database.")
        return

    day, month, year, tmin, tmax, prcp, eto = rows[0]

    # send precipitation
    send_to_adafruit(RAIN_FEED, prcp)
    # send average temperature
    avg_temp = (tmin + tmax) / 2
    send_to_adafruit(TEMP_FEED, avg_temp)


if __name__ == '__main__':
    main()
