import hashlib
import json
import numpy as np
import pymc as pm
import astropy.units as u
from astropy.time import Time
from thejoker import TheJoker, JokerPrior, RVData
from thejoker.units import with_unit

from app.plots.rv_curve import load_rv_data
from app.models.keplerian_fit import KeplerianFit

# Global in-memory cache as a fast secondary lookup
_samples_cache = {}


def get_rv_data_hash(df) -> str:
    """
    Computes a deterministic SHA256 hash of the RV observations.
    """
    data_str = json.dumps(
        [list(df["jd"].values), list(df["radial_velocity"].values)],
        sort_keys=True
    )
    return hashlib.sha256(data_str.encode("utf-8")).hexdigest()


def serialize_samples(samples, max_samples=50) -> dict | None:
    """
    Serializes a subset of JokerSamples (always including the MAP orbit at index 0)
    to a JSON-serializable dictionary.
    """
    if samples is None or len(samples) == 0:
        return None

    num_samples = len(samples)
    indices = [0]
    if num_samples > 1:
        rng = np.random.default_rng(42)
        extra_indices = list(rng.choice(
            np.arange(1, num_samples),
            size=min(num_samples - 1, max_samples - 1),
            replace=False
        ))
        indices.extend(extra_indices)

    serialized = {
        "t_ref_jd": float(samples.t_ref.jd) if hasattr(samples.t_ref, "jd") else float(samples.t_ref),
        "P": [float(val) for val in samples["P"][indices].value],
        "e": [float(val) for val in samples["e"][indices].value],
        "omega": [float(val) for val in samples["omega"][indices].value],
        "M0": [float(val) for val in samples["M0"][indices].value],
        "K": [float(val) for val in samples["K"][indices].value],
        "v0": [float(val) for val in samples["v0"][indices].value],
    }
    return serialized


def deserialize_samples(serialized) -> TheJoker | None:
    """
    Reconstructs a JokerSamples object from a serialized dictionary.
    """
    if not serialized:
        return None

    from thejoker import JokerSamples
    t_ref = Time(serialized["t_ref_jd"], format="jd")
    samples = JokerSamples(
        samples={
            "P": serialized["P"] * u.day,
            "e": serialized["e"] * u.one,
            "omega": serialized["omega"] * u.rad,
            "M0": serialized["M0"] * u.rad,
            "K": serialized["K"] * u.km / u.s,
            "v0": serialized["v0"] * u.km / u.s,
        },
        t_ref=t_ref
    )
    return samples


def run_joker_fit(source, prior_samples=100000, p_guess=None, k_guess=None, v0_guess=None, e_guess=None, user=None):
    """
    Runs The Joker rejection sampler, dynamically tuning priors based on guesses,
    and saves the fit to the database.
    """
    try:
        df = load_rv_data(source, user=user)
    except ValueError:
        return None, None

    if df.shape[0] < 3:
        return None, None

    t = Time(df["jd"].values, format="jd")
    rv = df["radial_velocity"].values * u.km / u.s
    rv_err = df["radial_velocity_error"].values * u.km / u.s
    data = RVData(t, rv, rv_err)

    # Use guesses to set prior bounds and linear parameters
    baseline = df["jd"].max() - df["jd"].min()
    
    # 1. Period (P) prior range
    if p_guess is not None and p_guess > 0:
        P_min = max(0.1, 0.7 * p_guess) * u.day
        P_max = 1.3 * p_guess * u.day
    else:
        P_min = 2.0 * u.day
        P_max = max(baseline * 4.0, 100.0) * u.day

    # 2. Semi-amplitude (K) scale prior
    if k_guess is not None and k_guess > 0:
        sigma_K0 = k_guess * u.km / u.s
    else:
        sigma_K0 = 30.0 * u.km / u.s

    # Define custom model context for custom priors
    with pm.Model() as model:
        pars = {}

        # 3. Custom Systemic Velocity (v0) prior
        if v0_guess is not None:
            v0 = pm.Normal("v0", v0_guess, 15.0)
            pars["v0"] = with_unit(v0, u.km / u.s)

        # 4. Custom Eccentricity (e) prior
        if e_guess is not None and 0.0 <= e_guess <= 0.99:
            e = pm.Uniform("e", max(0.001, e_guess - 0.15), min(0.99, e_guess + 0.15))
            pars["e"] = with_unit(e, u.one)

        prior = JokerPrior.default(
            P_min=P_min,
            P_max=P_max,
            sigma_K0=sigma_K0,
            sigma_v=100.0 * u.km / u.s,
            model=model,
            pars=pars
        )

    joker = TheJoker(prior)
    samples = joker.rejection_sample(data, prior_samples=prior_samples)

    if len(samples) == 0:
        return None, []

    sample_arrays = {}
    for k in ['P', 'e', 'omega', 'K', 'v0']:
        v = samples[k]
        if hasattr(v, 'value'):
            v = v.value
        if np.isscalar(v) or v.ndim == 0:
            v = np.array([v])
        sample_arrays[k] = v

    # Compute mass function for all samples in Solar Masses
    # f(m) = 1.03606e-7 * P * |K|^3 * (1 - e^2)^1.5
    f_m_vals = 1.03606e-7 * sample_arrays['P'] * (np.abs(sample_arrays['K']) ** 3) * ((1.0 - sample_arrays['e'] ** 2) ** 1.5)
    sample_arrays['f_m'] = f_m_vals


    parameters = []
    names = {
        'P': ('Orbital Period (P)', 'days'),
        'e': ('Eccentricity (e)', ''),
        'omega': ('Argument of Periastron (ω)', 'rad'),
        'K': ('Velocity Amplitude (K)', 'km/s'),
        'v0': ('Systemic Velocity (v0)', 'km/s'),
        'f_m': ('Binary Mass Function f(m)', 'M_☉'),
    }

    for key, (label, unit) in names.items():
        vals = sample_arrays[key]

        map_val = vals[0]  # The first sample is the best-fit MAP orbit
        median = np.median(vals)
        std = np.std(vals)
        ci_low = np.percentile(vals, 16)
        ci_high = np.percentile(vals, 84)

        if len(vals) <= 1:
            err_str = "N/A"
            ci_str = "N/A"
        else:
            fmt = ".4f" if key == 'f_m' else ".2f"
            err_str = f"{std:{fmt}}"
            ci_str = f"{ci_low:{fmt}} – {ci_high:{fmt}}"

        fmt = ".4f" if key == 'f_m' else ".2f"
        parameters.append({
            "name": label,
            "unit": unit,
            "val": f"{map_val:{fmt}}",
            "err": err_str,
            "ci": ci_str
        })


    # Persist the fit results directly to the database
    data_hash = get_rv_data_hash(df)
    KeplerianFit.objects.update_or_create(
        source=source,
        defaults={
            "fit_parameters": parameters,
            "sample_bundle": serialize_samples(samples),
            "observation_hash": data_hash,
        }
    )

    return samples, parameters


def get_fit_results(source, force_run=False, p_guess=None, k_guess=None, v0_guess=None, e_guess=None, user=None):
    """
    Retrieves the fit results. First checks Django database. If force_run is True or
    no saved fit matches the current observation data hash, it executes a new fit.
    """
    try:
        df = load_rv_data(source, user=user)
    except ValueError:
        return None, None

    if df.shape[0] < 3:
        return None, None

    num_points = df.shape[0]
    data_hash = get_rv_data_hash(df)
    cache_key = f"{source.id}_{num_points}_{data_hash}"

    # 1. Check in-memory cache first
    if not force_run and p_guess is None and k_guess is None and v0_guess is None and e_guess is None:
        if cache_key in _samples_cache:
            return _samples_cache[cache_key]

    # 2. Check Django Database next (if not forced and no custom guesses specified)
    if not force_run and p_guess is None and k_guess is None and v0_guess is None and e_guess is None:
        saved_fit = KeplerianFit.objects.filter(source=source).order_by("-created_at").first()
        if saved_fit:
            samples = deserialize_samples(saved_fit.sample_bundle)
            parameters = saved_fit.fit_parameters
            # Cache it in memory for fast subsequent page loads
            _samples_cache[cache_key] = (samples, parameters)
            return samples, parameters

    # 3. Run a new fit (forced, guesses provided, or no saved fit found)
    samples, parameters = run_joker_fit(
        source,
        p_guess=p_guess,
        k_guess=k_guess,
        v0_guess=v0_guess,
        e_guess=e_guess,
        user=user
    )
    
    if samples is not None:
        _samples_cache[cache_key] = (samples, parameters)

    return samples, parameters
