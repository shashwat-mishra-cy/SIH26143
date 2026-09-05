# Drift Simulation Engine (`drift/simulation`)

## 1. Architecture & OpenDrift Integration Plan
The `drift/simulation` package will integrate the **OpenDrift** framework (specifically Lagrangian particle tracking models such as `OceanDrift` or `OilDrift`) to model the movement and weathering of oil slicks in marine environments.

```text
               +----------------------------------+
               |  Satellite Spill Detection Input |
               +----------------------------------+
                                │
                                ▼
               +----------------------------------+
               | Environmental Forcing Ingestion  |
               | (Winds: u10, v10 | Currents: u,v)|
               +----------------------------------+
                                │
                                ▼
               +----------------------------------+
               |   OpenDrift Hindcast Simulation  |
               |   - Backward Particle Tracking   |
               |   - Stochastic Random Walk       |
               |   - Environmental Forcing Coupling|
               +----------------------------------+
                                │
                                ▼
               +----------------------------------+
               |   Probable Source & Time Window  |
               |         Estimation Engine        |
               +----------------------------------+
                                │
                                ▼
               +----------------------------------+
               | AIS Module Interface Contract    |
               +----------------------------------+
```

## 2. Core Concepts

### 2.1 Forward Drift Simulation
Forward drift models the trajectory of an oil spill forward in time ($t_0 \to t_{end}$). Given a spill detection coordinate and start time, forward simulation predicts future slick advection and dispersion under forecasted wind and current forcing. Used for forward impact assessment and boundary envelope prediction.

### 2.2 Backward / Hindcast Drift Simulation
Backward drift operates in reverse time ($t_{obs} \to t_{obs} - \Delta t$). Starting from the satellite-observed spill polygon and timestamp, particles are tracked backward along inverted velocity vectors to backtrack where and when the release likely originated.

### 2.3 Particle Trajectories
Lagrangian particle tracking represents the oil slick as an ensemble of discrete particles. Each particle's velocity vector $\vec{v}_p$ is modeled as a combination of ocean surface current advection $\vec{u}_{curr}$, wind leeway factor $\gamma \vec{u}_{wind}$ (typically ~2-3% of surface wind velocity), and turbulent diffusion.

### 2.4 Environmental Forcing
Particles dynamically query and interpolate underlying environmental fields (wind $u_{10}, v_{10}$ and current $u_{curr}, v_{curr}$) at each numerical integration time step (e.g., RK4 or Euler integration).

### 2.5 Uncertainty & Stochastic Dispersion
Uncertainty in wind/current forcing and small-scale turbulence is captured by applying stochastic random-walk diffusion perturbations ($\sigma$) to particle trajectories. Simulating particle ensembles ($N \approx 1000 - 10000$) provides a probabilistic distribution rather than a deterministic single path.

### 2.6 Source-Region & Release Window Estimation
Statistical aggregation of backward particle endpoints generates:
1. **Probable Source Region:** A 2D spatial kernel density estimate (KDE) or probability grid polygon highlighting the geographic area of highest origin probability.
2. **Estimated Release Window:** Confidence bounds for the time frame during which the spill entered the ocean environment.
