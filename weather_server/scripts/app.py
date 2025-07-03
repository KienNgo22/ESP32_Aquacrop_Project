import requests
import os
import sqlite3


from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path
from weather import get_server_root, get_climate_data_path
from db import _get_db_path 

# OpenWeatherMap config
if os.getenv("GITHUB_ACTIONS") != "true":
    server_root = get_server_root()    
    load_dotenv(dotenv_path=server_root / 'env/adafruit.env')

ADAFRUIT_IO_USERNAME = os.getenv("ADAFRUIT_IO_USERNAME")
ADAFRUIT_IO_KEY = os.getenv("ADAFRUIT_IO_KEY")
RAIN_FEED = os.getenv("RAIN_FEED")
TEMP_FEED = os.getenv("TEMP_FEED")
ICON_FEED = os.getenv("ICON_FEED")
AIO_BASE_URL = f"https://io.adafruit.com/api/v2/{ADAFRUIT_IO_USERNAME}/feeds"

def fetch_today_from_db():
    today = datetime.now().date().isoformat()
    db_path = _get_db_path()
    if not db_path.exists():
        return None
    conn = sqlite3.connect(db_path); cur = conn.cursor()
    cur.execute("SELECT tmin, tmax, prcp, eto FROM weather WHERE date = ?", (today,))
    row = cur.fetchone(); conn.close()
    return {'Tmin': row[0], 'Tmax': row[1], 'Prcp': row[2], 'Et0': row[3]} if row else None

def update_today_weather(base_dir=get_climate_data_path()):
    # 1️⃣ Try SQLite first
    if (db_data := fetch_today_from_db()):
        return db_data

    # 2️⃣ Fall back to scanning weather_*.txt
    try:
        files = [f for f in os.listdir(base_dir) if f.startswith('weather_') and f.endswith('.txt')]
        def extract_date(fn): return datetime.strptime(fn[8:-4], '%Y-%m-%d').date()
        files.sort(key=extract_date)

        # Binary search for the file whose 7-day span covers today
        target = datetime.now().date()
        left, right = 0, len(files)-1
        chosen = None
        while left <= right:
            mid = (left+right)//2
            start = extract_date(files[mid])
            end   = start + timedelta(days=6)
            if start <= target <= end:
                chosen = files[mid]; break
            if target < start:
                right = mid-1
            else:
                left = mid+1

        if not chosen:
            print("No flat-file contains today's data"); return None

        with open(os.path.join(base_dir, chosen)) as f:
            for line in f.readlines()[1:]:
                day, month, year, tmin, tmax, prcp, eto = line.split('\t')
                if (int(day), int(month), int(year)) == (target.day, target.month, target.year):
                    return {
                        'Tmin': float(tmin),
                        'Tmax': float(tmax),
                        'Prcp': float(prcp),
                        'Et0':  float(eto)
                    }
        print(f"Today's data not found in {chosen}")
        return None

    except Exception as e:
        print("Error accessing flat-files:", e)
        return None


def send_to_adafruit(feed_key, value):
    url = f"{AIO_BASE_URL}/{feed_key}/data"
    headers = {"X-AIO-Key": ADAFRUIT_IO_KEY, "Content-Type": "application/json"}
    payload = {"value": value}
   
    try:
        r = requests.post(url, json=payload, headers=headers)
        if r.status_code != 200:
            print(f"Failed to send to {feed_key}: {r.text}")
        else:
            print(f"Updated {feed_key}: {value}")
    except Exception as e:
        print(f"Error sending to Adafruit IO: {e}")

def main():
    today_weather = update_today_weather()

    if today_weather:
        send_to_adafruit(RAIN_FEED, today_weather['Prcp'])
        send_to_adafruit(TEMP_FEED, ((today_weather['Tmin'] + today_weather['Tmax']) / 2))
    else:
        print("Failing to fetch today's weather data!")
if __name__ == '__main__':
    main()