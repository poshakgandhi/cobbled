import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import astropy.units as u
from astropy.time import Time
from thejoker import TheJoker, JokerPrior, RVData

# -----------------------------------------------------------------------------
# 1. Read Radial Velocity Data from CSV
# -----------------------------------------------------------------------------
# Automatically resolve path to CSV file relative to this script
script_dir = os.path.dirname(os.path.abspath(__file__))
csv_file = os.path.join(script_dir, "app", "fixtures", "gaia_bh1_rvs.csv")

print(f"Reading RV data from: {csv_file}")
df = pd.read_csv(csv_file)

# Convert columns to Astropy quantities
t = Time(df["HJD"].values, format="jd")
rv = df["RV"].values * (u.km / u.s)
rv_err = df["RV Error"].values * (u.km / u.s)

# Create TheJoker RVData object
data = RVData(t=t, rv=rv, rv_err=rv_err)

# -----------------------------------------------------------------------------
# 2. Define Prior with Intrinsic Scatter (s) and Run TheJoker Fit
# -----------------------------------------------------------------------------
# Define intrinsic scatter s (stellar jitter / extra variance added in quadrature)
# Following Thompson et al. (2019) / TheJoker documentation example
s_scatter = 0.5 * (u.km / u.s)

# Define prior including intrinsic scatter s
prior = JokerPrior.default(
    P_min=100.0 * u.day,
    P_max=300.0 * u.day,
    sigma_K0=50.0 * (u.km / u.s),
    sigma_v=100.0 * (u.km / u.s),
    s=s_scatter,  # Intrinsic scatter / stellar jitter term
)

# Initialize sampler with deterministic seed for 100% reproducible results
rng = np.random.default_rng(42)
joker = TheJoker(prior, rng=rng)

# Draw prior samples and run rejection sampling
prior_samples = prior.sample(size=250_000)
samples = joker.rejection_sample(data, prior_samples=prior_samples)

print(f"Sampling complete. Number of surviving Keplerian orbits: {len(samples)}")
if len(samples) > 0:
    best_p = samples["P"][0]
    best_k = samples["K"][0]
    best_e = samples["e"][0]
    print(f"Best-fit Period (P)      : {best_p:.4f}")
    print(f"Best-fit Semi-Amp(K)     : {best_k:.2f}")
    print(f"Best-fit Ecc.    (e)     : {best_e:.4f}")
    print(f"Intrinsic Scatter (s)    : {s_scatter:.2f}")

# -----------------------------------------------------------------------------
# 3. Plot Time-Series Radial Velocity Curve
# -----------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(9, 5), dpi=150)

# Generate dense time grid for smooth orbit curves
t_grid = np.linspace(t.min().value - 10, t.max().value + 10, 1000)
t_grid_time = Time(t_grid, format="jd")

# Plot sample orbit predictions
plot_samples = samples[:50] if len(samples) > 50 else samples
for i in range(len(plot_samples)):
    orbit = plot_samples.get_orbit(i)
    model_rv = orbit.radial_velocity(t_grid_time)
    ax.plot(t_grid_time.value, model_rv.to(u.km / u.s).value, color="cyan", alpha=0.3, lw=1)

# Calculate effective total error including intrinsic scatter: sigma_eff = sqrt(sigma_obs^2 + s^2)
eff_err = np.sqrt(rv_err.value**2 + s_scatter.value**2)

# Overplot RV observations with effective errorbars
ax.errorbar(
    t.value,
    rv.value,
    yerr=eff_err,
    fmt="o",
    color="darkblue",
    ecolor="red",
    capsize=3,
    markersize=5,
    label=f"Observed RVs (σ_eff with s={s_scatter.value:.1f} km/s)",
)

ax.set_xlabel("Time [HJD]", fontsize=11, fontweight="bold")
ax.set_ylabel("Radial Velocity [km / s]", fontsize=11, fontweight="bold")
ax.set_title("Gaia-BH1 Orbit Fit with Intrinsic Scatter s (TheJoker)", fontsize=13, fontweight="bold")
ax.grid(True, linestyle="--", alpha=0.6)
ax.legend(loc="best")

plt.tight_layout()
plot_output = os.path.join(script_dir, "gaia_bh1_fit.png")
fig.savefig(plot_output)
plt.show()
print(f"Plot saved to {plot_output}")
