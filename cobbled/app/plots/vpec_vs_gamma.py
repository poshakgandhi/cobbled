import numpy as np
import plotly.graph_objects as go
from core.settings import MEDIA_ROOT
from numpy.lib.npyio import NpzFile
from plotly.offline import plot

from app.models import Source


def load_vpec_gamma_data(source: Source) -> NpzFile:
    try:
        source_id = source.gaiainfo.gaia_id
    except AttributeError:
        raise ValueError("No Gaia info for source")
    in_path = f"{MEDIA_ROOT}/demo_data/{source_id}/{source_id}_vpec_vs_gamma.npz"
    try:
        data = np.load(in_path)
        return data
    except FileNotFoundError:
        raise ValueError("No vpecvsgamma file provided for source_id")


def get_vvg_plot(source: Source):
    # Get data from hardcoded demo datafiles for now
    data = load_vpec_gamma_data(source)
    vpec = data["vpec"]
    vpec_lo = data["vpec_lo"]
    vpec_hi = data["vpec_hi"]
    gamma = data["gamma"]

    # Setup figure
    fig = go.Figure()

    # Deal with max and min values to plot fillbetween
    fig.add_trace(
        go.Scatter(x=gamma, y=vpec_hi, name="V_pec +error", line={"color": "green", "width": 0})
    )
    fig.add_trace(
        go.Scatter(
            x=gamma,
            y=vpec_lo,
            name="V_pec -error",
            fill="tonexty",
            line={"color": "green", "width": 0},
        )
    )

    # Plot central line
    fig.add_trace(
        go.Scatter(
            x=gamma, y=vpec, mode="lines", name="V_pec", line={"color": "black", "width": 2}
        )
    )

    # Plot minimum velocity
    y_min = vpec.min()
    x_min = gamma[np.argmin(vpec)]
    fig.add_trace(
        go.Scatter(
            x=[x_min],
            y=[y_min],
            name="V_pec Minimum",
            marker={
                "symbol": "circle",
                "color": "red",
                "size": 10,
                "line": dict(width=2, color="black"),
            },
        )
    )

    fig.update_xaxes(
        minor=dict(ticks="inside", ticklen=4, tickmode="auto", nticks=10, showgrid=True),
        ticks="inside",
        ticklen=7,
        tickmode="auto",
        showgrid=True,
        title="Systemic Velocity (km/s)",
    )
    fig.update_yaxes(
        minor=dict(ticks="inside", ticklen=4, tickmode="auto", nticks=10, showgrid=True),
        ticks="inside",
        ticklen=7,
        tickmode="auto",
        showgrid=True,
        title="Peculiar Velocity (km/s)",
    )

    window = (gamma.max() - gamma.min()) * 0.25
    x_left = x_min - window
    x_right = x_min + window
    x_idx = np.where((gamma >= x_left) & (gamma <= x_right))[0]
    y_hi_window = vpec_hi[x_idx]

    y_margin = (vpec_hi.max() - vpec_lo.min()) * 0.05
    y_top = y_hi_window.max() + y_margin
    y_bottom = vpec_lo.min() - y_margin

    fig.update_layout(
        showlegend=False, xaxis_range=[x_left, x_right], yaxis_range=[y_bottom, y_top]
    )

    return plot(fig, output_type="div")
