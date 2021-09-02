import base64
import json

import dash_bootstrap_components as dbc
import dash_html_components as html
import plotly.graph_objects as go
from scipy.signal import find_peaks, peak_widths
import numpy as np
from typing import Optional

from constants import PLOTLY_THEME


def find_peaks_scipy(x, height=None):
    """Find peaks in given 1D vector

    Args:
        x (numpy.ndarray): 1D vector of the y values of a waveform
        height ([float], optional): The minimum height required to be considered a
        peak. If no height is specified, it is taken as 10% of the maximum value in x.
        Defaults to None.

    Returns:
        tuple of the following:
            fwhm = full width at half max (width of the peak at specified height)
            hm = half max (height at which fwhm was found),
            leftips, rightips = intersection on x axis for y=hm
        see scipy.signal.peak_widths docstring for more information
    """
    if height is None:
        height = 0.1 * max(x)

    peaks, heights = find_peaks(x=x, height=height)
    heights = heights["peak_heights"]
    #
    fwhm, hm, leftips, rightips = peak_widths(x=x, peaks=peaks)

    return peaks, heights, fwhm, hm, leftips, rightips


def make_spectrum_with_picked_peaks(
    x,
    y,
    peaks,
    fwhm,
    hm,
    leftips,
    rightips,
    plotly_theme=PLOTLY_THEME,
):
    """Make a plotly figure from peak parameters

    Args:
        x (numpy.ndarray): 1D vector of the x values of a waveform
        y (numpy.ndarray): 1D vector of the x values of a waveform
        peaks (numpy.ndarray): 1D vector of peaks from waveform
        fwhm (numpy.ndarray): 1D vector of full-width-at-half-maxima values
        hm (numpy.ndarray): 1D vector of the heights of the fwhm array
        leftips (numpy.ndarray): Interpolated positions of left intersection points
            of a horizontal line at the respective evaluation height
        rightips (numpy.ndarray): same as leftips except on the right side
        plotly_theme (str): theme for plotly. If none specified, default of "ggplot" is
            used

    Returns:
        go.Figure
    """
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
    """Parse contents of uploaded file to json-string

    Args:
        contents (str): contents of the uploaded file

    Returns:
        json-decoded string of contents
    """
    content_type, content_string = contents.split(",")
    decoded = base64.b64decode(content_string)
    j = json.loads(decoded)
    return j


def make_sample_info_card(sample_info, filename):
    """Makes a dash-bootstrap style card from sample information

    Args:
        sample_info (dict): information about sample such as method name or
            run date, etc.
        filename (str): name of the file being processed

    Returns:
        html (as a str) of the info-card
    """
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
    """Makes plotly figure for visualizing the differences with tolerances

    Args:
        df (pd.DataFrame): dataframe to be visualized
        tolerance (float): tolerance associated with that dataframe

    Returns:
        plotly figure
    """
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
