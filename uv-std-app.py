import itertools
import json

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import numpy as np
import pandas as pd
from dash.dependencies import Input, Output, State

from constants import ALTERNATE_ROW_HIGHLIGHTING, TABLE_HEADER, THRESHOLD_POSITION
from functions import (
    find_peaks_scipy,
    make_spectrum_with_picked_peaks,
    parse_contents,
    make_sample_info_card,
    make_fig_for_diff_tables,
    make_dash_table_from_dataframe,
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
                    children=dbc.Button(
                        "Upload a reference file", color="primary", block=True
                    ),
                ),
                width=12,
            ),
            align="center",
            className="mt-3 mb-3",
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
                    children=dbc.Button(
                        "Upload files to compare with reference file",
                        color="primary",
                        block=True,
                    ),
                ),
            ),
            className="mt-3 mb-3",
        ),
        dbc.Row(
            children=[
                dbc.Col(
                    [
                        html.H5("{} Threshold ".format(k[0].upper() + k[1::])),
                        dbc.Input(
                            id="{}-threshold".format(k),
                            type="number",
                            placeholder="{} threshold".format(k[0].upper() + k[1::]),
                            step=0.01,
                        ),
                    ],
                    width=4,
                    align="center",
                )
                for k in ["position", "fwhm", "height"]
            ],
            align="center",
            className="mt-3 mb-3",
            justify="center",
        ),
        dcc.Store(id="differences-table-storage"),
        html.Div(id="differences-table"),
    ],
)

tab3 = dbc.Tab(
    label="Details",
    id="tab-3",
    children=[
        html.Div(id="samples-uploaded"),
    ],
)
app.layout = dbc.Container(dbc.Tabs(children=[tab1, tab2, tab3], className="nav-fill"))


def calculate_ref_table_and_differences(peaks, heights, fwhm, ref_df=None):
    df = pd.DataFrame(index=["Position", "Height", "FWHM"])
    df["Parameter"] = ["Position (s)", "Height", "FWHM (s)"]
    for i in range(len(peaks)):
        df["Peak " + str(i + 1)] = [peaks[i] / 10.0, heights[i], fwhm[i] / 10.0]

    if ref_df is None:
        diff = None
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

    data_table, differences = calculate_ref_table_and_differences(
        peaks, heights, fwhm, ref_df
    )
    return info_card, fig, data_table, differences


# def put_tab_3_into_html(info_card, figure, data_table, width_col_1=3, width_col_2=9):
#     col1 = dbc.Col(info_card, width=width_col_1)
#     col2 = dbc.Col(dcc.Graph(figure=figure), width=width_col_2)
#     row1 = dbc.Row(children=[col1, col2], align="center")
#     row2 = make_dash_table_from_dataframe(table=data_table, with_slash=3)
#     print(row2)
#
#     return [row1, row2]


def put_tab_2_into_html(
    positions, threshold_position, fwhms, threshold_fwhm, heights, threshold_height
):
    titles = [
        html.H4("{}".format(i), className="mt-3 mb-3")
        for i in ["Positions", "FWHMs", "Heights"]
    ]
    figures = [
        dbc.Row(dbc.Col(dcc.Graph(figure=fig), width=12), align="center")
        for fig in map(
            make_fig_for_diff_tables,
            [positions, fwhms, heights],
            [threshold_position, threshold_fwhm, threshold_height],
        )
    ]
    tables = [
        table
        for table in map(
            make_dash_table_from_dataframe,
            [positions, fwhms, heights],  # table value
            [2, 2, 2],  # with_slash value
            [threshold_position, threshold_fwhm, threshold_height],  # threshold value
        )
    ]

    # this returns a list consisting of [title[0], figures[0], tables[0], title[1], ...]
    return [
        i
        for i in itertools.chain.from_iterable(
            itertools.zip_longest(titles, figures, tables)
        )
    ]


@app.callback(
    Output("reference-row", "children"),
    Output("reference-table", "data"),
    Input("upload-data", "contents"),
    State("upload-data", "filename"),
)
def update_output_tab_1(contents, filename):
    if contents is not None:
        info_card, fig, data_table, diff = get_file_contents_and_analyze(
            contents, filename
        )
        data = {"reference": data_table.to_json(orient="split")}
        col1 = dbc.Col(info_card, width=3)
        col2 = dbc.Col(dcc.Graph(figure=fig), width=9)
        row1 = dbc.Row(children=[col1, col2], align="center")
        row2 = make_dash_table_from_dataframe(table=data_table, with_slash=1)
        return [row1, row2], json.dumps(data)


@app.callback(
    Output("samples-uploaded", "children"),
    Output("differences-table-storage", "data"),
    Input("upload-data-multiple", "contents"),
    Input("reference-table", "data"),
    [Input("{}-threshold".format(i), "value") for i in ["position", "fwhm", "height"]],
    State("upload-data-multiple", "filename"),
)
def update_output_tab_3(
    contents, data, threshold_position, threshold_fwhm, threshold_height, filename
):
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
            col1 = dbc.Col(info_card, width=3)
            col2 = dbc.Col(dcc.Graph(figure=fig), width=9)
            row1 = dbc.Row(children=[col1, col2], align="center")
            row2 = make_dash_table_from_dataframe(
                table=data_table,
                with_slash=3,
                threshold_position=threshold_position,
                threshold_fwhm=threshold_fwhm,
                threshold_height=threshold_height,
            )

            children += [row1, row2]

            positions = positions.append(diff.iloc[[0]])
            fwhms = fwhms.append(diff.iloc[[1]])
            heights = heights.append(diff.iloc[[2]])

        peak_metadata = {
            "positions": positions.to_json(orient="split"),
            "fwhms": fwhms.to_json(orient="split"),
            "heights": heights.to_json(orient="split"),
        }

        return children, json.dumps(peak_metadata)


@app.callback(
    Output("differences-table", "children"),
    Input("differences-table-storage", "data"),
    [Input("{}-threshold".format(i), "value") for i in ["position", "fwhm", "height"]],
)
def get_peak_metadata_from_storage(
    metadata, threshold_position, threshold_fwhm, threshold_height
):
    metadata = json.loads(metadata)
    positions = pd.read_json(
        metadata["positions"],
        orient="split",
    )
    fwhms = pd.read_json(metadata["fwhms"], orient="split")
    heights = pd.read_json(metadata["heights"], orient="split")

    positions = positions.round(2)
    fwhms = fwhms.round(2)
    heights = heights.round(2)

    return put_tab_2_into_html(
        positions, threshold_position, fwhms, threshold_fwhm, heights, threshold_height
    )


@app.callback(
    [Output("{}-threshold".format(i), "value") for i in ["position", "fwhm", "height"]],
    [Input("reference-table", "data")],
)
def calculate_thresholds(data):
    ref_df = json.loads(data)
    ref_df = pd.read_json(ref_df["reference"], orient="split").drop("Parameter", axis=1)
    _, threshold_fwhm, threshold_height = np.round(
        (ref_df.max(axis=1).values / 10.0), 2
    )
    threshold_position = THRESHOLD_POSITION
    return threshold_position, threshold_height, threshold_fwhm


if __name__ == "__main__":
    # app.run_server(debug=True)
    app.run_server()
