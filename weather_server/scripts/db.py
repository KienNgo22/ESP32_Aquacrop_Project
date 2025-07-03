# db.py
from pathlib import Path
import sqlite3

# --- DB Helper Functions Inserted Here ---  <-- ADDED BLOCK START
# Returns the path to the SQLite database file

def _get_db_path():
    return Path(__file__).resolve().parent.parent / "climate_data" / "weather.db"

# Initializes the database and creates the weather table if it doesn't exist

def _init_db():
    db_file = _get_db_path()
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_file)
    conn.execute("""
      CREATE TABLE IF NOT EXISTS weather (
        date TEXT PRIMARY KEY,
        day INTEGER,
        month INTEGER,
        year INTEGER,
        tmin REAL,
        tmax REAL,
        prcp REAL,
        eto REAL
      )
    """)
    conn.commit()
    conn.close()

# Inserts or replaces a single day's weather data into the database

def _upsert_day(date_str, day, month, year, tmin, tmax, prcp, eto):
    conn = sqlite3.connect(_get_db_path())
    cur = conn.cursor()
    cur.execute("""
      INSERT OR REPLACE INTO weather
      (date, day, month, year, tmin, tmax, prcp, eto)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (date_str, day, month, year, tmin, tmax, prcp, eto))
    conn.commit()
    conn.close()
# --- DB Helper Functions Inserted Here ---  <-- ADDED BLOCK END