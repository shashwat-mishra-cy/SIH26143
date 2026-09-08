from datetime import datetime, timedelta

from opendrift.models.oceandrift import OceanDrift
from opendrift.readers import reader_netCDF_CF_generic


# Load ERA5 wind data
reader = reader_netCDF_CF_generic.Reader(
    "drift/data/era5_test.nc"
)

# Create OpenDrift model
o = OceanDrift(loglevel=20)

# Tell OpenDrift to use the ERA5 reader
o.add_reader(reader)

# Seed particles inside our ERA5 coverage
o.seed_elements(
    lon=72.5,
    lat=18.0,
    number=10,
    time=datetime(2025, 1, 1, 12, 0, 0),
)

# Run for 1 hour
o.run(
    duration=timedelta(hours=1),
    time_step=timedelta(minutes=10),
)

# Print trajectory of particle 1
particle_1_lon = o.result["lon"].isel(trajectory=0)
particle_1_lat = o.result["lat"].isel(trajectory=0)
particle_1_time = o.result["time"]

print("\nParticle 1 trajectory:")

for t, lon, lat in zip(
    particle_1_time,
    particle_1_lon,
    particle_1_lat,
):
    print(
        f"{t} | "
        f"lon={float(lon):.6f}, "
        f"lat={float(lat):.6f}"
    )