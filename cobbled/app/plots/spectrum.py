import pandas as pd
import plotly.graph_objects as go
from plotly.offline import plot

from app.models import Observation

x_margin = 5


def load_spectrum_data(observation: Observation) -> pd.DataFrame:
    try:
        dataset = observation.dataset
    except AttributeError:
        raise ValueError("No Dataset for observation")

    df = dataset.get_df()
    return df


def get_spectrum_plot(observation: Observation):
    data = load_spectrum_data(observation)

    # Setup figure
    fig = go.Figure()

    # Plot central line
    fig.add_trace(
        go.Scatter(
            x=data["wavelength"],
            y=data["flux"],
            error_y=dict(type="data", array=data["flux_err"], visible=data["flux_err"])
            if "flux_err" in data.columns
            else None,
            name="Flux",
            mode="lines",
            line=dict(width=1, color="black"),
        )
    )

    fig.update_xaxes(
        minor=dict(ticks="inside", ticklen=4, tickmode="auto", nticks=10, showgrid=True),
        ticks="inside",
        ticklen=7,
        tickmode="auto",
        showgrid=True,
        title=f"Wavelength ({observation.dataset.wavelength_units.symbol})",
    )
    fig.update_yaxes(
        minor=dict(ticks="inside", ticklen=4, tickmode="auto", nticks=10, showgrid=True),
        ticks="inside",
        ticklen=7,
        tickmode="auto",
        showgrid=True,
        title=f"Flux ({observation.dataset.flux_units.symbol})",
    )
    fig.update_layout(
        showlegend=False,
    )

    return plot(fig, output_type="div")
