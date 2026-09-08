from datetime import datetime, timedelta

from opendrift.models.oceandrift import OceanDrift


# Create the OpenDrift model
o = OceanDrift(loglevel=20)

# Artificial ocean current:
# 0.5 m/s toward the east
o.set_config("environment:fallback:x_sea_water_velocity", 0.5)

# No north/south current
o.set_config("environment:fallback:y_sea_water_velocity", 0.0)

# Disable wind for this experiment
o.set_config("environment:fallback:x_wind", 0.0)
o.set_config("environment:fallback:y_wind", 0.0)

# Keep particles in the ocean for this controlled test
o.set_config("environment:fallback:land_binary_mask", 0)

# Starting location
lon = 72.60
lat = 18.20

# Create 10 particles
o.seed_elements(
    lon=lon,
    lat=lat,
    number=10,
    time=datetime(2026, 1, 1, 12, 0, 0),
)

# Simulate for one hour
o.run(
    duration=timedelta(hours=1),
    time_step=timedelta(minutes=10),
)

print("\nSimulation completed.")

print("\nParticle 1 trajectory:")

particle_1_lon = o.result["lon"].isel(trajectory=0)
particle_1_lat = o.result["lat"].isel(trajectory=0)
particle_1_time = o.result["time"]

for t, lon, lat in zip(
    particle_1_time,
    particle_1_lon,
    particle_1_lat,
):
    print(
        f"{t.values} | "
        f"lon={float(lon):.6f}, "
        f"lat={float(lat):.6f}"
    )