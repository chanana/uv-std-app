import base64
import json

import dash_bootstrap_components as dbc
import dash_html_components as html
import plotly.graph_objects as go
from scipy.signal import find_peaks, peak_widths

from constants import PLOTLY_THEME


def find_peaks_scipy(x, height=None):
    """Find peaks in given 1D vector

    Args:
        x (numpy.ndarray): 1D vector of the y values of a waveform
        height ([float], optional): The minimum height required to be considered a
        peak. If no height is specified, it is taken as 10% of the maximum value in x.
        Defaults to None.
    """
    if height is None:
        height = 0.1 * max(x)

    peaks, heights = find_peaks(x=x, height=height)
    heights = heights["peak_heights"]
    # fwhm = full width at half max (width of the peak at specified height)
    # hm = half max (height at which fwhm was found),
    # leftips, rightips = intersection on x axis for y=hm
    fwhm, hm, leftips, rightips = peak_widths(x=x, peaks=peaks, rel_height=0.5)

    return peaks, heights, fwhm, hm, leftips, rightips


def make_spectrum_with_picked_peaks(
    x, y, peaks, fwhm, hm, leftips, rightips, plotly_theme=PLOTLY_THEME
):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name="original"))
    fig.add_trace(go.Scatter(x=x[peaks], y=y[peaks], mode="markers", name="peaks"))
    for i in range(len(hm)):
        fig.add_trace(
            go.Scatter(
                x=x[leftips[i] : rightips[i]],
                y=[hm[i]] * fwhm[i],
                mode="lines",
                name="peak" + str(i + 1),
            )
        )
    fig.update_layout(template=plotly_theme)
    return fig


def parse_contents(contents):
    content_type, content_string = contents.split(",")
    decoded = base64.b64decode(content_string)
    j = json.loads(decoded)
    return j


def make_sample_info_card(sample_info, filename):
    info_card = dbc.Card(
        dbc.CardBody(
            children=[html.P(filename)]
            + [
                html.P([html.B(i), ": ", sample_info[i]])
                for i in ["Sample Name", "Method Name", "Run Date"]
            ],
        )
    )
    return info_card


def make_fig_for_diff_tables(df, tolerance):
    fig = go.Figure()
    for i in range(df.shape[0]):
        fig.add_trace(
            go.Scatter(
                x=df.columns,
                y=df.iloc[i, :].values,
                name="Sample " + str(i + 1),
                mode="lines+markers",
            )
        )
    fig.add_trace(
        go.Scatter(
            x=df.columns,
            y=[tolerance] * len(df.columns),
            name="upper limit",
            mode="lines",
            line=dict(color="firebrick", width=2, dash="dash"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df.columns,
            y=[-tolerance] * len(df.columns),
            name="lower limit",
            mode="lines",
            line=dict(color="firebrick", width=2, dash="dash"),
        )
    )
    fig.update_layout(template=PLOTLY_THEME)
    return fig
