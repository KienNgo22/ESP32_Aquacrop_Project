import sqlite3
from pathlib import Path
from datetime import date, timedelta

def get_db_path() -> Path:
    """
    Returns the path to the SQLite database file.
    Changed: Centralized path logic vs. manual folder paths.
    """
    # Was: base_dir = weather_server/climate_data + manual joins
    return Path(__file__).resolve().parent.parent / 'climate_data' / 'weather.db'

def init_db() -> None:
    """
    Initialize the SQLite database and create weather_data table.
    Changed: Ensures directory exists and schema in one place.
    """
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)     # Replaces manual os.makedirs calls
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS weather_data (
            date TEXT PRIMARY KEY,    -- used for upsert and queries
            day INTEGER,
            month INTEGER,
            year INTEGER,
            tmin REAL,
            tmax REAL,
            prcp REAL,
            eto REAL
        )
    ''')
    conn.commit()
    conn.close()

def upsert_entries(entries: list[dict]) -> None:
    """
    INSERT OR REPLACE all incoming entries.
    Changed: Replaces complex .txt append/rollover & duplicate-check logic.
    Each entry dict must have: day, month, year, tmin, tmax, prcp, eto.
    """
    init_db()  # ensure schema
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    for e in entries:
        dt = date(e['year'], e['month'], e['day'])
        date_str = dt.isoformat()
        c.execute('''
            INSERT OR REPLACE INTO weather_data
            (date, day, month, year, tmin, tmax, prcp, eto)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            date_str,
            e['day'], e['month'], e['year'],
            e['tmin'], e['tmax'], e['prcp'], e['eto']
        ))
    conn.commit()
    conn.close()

def get_weather_range(start_date: date, days: int = 5) -> list[tuple]:
    """
    SELECT rows BETWEEN start_date AND start_date+days-1.
    Changed: One SQL BETWEEN instead of binary-search across files.
    Returns list of (day, month, year, tmin, tmax, prcp, eto).
    """
    init_db()
    end_date = start_date + timedelta(days=days - 1)
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute('''
        SELECT day, month, year, tmin, tmax, prcp, eto
          FROM weather_data
         WHERE date BETWEEN ? AND ?
      ORDER BY date ASC
    ''', (start_date.isoformat(), end_date.isoformat()))
    rows = c.fetchall()
    conn.close()
    return rows

def write_temp_txt(rows: list[tuple], temp_path: str) -> None:
    """
    Write out a flat .txt for AquaCrop.
    Changed: Unified temp-file writer vs ad-hoc in simulation.py.
    """
    with open(temp_path, 'w') as f:
        f.write("Day\tMonth\tYear\tTmin(C)\tTmax(C)\tPrcp(mm)\tEt0(mm)\n")
        for r in rows:
            f.write("\t".join(str(x) for x in r) + "\n")

if __name__ == '__main__':
    # Convenience: create DB and print its location
    init_db()
    print(f"Database initialized at: {get_db_path()}")
