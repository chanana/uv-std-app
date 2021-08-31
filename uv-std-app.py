import base64
import json

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash.dependencies import Input, Output, State

from functions import find_peaks_scipy

# Define themes for plotly and dash
dash_theme = dbc.themes.SANDSTONE
plotly_theme = "ggplot2"

app = dash.Dash(__name__, external_stylesheets=[dash_theme])

tab1 = dbc.Tab(
    label="Reference File",
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
        html.Div(id="reference-row"),
        dcc.Store(id="peak-tables"),
    ],
)

tab2 = dbc.Tab(
    label="Sample Files",
    id="tab-2",
    children=[
        dbc.Row(
            dbc.Col(
                dcc.Upload(
                    id="upload-data-multiple",
                    multiple=True,
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
                ),
            )
        ),
    ],
)

tab3 = dbc.Tab(
    label="Details",
    id="tab-3",
    children=[
        dbc.Row(dbc.Col()),
        html.Div(id="samples-uploaded"),
    ],
)
app.layout = dbc.Container(dbc.Tabs(children=[tab1, tab2, tab3], className="nav-fill"))


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
                name="peak" + str(i + 1),
            )
        )
    fig.update_layout(template=plotly_theme)
    return fig


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


def make_data_table(peaks, heights, fwhm, ref_df=None):
    df = pd.DataFrame(index=["Position", "Height", "FWHM"])
    df["Parameter"] = ["Position (s)", "Height", "FWHM"]
    for i in range(len(peaks)):
        df["Peak " + str(i + 1)] = [peaks[i] / 10.0, heights[i], fwhm[i] / 10.0]

    if ref_df is None:
        return df
    else:
        # Filter both current and reference data tables to include only columns with
        # "Peak" in their name and then take their difference to 2 decimals
        df_filtered = df.filter(regex="Peak*").to_numpy()
        ref_df_filtered = ref_df.filter(regex="Peak*").to_numpy()
        diff = pd.DataFrame(ref_df_filtered - df_filtered)
        diff = diff.round(2)

        # Modify current data table to have <data/diff> for each cell
        for i in range(df.shape[0]):
            for j in range(1, df.shape[1]):
                df.iloc[i, j] = str(df.iloc[i, j]) + "/" + str(diff.iloc[i, j - 1])
    return df


def get_file_contents_and_analyze(content, filename, ref_df=None):
    j = parse_contents(content)
    x = np.array(j["time"][:6000])
    y = np.array(j["intensities"]["254"][:6000])
    peaks, heights, fwhm, hm, leftips, rightips = find_peaks_scipy(y)

    heights = np.round(heights, 2)
    fwhm = np.array(np.floor(fwhm), dtype=int)
    leftips = np.array(np.floor(leftips), dtype=int)
    rightips = np.array(np.floor(rightips), dtype=int)

    fig = make_spectrum_with_picked_peaks(x, y, peaks, fwhm, hm, leftips, rightips)
    info_card = make_sample_info_card(sample_info=j, filename=filename)
    data_table = make_data_table(peaks, heights, fwhm, ref_df)

    return info_card, fig, data_table


def highlight_cells(data_table, position_tolerance):
    # This function is called for every data table that is rendered. If that table is
    # of the reference sample, then the columns for all of the peaks will be of dtype
    # numpy.float64. Checking if the first column is float64 is enough to determine if
    # the table is the reference and thus skip any highlighting.
    if data_table["Peak 1"].dtype == np.float64:
        return [{"if": {"row_index": "odd"}, "backgroundColor": "rgb(248, 248, 248)"}]

    columns = data_table.filter(regex="Peak*").columns.to_list()
    rows = ["Position"]  # We only have a tolerance on position (for now)
    # This is one big conditional expression https://stackoverflow.com/a/9987533 and
    # sort of looks like a list comprehension but it's not
    return [
        {
            "if": {
                "row_index": i,
                "column_id": col,
            },
            "backgroundColor": "#2ECC40",  # Green
            "color": "white",
        }
        if abs(float(str(data_table.loc[row, col]).split("/")[1])) < position_tolerance
        else {
            "if": {
                "row_index": i,
                "column_id": col,
            },
            "backgroundColor": "#FF4136",  # Red
            "color": "white",
        }
        if abs(float(str(data_table.loc[row, col]).split("/")[1])) >= position_tolerance
        else {}
        for col in columns
        for i, row in enumerate(rows)
    ] + [{"if": {"row_index": "odd"}, "backgroundColor": "#f8f8f8"}]


def put_into_html(
    info_card, figure, data_table, position_tolerance=3, width_col_1=3, width_col_2=9
):
    col1 = dbc.Col(info_card, width=width_col_1)
    col2 = dbc.Col(dcc.Graph(figure=figure), width=width_col_2)
    row1 = dbc.Row(children=[col1, col2], align="center")
    row2 = dbc.Row(
        dbc.Col(
            dash_table.DataTable(
                columns=[{"name": i, "id": i} for i in data_table.columns],
                data=data_table.to_dict("records"),
                style_data_conditional=(
                    highlight_cells(data_table, position_tolerance)
                ),
                style_header={
                    "backgroundColor": "rgb(230, 230, 230)",
                    "fontWeight": "bold",
                },
            ),
            width=12,
        ),
        align="center",
    )

    return [row1, row2]


@app.callback(
    Output("reference-row", "children"),
    Output("peak-tables", "data"),
    Input("upload-data", "contents"),
    State("upload-data", "filename"),
)
def update_output_tab_1(contents, filename):
    if contents is not None:
        info_card, fig, data_table = get_file_contents_and_analyze(contents, filename)
        data = {"reference": data_table.to_json(orient="split")}
        return put_into_html(info_card, fig, data_table), json.dumps(data)
    else:
        return [None, None]


@app.callback(
    Output("samples-uploaded", "children"),
    Input("upload-data-multiple", "contents"),
    Input("peak-tables", "data"),
    State("upload-data-multiple", "filename"),
)
def update_output_tab_2(contents: list, data: str, filename: list) -> list:
    if contents is not None:
        children = []
        ref_df = json.loads(data)
        ref_df = pd.read_json(ref_df["reference"], orient="split")
        for content, f in zip(contents, filename):
            info_card, fig, data_table = get_file_contents_and_analyze(
                content, f, ref_df
            )
            children += put_into_html(info_card, fig, data_table)

        return children


if __name__ == "__main__":
    app.run_server(debug=True)
