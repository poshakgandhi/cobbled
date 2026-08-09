---
title: Cobbled
emoji: 🌌
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# COBBLED 2.0 - Compact Object Binary Live Experiments Database

**COBBLED 2.0** is an advanced astrophysical data platform designed for managing, analyzing, and modeling spectroscopic radial velocity (RV) observations for compact binary systems and stellar-mass black hole candidates (e.g., Gaia-BH1, Gaia-BH3).

---

## 🌟 Key Features in COBBLED 2.0

1. **TheJoker Keplerian Fitting Engine with Intrinsic Scatter ($s$)**:
   - Integrated **TheJoker** Monte Carlo rejection sampler with customizable prior initial guesses ($P, K, v_0, e$).
   - Full support for **Intrinsic Scatter / Stellar Jitter ($s$)** added in quadrature to observational errors ($\sigma_{\text{eff}} = \sqrt{\sigma_{\text{obs}}^2 + s^2}$).
   - Deterministic, 100% reproducible sampling using fixed-seed random number generation.

2. **On-Demand Fine Grid Periodogram & $\Delta \chi^2$ Scan**:
   - Evaluates marginal log-likelihoods ($\ln \mathcal{L}$) across prior grid samples binned into 300 fine period steps.
   - Computes continuous $\Delta \chi^2(P)$ likelihood profiles with $1\sigma$ ($\Delta\chi^2=1.0$) and $3\sigma$ ($\Delta\chi^2=9.0$) confidence limits.
   - Enforces strict period straddling validation ($P_{\min} < P_{\text{best}} < P_{\max}$).

3. **Two-Tier Privacy & Data Provenance Model**:
   - Strict separation between private user drafts (`is_community=False`) and published community data (`is_community=True`).
   - One-click **`[ 🌐 Transfer ]`** action to publish private observations to the public tier while retaining uploader credit.

4. **Persistent Volume Storage**:
   - Hugging Face Spaces & Docker persistent volume mounting at `/data/db.sqlite3` and `/data/media/`.

5. **Enhanced UI Layout**:
   - Top-aligned left sidebar navigation menu with responsive dropdown hierarchy.

---

## 🚀 Quick Start (Local Setup)

### Prerequisites
Install [uv](https://docs.astral.sh/uv/getting-started/installation/):
```bash
pipx install uv
```

### Installation
```bash
git clone https://github.com/poshakgandhi/cobbled.git
cd cobbled
git checkout cobbled-2.0
cp .env.default .env

uv venv
source .venv/bin/activate
make develop
make setup
```

Run dev server:
```bash
PYTHONPATH=cobbled python cobbled/manage.py runserver 0.0.0.0:8000
```
Open `http://localhost:8000` in your browser.

---

## 📁 Standalone Gaia-BH1 Fitting Script
A standalone, zero-framework Python script is included at [`cobbled/fit_gaia_bh1_simple.py`](file:///soft/cobbled/cobbled/fit_gaia_bh1_simple.py) for testing directly in VSCode or Spyder:
```bash
python cobbled/fit_gaia_bh1_simple.py
```

---

## 📜 License
Apache-2.0 License.
