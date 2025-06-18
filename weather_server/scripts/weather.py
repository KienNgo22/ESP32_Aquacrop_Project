# weather.py
import requests
import os
import math

from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from db import upsert_entries  # Changed: switch from txt-files to DB

# Load OpenWeatherMap credentials
if os.getenv("GITHUB_ACTIONS") != "true":
    load_dotenv(dotenv_path=Path(__file__).resolve().parent / 'env' / 'OpenWeather.env')

API_KEY      = os.getenv("API_KEY")
CITY         = os.getenv("CITY")
COUNTRY_CODE = os.getenv("COUNTRY_CODE")
API_URL      = (
    f"http://api.openweathermap.org/data/2.5/forecast"
    f"?q={CITY},{COUNTRY_CODE}&appid={API_KEY}&units=metric"
)

def calculate_eto_hargreaves(tmax, tmin, tmean, ra):
    # Unchanged formula
    if tmax <= tmin:
        return 0.0
    return max(0,
        0.0023 * (tmean + 17.8) * math.sqrt(tmax - tmin) * ra
    )

def get_extraterrestrial_radiation(lat, doy):
    # Unchanged calculation
    lat_rad     = math.radians(lat)
    declination = 0.409 * math.sin(2*math.pi*doy/365 - 1.39)
    ws          = math.acos(-math.tan(lat_rad) * math.tan(declination))
    dr          = 1 + 0.033 * math.cos(2*math.pi*doy/365)
    ra = (24*60/math.pi) * 0.082 * dr * (
        ws*math.sin(lat_rad)*math.sin(declination) +
        math.cos(lat_rad)*math.cos(declination)*math.sin(ws)
    )
    return ra

def fetch_and_store():
    """
    Fetch 5-7 day forecast, compute stats & ETo,
    then upsert into SQLite database.
    Changed: Replaces write_forecast_data() entirely.
    """
    try:
        resp = requests.get(API_URL, timeout=10)
        data = resp.json()
        lat  = data["city"]["coord"]["lat"]

        daily = {}
        for e in data["list"]:
            dt = datetime.fromtimestamp(e["dt"])
            d  = dt.strftime("%Y-%m-%d")
            rec = daily.setdefault(d, {"temps": [], "precip": 0.0, "doy": dt.timetuple().tm_yday})
            rec["temps"].append(e["main"]["temp"])
            rec["precip"] += e.get("rain", {}).get("3h",0) + e.get("snow", {}).get("3h",0)

        entries = []
        for d, rec in daily.items():
            if len(rec["temps"]) < 3:
                continue
            tmax  = max(rec["temps"])
            tmin  = min(rec["temps"])
            tmean = sum(rec["temps"]) / len(rec["temps"])
            eto   = calculate_eto_hargreaves(tmax, tmin, tmean, get_extraterrestrial_radiation(lat, rec["doy"]))
            yr, mo, da = map(int, d.split('-'))
            entries.append({
                "day": da, "month": mo, "year": yr,
                "tmin": round(tmin,2), "tmax": round(tmax,2),
                "prcp": round(rec["precip"],2), "eto": round(eto,2)
            })

        if entries:
            upsert_entries(entries)
            print(f"Upserted {len(entries)} forecast rows into DB.")
        else:
            print("No valid forecast data to upsert.")

    except Exception as e:
        print("Error fetching/storing forecast:", e)

if __name__ == "__main__":
    print("Fetching & storing forecast …")
    fetch_and_store()
