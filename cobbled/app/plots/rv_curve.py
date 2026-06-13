import numpy as np
import pandas as pd
import plotly.graph_objects as go
from django.db.models import F
from plotly.offline import plot

from app.models import DataSet, Observation, Source

x_margin = 5


def load_gaia_rv_data(source: Source) -> pd.DataFrame:
    try:
        gaia_rv = source.gaiainfo.radial_velocity
        gaia_rv_err = source.gaiainfo.radial_velocity_error

        # Check both values actually exist
        assert gaia_rv is not None
        assert gaia_rv_err is not None

        return gaia_rv, gaia_rv_err

    except (AttributeError, AssertionError):
        raise ValueError("No rv given for source")


def load_rv_data(source: Source, user=None) -> pd.DataFrame:
    from django.db.models import Q

    qset = DataSet.objects.filter(observation__source=source)

    if user and user.is_authenticated:
        if not user.is_staff:
            researcher = getattr(user, "researcher", None)
            if researcher:
                qset = qset.filter(
                    Q(is_valid=True) |
                    Q(observation__observer=researcher) |
                    Q(observation__project__principal_investigator=researcher) |
                    Q(observation__project__members=researcher) |
                    Q(observation__proposal__project__principal_investigator=researcher) |
                    Q(observation__proposal__project__members=researcher)
                ).distinct()
            else:
                qset = qset.filter(is_valid=True)
    else:
        qset = qset.filter(is_valid=True)

    qset = qset.annotate(jd=F("observation__jd"))

    df = pd.DataFrame(list(qset.values()))

    if df.empty:
        raise ValueError("No valid vr readings")

    return df


def get_rv_plot(source: Source, fit_samples=None, user=None):
    data = load_rv_data(source, user=user)

    jd_min = data["jd"].min()
    x = data["jd"] - jd_min
    y = data["radial_velocity"]
    yerr = data["radial_velocity_error"]

    # Setup figure
    fig = go.Figure()

    # Plot Gaia RV bounds if available
    try:
        gaia_rv, gaia_rv_err = load_gaia_rv_data(source)
        got_gaia_rv = True
    except ValueError:
        got_gaia_rv = False

    if got_gaia_rv:
        x_range = (-x_margin, data["jd"].max() - jd_min + x_margin)
        y1 = gaia_rv - gaia_rv_err
        y2 = gaia_rv + gaia_rv_err

        # Add hidden trace to enable fillbetween to latch to it
        fig.add_trace(
            go.Scatter(
                x=[-1e32, 1e32],
                y=[y1, y1],
                mode="lines",
                name="Gaia V_rad -error",
                line={"color": "red", "width": 0},
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[-1e32, 1e32],
                y=[y2, y2],
                mode="lines",
                name="Gaia V_rad +error",
                fill="tonexty",
                line={"color": "red", "width": 0},
            )
        )

    # Plot fitted orbits if available
    if fit_samples:
        x_range = (-x_margin, data["jd"].max() - jd_min + x_margin)
        x_grid = np.linspace(x_range[0], x_range[1], 500)
        jd_grid = x_grid + jd_min

        # Calculate next extrema for the best-fit model
        from astropy.time import Time
        t_now = Time.now().jd
        t_last_obs = data["jd"].max()
        
        # Get period for threshold check
        if hasattr(fit_samples, 'get_orbit'):
            import astropy.units as u
            best_orbit = fit_samples.get_orbit(0)
            best_P = best_orbit.P.to(u.day).value
        else:
            best_fit = fit_samples[0]
            best_P = best_fit['P']

        limit = max(365.0, 5 * best_P)
        is_far_ahead = (t_now - t_last_obs) > limit

        extrema_x = []
        extrema_y = []
        extrema_text = []

        if not is_far_ahead:
            t_last = t_now
            if hasattr(fit_samples, 'get_orbit'):
                t_eval = np.linspace(t_last, t_last + best_P, 300)
                t_eval_time = Time(t_eval, format='jd')
                rv_eval = best_orbit.radial_velocity(t_eval_time).to(u.km/u.s).value
                
                min_idx = np.argmin(rv_eval)
                max_idx = np.argmax(rv_eval)
                
                extrema_x = [t_eval[min_idx] - jd_min, t_eval[max_idx] - jd_min]
                extrema_y = [rv_eval[min_idx], rv_eval[max_idx]]
                extrema_text = ["Next Min RV Peak", "Next Max RV Peak"]
            else:
                # Mock data
                best_K = best_fit['K']
                best_v0 = best_fit['v0']
                best_phi = best_fit.get('phi', 0.0)
                
                t_eval = np.linspace(t_last, t_last + best_P, 300)
                x_eval = t_eval - jd_min
                rv_eval = best_v0 + best_K * np.sin(2 * np.pi * x_eval / best_P + best_phi)
                
                min_idx = np.argmin(rv_eval)
                max_idx = np.argmax(rv_eval)
                
                extrema_x = [t_eval[min_idx] - jd_min, t_eval[max_idx] - jd_min]
                extrema_y = [rv_eval[min_idx], rv_eval[max_idx]]
                extrema_text = ["Next Min RV Peak", "Next Max RV Peak"]

        if hasattr(fit_samples, 'get_orbit'):
            # It's a JokerSamples object
            import astropy.units as u
            from astropy.time import Time
            t_grid_astropy = Time(jd_grid, format='jd')
            num_samples = len(fit_samples)
            num_plot = min(num_samples, 25)
            
            # Select random subset (reproducible with seed)
            rng = np.random.default_rng(42)
            indices = rng.choice(num_samples, size=num_plot, replace=False)
            
            # Draw individual posterior orbits in thin light lines
            for idx in indices:
                orbit = fit_samples.get_orbit(idx)
                rv_orbit = orbit.radial_velocity(t_grid_astropy).to(u.km/u.s).value
                fig.add_trace(
                    go.Scatter(
                        x=x_grid,
                        y=rv_orbit,
                        mode="lines",
                        line=dict(color="rgba(33, 150, 243, 0.12)", width=1.5),
                        hoverinfo="skip",
                        showlegend=False,
                    )
                )
            
            # Draw MAP/best fit orbit in solid line (index 0 is MAP)
            map_orbit = fit_samples.get_orbit(0)
            rv_map = map_orbit.radial_velocity(t_grid_astropy).to(u.km/u.s).value
            fig.add_trace(
                go.Scatter(
                    x=x_grid,
                    y=rv_map,
                    mode="lines",
                    name="The Joker Fit",
                    line=dict(color="#2196f3", width=3),
                    showlegend=True,
                )
            )
        else:
            # It's mock data (list of dicts)
            for i, p in enumerate(fit_samples):
                P = p['P']
                K = p['K']
                v0 = p['v0']
                phi = p.get('phi', 0.0)
                y_fit = v0 + K * np.sin(2 * np.pi * x_grid / P + phi)
                color = "rgba(33, 150, 243, 0.15)" if i > 0 else "#2196f3"
                width = 1.5 if i > 0 else 3
                fig.add_trace(
                    go.Scatter(
                        x=x_grid,
                        y=y_fit,
                        mode="lines",
                        name="Mock Best Fit" if i == 0 else None,
                        line=dict(color=color, width=width),
                        hoverinfo="skip",
                        showlegend=(i == 0),
                    )
                )

        # Plot planning next extrema on the RV curve (red squares)
        if extrema_x:
            fig.add_trace(
                go.Scatter(
                    x=extrema_x,
                    y=extrema_y,
                    mode="markers+text",
                    name="Model Next Extrema",
                    marker=dict(
                        symbol="square",
                        color="red",
                        size=10,
                        line=dict(width=1.5, color="white")
                    ),
                    text=extrema_text,
                    textposition="top center",
                    textfont=dict(color="red", size=9, family="Arial Black"),
                    showlegend=True,
                )
            )

    # Plot observed data points
    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            error_y=dict(type="data", array=yerr, visible=True),
            name="V_rad (Observed)",
            mode="markers",
            marker={
                "symbol": "circle",
                "color": "green",
                "size": 10,
                "line": dict(width=2, color="black"),
            },
        )
    )

    plotAnnotes = []

    # Fetch all relevant observations in a single query with select_related
    # to avoid the N+1 query problem during annotation URL generation.
    obs_dict = {
        obs.pk: obs
        for obs in Observation.objects.filter(source=source).select_related(
            "proposal", "proposal__project", "project"
        )
    }

    # A nasty and a bit hacky way to get hyperlinks onto the plot without needing Dash magic
    for index, row in data.iterrows():
        obs_id = row["observation_id"]
        obs_obj = obs_dict.get(obs_id)
        if obs_obj:
            url = obs_obj.get_absolute_url()
            plotAnnotes.append(
                dict(
                    x=row["jd"] - jd_min,
                    y=row["radial_velocity"],
                    text=f"<a href='{url}'>     </a>",
                    showarrow=False,
                    xanchor="center",
                    yanchor="middle",
                )
            )

    # Add label to Gaia RV range if it was plotted earlier
    if got_gaia_rv:
        x_range = (-x_margin, data["jd"].max() - jd_min + x_margin)
        plotAnnotes.append(
            dict(
                x=0.5 * (x_range[0] + x_range[1]),
                y=gaia_rv,
                text="Gaia RV ± 1σ",
                xanchor="right",
            )
        )

    fig.update_xaxes(
        minor=dict(ticks="inside", ticklen=4, tickmode="auto", nticks=10, showgrid=True),
        ticklen=7,
        tickmode="auto",
        ticks="inside",
        showgrid=True,
        title=f"Time since JD {jd_min:.1f} (days)",
    )
    fig.update_yaxes(
        minor=dict(ticks="inside", ticklen=4, tickmode="auto", nticks=10, showgrid=True),
        ticklen=7,
        tickmode="auto",
        ticks="inside",
        showgrid=True,
        title="Radial Velocity (km/s)",
    )
    fig.update_layout(
        annotations=plotAnnotes,
        showlegend=True if (got_gaia_rv or fit_samples is not None) else False,
        xaxis_range=[-x_margin, data["jd"].max() - jd_min + x_margin],
        dragmode="pan",
    )

    return plot(fig, output_type="div")
