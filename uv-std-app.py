import json

import dash
import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
from dash import dcc, html
from dash.dependencies import Input, Output, State

from constants import THRESHOLD_POSITION
from html_functions import (
    get_file_contents_and_analyze,
    make_dash_table_from_dataframe,
    put_tab_2_into_html,
)

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.SANDSTONE],
    prevent_initial_callbacks=True,
)

# contains the reference file
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

# shows overall summary graphs of deviations from reference file
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

# shows details for each file uploaded including peaks picked and individual deviations
tab3 = dbc.Tab(
    label="Details",
    id="tab-3",
    children=[
        html.Div(id="samples-uploaded"),
    ],
)
app.layout = dbc.Container(dbc.Tabs(children=[tab1, tab2, tab3], className="nav-fill"))


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

    else:
        return [], {}


@app.callback(
    Output("differences-table", "children"),
    Input("differences-table-storage", "data"),
    [Input("{}-threshold".format(i), "value") for i in ["position", "fwhm", "height"]],
)
def get_peak_metadata_from_storage(
    metadata, threshold_position, threshold_fwhm, threshold_height
):
    if metadata == {}:
        return []
    else:
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
            positions,
            threshold_position,
            fwhms,
            threshold_fwhm,
            heights,
            threshold_height,
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
    app.run_server(host="0.0.0.0")
