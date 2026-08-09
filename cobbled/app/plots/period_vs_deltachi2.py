import numpy as np
import plotly.graph_objects as go
import astropy.units as u
from astropy.time import Time
from app.fitting import load_rv_data

def get_period_vs_deltachi2_plot(source, fit_samples=None, user=None) -> str:
    """
    Generates a Plotly scatter plot showing Period vs Delta Chi^2 for accepted orbit samples (up to 50 max).
    The MAP (best-fit) orbit at index 0 is highlighted with a prominent gold star.
    """
    if fit_samples is None or len(fit_samples) == 0:
        return ""

    try:
        df = load_rv_data(source, user=user)
    except ValueError:
        return ""

    if df.shape[0] < 3:
        return ""

    t = Time(df["jd"].values, format="jd")
    rv_obs = df["radial_velocity"].values
    rv_err = df["radial_velocity_error"].values

    # Restrict to up to 50 samples max
    num_samples = min(50, len(fit_samples))
    
    periods = []
    deltachi2_vals = []
    ecc_vals = []
    k_vals = []

    # Compute chi2 for MAP orbit (index 0)
    if hasattr(fit_samples, 'get_orbit'):
        map_orbit = fit_samples.get_orbit(0)
        rv_map = map_orbit.radial_velocity(t).to(u.km/u.s).value
        chi2_map = np.sum(((rv_obs - rv_map) / rv_err) ** 2)
        
        for i in range(num_samples):
            orbit = fit_samples.get_orbit(i)
            P = orbit.P.to(u.day).value
            e = float(orbit.e.value) if hasattr(orbit.e, 'value') else float(orbit.e)
            K = orbit.K.to(u.km/u.s).value
            
            rv_mod = orbit.radial_velocity(t).to(u.km/u.s).value
            chi2_i = np.sum(((rv_obs - rv_mod) / rv_err) ** 2)
            d_chi2 = chi2_i - chi2_map
            
            periods.append(P)
            deltachi2_vals.append(max(0.0, d_chi2))
            ecc_vals.append(e)
            k_vals.append(K)
    else:
        # Dictionary samples
        map_fit = fit_samples[0]
        best_P = map_fit['P']
        best_K = map_fit['K']
        best_v0 = map_fit['v0']
        best_phi = map_fit.get('phi', 0.0)
        jd_min = df["jd"].min()
        x_eval = df["jd"].values - jd_min
        rv_map = best_v0 + best_K * np.sin(2 * np.pi * x_eval / best_P + best_phi)
        chi2_map = np.sum(((rv_obs - rv_map) / rv_err) ** 2)
        
        for i in range(num_samples):
            s = fit_samples[i]
            P = s['P']
            e = s.get('e', 0.0)
            K = s['K']
            v0 = s['v0']
            phi = s.get('phi', 0.0)
            rv_mod = v0 + K * np.sin(2 * np.pi * x_eval / P + phi)
            chi2_i = np.sum(((rv_obs - rv_mod) / rv_err) ** 2)
            d_chi2 = chi2_i - chi2_map
            
            periods.append(P)
            deltachi2_vals.append(max(0.0, d_chi2))
            ecc_vals.append(e)
            k_vals.append(K)

    periods = np.array(periods)
    deltachi2_vals = np.array(deltachi2_vals)
    ecc_vals = np.array(ecc_vals)
    k_vals = np.array(k_vals)

    fig = go.Figure()

    # Other accepted samples (indices 1..N-1)
    if num_samples > 1:
        fig.add_trace(go.Scatter(
            x=periods[1:],
            y=deltachi2_vals[1:],
            mode='markers',
            name='Accepted Orbits',
            marker=dict(
                size=10,
                color=ecc_vals[1:],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title='Eccentricity e', thickness=12, len=0.8),
                line=dict(width=1, color='#1e293b'),
                opacity=0.85
            ),
            text=[f"Sample #{i+1}<br>Period: {periods[i]:.3f} d<br>Δχ²: {deltachi2_vals[i]:.2f}<br>e: {ecc_vals[i]:.3f}<br>K: {k_vals[i]:.2f} km/s" for i in range(1, num_samples)],
            hoverinfo='text'
        ))

    # MAP Best-Fit Orbit (index 0)
    fig.add_trace(go.Scatter(
        x=[periods[0]],
        y=[deltachi2_vals[0]],
        mode='markers+text',
        name='MAP Solution (Best-Fit)',
        text=[f"  MAP (P = {periods[0]:.2f} d)"],
        textposition="top right",
        textfont=dict(size=13, color="#dc2626", family="sans-serif"),
        marker=dict(
            size=20,
            symbol='star',
            color='#dc2626',
            line=dict(width=2, color='#fef08a')
        ),
        hoverinfo='text',
        hovertext=[f"<b>MAP Solution (Best-Fit)</b><br>Period: {periods[0]:.4f} d<br>Δχ²: 0.00 (Minimum)<br>e: {ecc_vals[0]:.3f}<br>K: {k_vals[0]:.2f} km/s"]
    ))

    # Add 1-sigma & 3-sigma confidence thresholds
    max_dchi2 = max(10.0, np.max(deltachi2_vals) * 1.1)
    min_p = np.min(periods) * 0.95
    max_p = np.max(periods) * 1.05

    fig.add_shape(
        type="line",
        x0=min_p,
        x1=max_p,
        y0=1.0, y1=1.0,
        line=dict(color="#2563eb", width=1.5, dash="dash"),
    )
    fig.add_annotation(
        x=max_p, y=1.0,
        text="1σ (Δχ² = 1.0)",
        showarrow=False,
        font=dict(size=10, color="#2563eb"),
        yshift=8
    )

    fig.add_shape(
        type="line",
        x0=min_p,
        x1=max_p,
        y0=9.0, y1=9.0,
        line=dict(color="#d97706", width=1.5, dash="dot"),
    )
    fig.add_annotation(
        x=max_p, y=9.0,
        text="3σ (Δχ² = 9.0)",
        showarrow=False,
        font=dict(size=10, color="#d97706"),
        yshift=8
    )

    fig.update_layout(
        title=dict(
            text=f"<b>Posterior Period vs. Δχ² Profile</b> (Top {num_samples} Accepted Orbits)",
            font=dict(size=16)
        ),
        xaxis=dict(
            title="<b>Orbital Period P (days)</b>",
            showgrid=True,
            gridcolor='#e2e8f0'
        ),
        yaxis=dict(
            title="<b>Δχ² = χ² - χ²<sub>MAP</sub></b>",
            showgrid=True,
            gridcolor='#e2e8f0',
            range=[-0.5, max_dchi2]
        ),
        template="plotly_white",
        margin=dict(l=60, r=40, t=50, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig.to_html(full_html=False, include_plotlyjs="cdn")
