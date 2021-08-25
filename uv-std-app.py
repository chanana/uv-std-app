import base64
import json

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import numpy as np
import plotly.graph_objects as go
from dash.dependencies import Input, Output, State

from functions import find_peaks_scipy

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

tab1 = dbc.Tab(
    label="Starting parameters",
    id="tab-1",
    children=[
        dbc.Row(
            dbc.Col(
                dcc.Upload(
                    id="upload-data",
                    multiple=False,
                    children=[
                        "Drag and Drop or ",
                        html.A("Select a File"),
                        " to use as a reference file.",
                    ],
                    style={
                        "width": "100%",
                        "height": "60px",
                        "lineHeight": "60px",
                        "borderWidth": "1px",
                        "borderStyle": "dashed",
                        "borderRadius": "5px",
                        "textAlign": "center",
                    },
                ),
                width=12,
            ),
            align="center",
        ),
        dbc.Row(id="reference-row", children=[], align="center"),
    ],
)

tab2 = dcc.Tab(
    label="Analysis",
    id="tab-2",
    children=[
        dbc.Row(
            dbc.Col(
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
            )
        ),
        html.Div(id="output-data-upload-multiple"),
    ],
)
app.layout = dbc.Container(
    [
        dcc.Tabs(id="tabs-example", value="tab-1", children=[tab1, tab2]),
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


def make_sample_info_card(element_id, sample_info, filename):
    info_card = dbc.Card(
        dbc.CardBody(
            id=element_id,
            children=[html.P(filename)]
            + [
                html.P([html.B(i), ": ", sample_info[i]])
                for i in ["Sample Name", "Method Name", "Run Date"]
            ],
        )
    )
    return info_card


def make_fig_and_info_columns(info_card, figure, width_col_1=3, width_col_2=9):
    col1 = dbc.Col(info_card, width=width_col_1)
    col2 = dbc.Col(dcc.Graph(id="reference-fig", figure=figure), width=width_col_2)
    return [col1, col2]


@app.callback(
    Output("reference-row", "children"),
    Input("upload-data", "contents"),
    State("upload-data", "filename"),
)
def update_output_tab_1(contents, filename):
    if contents is not None:
        j = parse_contents(contents)
        x = np.array(j["time"][:6000])
        y = np.array(j["intensities"]["254"][:6000])
        peaks, fwhm, hm, leftips, rightips = find_peaks_scipy(y)

        fwhm = np.array(np.floor(fwhm), dtype=int)
        leftips = np.array(np.floor(leftips), dtype=int)
        rightips = np.array(np.floor(rightips), dtype=int)

        fig = make_spectrum_with_picked_peaks(x, y, peaks, fwhm, hm, leftips, rightips)
        info_card = make_sample_info_card(
            element_id="reference-file", sample_info=j, filename=filename
        )
        return make_fig_and_info_columns(info_card, fig)
    # else:
    #     return children


# @app.callback(
#     Output("output-data-upload-multiple", "children"),
#     Input("upload-data-multiple", "list_of_contents"),
#     State("upload-data-multiple", "list_of_filenames"),
#     State("upload-data-multiple", "list_of_last_modified"),
# )
# def update_output_tab_2(list_of_contents, list_of_filenames, list_of_last_modified):
#     if list_of_contents is not None:
#         children = [parse_contents(c) for c in list_of_contents]
#         return children


if __name__ == "__main__":
    app.run_server(debug=True)
