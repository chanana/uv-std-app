import json

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import numpy as np
import pandas as pd
from dash.dependencies import Input, Output, State

from constants import ALTERNATE_ROW_HIGHLIGHTING, TABLE_HEADER
from functions import (
    find_peaks_scipy,
    make_spectrum_with_picked_peaks,
    parse_contents,
    make_sample_info_card,
    make_fig_for_diff_tables,
)

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.SANDSTONE])

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
        dcc.Store(id="reference-table"),
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
        dbc.Row(
            children=[
                dbc.Col(
                    [
                        html.H4("{} Threshold ".format(k)),
                        dcc.Input(
                            id="{}-threshold".format(k),
                            type="number",
                            placeholder="{} threshold".format(k),
                            step=0.01,
                        ),
                    ],
                    width=4,
                )
                for k in ["position", "fwhm", "height"]
            ],
            align="center",
        ),
        dcc.Store(id="differences-table-storage"),
        html.Div(id="differences-table"),
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
        diff = np.around(ref_df_filtered - df_filtered, 2)
        diff = pd.DataFrame(
            diff, columns=["Peak " + str(i + 1) for i in range(diff.shape[1])]
        )

        # Modify current data table to have <data/diff> for each cell
        for i in range(df.shape[0]):
            for j in range(1, df.shape[1]):
                df.iloc[i, j] = str(df.iloc[i, j]) + "/" + str(diff.iloc[i, j - 1])
    return df, diff


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
    if ref_df is not None:
        data_table, differences = make_data_table(peaks, heights, fwhm, ref_df)
        return info_card, fig, data_table, differences
    else:
        data_table = make_data_table(peaks, heights, fwhm, ref_df)
        return info_card, fig, data_table


def highlight_cells(data_table, position_tolerance=3):
    # This function is called for every data table that is rendered. If that table is
    # of the reference sample, then the columns for all of the peaks will be of dtype
    # numpy.float64. Checking if the first column is float64 is enough to determine if
    # the table is the reference and thus skip any highlighting.
    if data_table["Peak 1"].dtype == np.float64:
        return [ALTERNATE_ROW_HIGHLIGHTING]

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
    ] + [ALTERNATE_ROW_HIGHLIGHTING]


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
                style_header=TABLE_HEADER,
            ),
            width=12,
        ),
        align="center",
    )

    return [row1, row2]


@app.callback(
    Output("reference-row", "children"),
    Output("reference-table", "data"),
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
    Output("differences-table-storage", "data"),
    Input("upload-data-multiple", "contents"),
    Input("reference-table", "data"),
    State("upload-data-multiple", "filename"),
)
def update_output_tab_2_and_3(contents: list, data: str, filename: list) -> tuple:
    if contents is not None:
        children = []
        positions = pd.DataFrame()
        fwhms = pd.DataFrame()
        heights = pd.DataFrame()

        ref_df = json.loads(data)
        ref_df = pd.read_json(ref_df["reference"], orient="split")
        for content, f in zip(contents, filename):
            info_card, fig, data_table, diff = get_file_contents_and_analyze(
                content, f, ref_df
            )
            children += put_into_html(info_card, fig, data_table)

            positions = positions.append(diff.iloc[[0]])
            fwhms = fwhms.append(diff.iloc[[1]])
            heights = heights.append(diff.iloc[[2]])

        peak_metadata = {
            "positions": positions.to_json(orient="split"),
            "fwhms": fwhms.to_json(orient="split"),
            "heights": heights.to_json(orient="split"),
        }

        return children, json.dumps(peak_metadata)
    else:
        return None, None


@app.callback(
    Output("differences-table", "children"),
    Input("differences-table-storage", "data"),
    [Input("{}-threshold".format(i), "value") for i in ["position", "fwhm", "height"]],
)
def get_peak_metadata_from_storage(peak_metadata, p, f, h):
    d = json.loads(peak_metadata)
    positions = pd.read_json(
        d["positions"],
        orient="split",
    )
    fwhms = pd.read_json(d["fwhms"], orient="split")
    heights = pd.read_json(d["heights"], orient="split")

    positions = positions.round(2)
    fwhms = fwhms.round(2)
    heights = fwhms.round(2)

    title_row1 = html.H4("Positions", className="mt-3 mb-3")
    title_row2 = html.H4("FWHMs", className="mt-3 mb-3")
    title_row3 = html.H4("Heights", className="mt-3 mb-3")

    fig_row1 = dbc.Row(
        dbc.Col(dcc.Graph(figure=make_fig_for_diff_tables(positions, p)), width=12),
        align="center",
    )
    fig_row2 = dbc.Row(
        dbc.Col(dcc.Graph(figure=make_fig_for_diff_tables(fwhms, f)), width=12),
        align="center",
    )
    fig_row3 = dbc.Row(
        dbc.Col(dcc.Graph(figure=make_fig_for_diff_tables(heights, h)), width=12),
        align="center",
    )

    row1 = dbc.Row(
        dbc.Col(
            dash_table.DataTable(
                columns=[{"name": i, "id": i} for i in positions.columns],
                data=positions.to_dict("records"),
                style_data_conditional=([ALTERNATE_ROW_HIGHLIGHTING]),
                style_header=TABLE_HEADER,
            ),
            width=12,
        ),
        align="center",
    )
    row2 = dbc.Row(
        dbc.Col(
            dash_table.DataTable(
                columns=[{"name": i, "id": i} for i in fwhms.columns],
                data=fwhms.to_dict("records"),
                style_data_conditional=([ALTERNATE_ROW_HIGHLIGHTING]),
                style_header=TABLE_HEADER,
            ),
            width=12,
        ),
        align="center",
    )
    row3 = dbc.Row(
        dbc.Col(
            dash_table.DataTable(
                columns=[{"name": i, "id": i} for i in heights.columns],
                data=heights.to_dict("records"),
                style_data_conditional=([ALTERNATE_ROW_HIGHLIGHTING]),
                style_header=TABLE_HEADER,
            ),
            width=12,
        ),
        align="center",
    )
    return [
        title_row1,
        fig_row1,
        row1,
        title_row2,
        fig_row2,
        row2,
        title_row3,
        fig_row3,
        row3,
    ]


@app.callback(
    [Output("{}-threshold".format(i), "value") for i in ["position", "fwhm", "height"]],
    [Input("reference-table", "data")],
)
def change_threshold(data):
    ref_df = json.loads(data)
    ref_df = pd.read_json(ref_df["reference"], orient="split").drop("Parameter", axis=1)
    _, f, h = np.round((ref_df.max(axis=1).values / 10.0), 2)
    p = 3.0
    return p, f, h


if __name__ == "__main__":
    app.run_server(debug=True)