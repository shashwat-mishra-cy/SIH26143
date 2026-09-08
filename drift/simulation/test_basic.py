from datetime import datetime, timedelta

from opendrift.models.oceandrift import OceanDrift


# Create the OpenDrift model
o = OceanDrift(loglevel=20)

# Imaginary starting location
# Longitude, Latitude
lon = 72.60
lat = 18.20

# Start with 10 particles
o.seed_elements(
    lon=lon,
    lat=lat,
    number=10,
    time=datetime(2026, 1, 1, 12, 0, 0),
)

# Run the simulation for 1 hour
o.run(
    duration=timedelta(hours=1),
    time_step=timedelta(minutes=10),
)

print("Simulation completed successfully.")
print(f"Number of particles: {len(o.elements.lon)}")

print("\nFinal particle positions:")

for i in range(len(o.elements.lon)):
    print(
        f"Particle {i + 1}: "
        f"lon={o.elements.lon[i]:.6f}, "
        f"lat={o.elements.lat[i]:.6f}"
    )

print("\nSimulation result:")
print(o.result)

print("\nParticle 1 trajectory:")

particle_1_lon = o.result["lon"].isel(trajectory=0)
particle_1_lat = o.result["lat"].isel(trajectory=0)
particle_1_time = o.result["time"]

for t, lon, lat in zip(particle_1_time, particle_1_lon, particle_1_lat):
    print(
        f"{t}: "
        f"lon={float(lon):.6f}, "
        f"lat={float(lat):.6f}"
    )