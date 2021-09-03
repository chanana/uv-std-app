import plotly.graph_objects as go
from constants import PLOTLY_THEME


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
