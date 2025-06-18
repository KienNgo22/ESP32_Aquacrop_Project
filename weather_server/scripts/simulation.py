# simulation.py
from datetime import date
from pathlib import Path

from aquacrop import AquaCropModel, Soil, Crop, InitialWaterContent
from aquacrop.utils import prepare_weather

from db import init_db, get_weather_range, write_temp_txt  # Changed: DB + temp writer

def run_simulation(days_ahead: int = 5):
    init_db()  # Changed: ensure DB/table

    today = date.today()
    rows = get_weather_range(today, days=days_ahead)  # Changed: replaced file parsing
    if len(rows) < days_ahead:
        print(f"Warning: only found {len(rows)}/{days_ahead} days in DB")

    # Write a uniform temp file
    climate_dir = Path(__file__).resolve().parent.parent / 'climate_data'
    temp_file = climate_dir / 'temp_aquacrop_weather.txt'
    write_temp_txt(rows, str(temp_file))

    # Load into DataFrame and delete
    weather_df = prepare_weather(str(temp_file))
    temp_file.unlink(missing_ok=True)

    # Set up and run AquaCrop (unchanged)
    sandy_loam = Soil(soil_type='SandyLoam')
    init_wc = InitialWaterContent(value=['FC'])
    start = weather_df["Date"].iloc[0].strftime("%Y/%m/%d")
    end   = weather_df["Date"].iloc[-1].strftime("%Y/%m/%d")
    planting = weather_df["Date"].iloc[0].strftime("%m/%d")
    crop = Crop('Maize', planting_date=planting)
    print(f"Running AquaCrop from {start} to {end}")

    model = AquaCropModel(
        sim_start_time=start,
        sim_end_time=end,
        weather_df=weather_df,
        soil=sandy_loam,
        crop=crop,
        initial_water_content=init_wc
    )
    model.run_model(till_termination=True)

    # Print last flux rows
    flux = model._outputs.water_flux
    recent = flux[flux["dap"] != 0].tail(10)
    print("AquaCrop output:\n", recent)

if __name__ == '__main__':
    run_simulation()
