import dash
import dash_html_components as html
import dash_core_components as dcc
import base64
import json
import datetime
from functions import find_peaks_scipy
import plotly.graph_objects as go
import numpy as np

from dash.dependencies import Input, Output, State

external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div(
    [
        dcc.Tabs(
            id="tabs-example",
            value="tab-1",
            children=[
                dcc.Tab(
                    label="Starting parameters",
                    value="tab-1",
                    children=[
                        dcc.Upload(
                            id="upload-data",
                            children=html.Div(
                                [
                                    "Drag and Drop or ",
                                    html.A("Select a File"),
                                    " to use as a reference file.",
                                ]
                            ),
                            style={
                                "width": "100%",
                                "height": "60px",
                                "lineHeight": "60px",
                                "borderWidth": "1px",
                                "borderStyle": "dashed",
                                "borderRadius": "5px",
                                "textAlign": "center",
                            },
                            multiple=False,
                        ),
                        html.Div(id="output-data-upload"),
                        html.Div(
                            [
                                html.H3(
                                    "Uploaded Data",
                                    style={"text-align": "center"},
                                ),
                                dcc.Graph(id="spectrum-original"),
                            ]
                        ),
                    ],
                ),
                dcc.Tab(
                    label="Analysis",
                    value="tab-2",
                    children=[
                        dcc.Upload(
                            id="upload-data-multiple",
                            children=html.Div(
                                [
                                    "Add ",
                                    html.A("sample files"),
                                    " to compare with the reference.",
                                ]
                            ),
                            style={
                                "width": "100%",
                                "height": "60px",
                                "lineHeight": "60px",
                                "borderWidth": "1px",
                                "borderStyle": "dashed",
                                "borderRadius": "5px",
                                "textAlign": "center",
                            },
                            multiple=True,
                        ),
                        html.Div(id="output-data-upload-multiple"),
                    ],
                ),
            ],
        ),
        html.Div(id="tabs-example-content"),
    ]
)


def parse_contents(contents):
    content_type, content_string = contents.split(",")
    decoded = base64.b64decode(content_string)
    j = json.loads(decoded)
    return j


def make_spectrum_with_picked_peaks(x, y, peaks, fwhm, hm, leftips, rightips):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name="original"))
    fig.add_trace(go.Scatter(x=x[peaks], y=y[peaks], mode="markers", name="peaks"))
    for i in range(len(hm)):
        fig.add_trace(
            go.Scatter(
                x=x[leftips[i] : rightips[i]],
                y=[hm[i]] * fwhm[i],
                mode="lines",
                name="peak" + str(i),
            )
        )
    return fig


@app.callback(
    Output("output-data-upload", "children"),
    Output("spectrum-original", "figure"),
    Input("upload-data", "contents"),
    State("upload-data", "filename"),
    State("upload-data", "last_modified"),
)
def update_output_tab_1(contents, filename, last_modified):
    if contents is not None:
        j = parse_contents(contents)
        x = np.array(j["time"][:6000])
        y = np.array(j["intensities"]["254"][:6000])
        peaks, fwhm, hm, leftips, rightips = find_peaks_scipy(y)

        fwhm = np.array(np.floor(fwhm), dtype=int)
        leftips = np.array(np.floor(leftips), dtype=int)
        rightips = np.array(np.floor(rightips), dtype=int)

        fig = make_spectrum_with_picked_peaks(x, y, peaks, fwhm, hm, leftips, rightips)

        return (
            html.Div(
                [
                    html.H5(filename),
                    html.H6(datetime.datetime.fromtimestamp(last_modified)),
                    html.H6(j["Sample Name"]),
                    html.H6(j["Run Name"]),
                    html.H6(j["Method Name"]),
                ]
            ),
            fig,
        )
    else:
        return html.Div([html.H5("Please enjoy some dummy data!")]), go.Figure(
            go.Scatter(x=[1, 2, 3], y=[1, 2, 3], mode="lines", name="dummy")
        )


@app.callback(
    Output("output-data-upload-multiple", "children"),
    Input("upload-data-multiple", "list_of_contents"),
    State("upload-data-multiple", "list_of_filenames"),
    State("upload-data-multiple", "list_of_last_modified"),
)
def update_output_tab_2(list_of_contents, list_of_filenames, list_of_last_modified):
    if list_of_contents is not None:
        children = [
            parse_contents(c, n, d)
            for c, n, d in zip(
                list_of_contents, list_of_filenames, list_of_last_modified
            )
        ]
        return children


if __name__ == "__main__":
    app.run_server(debug=True)
