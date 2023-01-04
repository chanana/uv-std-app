import base64
import itertools
import json

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import numpy as np

from analytical_functions import calculate_ref_table_and_differences, find_peaks_scipy
from constants import ALTERNATE_ROW_HIGHLIGHTING, TABLE_HEADER
from figure_functions import make_fig_for_diff_tables, make_spectrum_with_picked_peaks


def parse_contents(contents):
    """Parse contents of uploaded file to json-string

    Args:
        contents (str): contents of an uploaded file

    Returns:
        json-decoded string of contents
    """
    content_type, content_string = contents.split(",")
    decoded = base64.b64decode(content_string)
    j = json.loads(decoded)
    return j


def get_file_contents_and_analyze(content, filename, ref_df=None):
    """Generate dash components from peak, sample info

    Args:
        content (str): contents of an uploaded file
        filename (str): name of an uploaded file
        ref_df (pd.DataFrame): reference sample data

    Returns: tuple of sample information as html, plotly figure, dataframe of sample,
        dataframe of difference between reference and sample
    """
    j = parse_contents(content)
    x = np.array(j["time"][:6000])
    y = np.array(j["intensities"]["254"][:6000])
    peaks, heights, fwhm, hm, leftips, rightips = find_peaks_scipy(y, height=0.1)

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


def put_tab_2_into_html(
    positions, threshold_position, fwhms, threshold_fwhm, heights, threshold_height
):
    """Convert differences between samples and reference into dash html for tab 2

    Args:
        positions (pd.DataFrame): table of differences in peak positions for all samples
            compared to reference
        threshold_position (float): max absolute deviation allowed for position
        fwhms (pd.DataFrame): table of differences in peak Full-width-at half-maximums
            for all samples compared to reference
        threshold_fwhm (float): max absolute deviation allowed for FWHM
        heights (pd.DataFrame): table of differences in peak heights for all samples
            compared to reference
        threshold_height (float): max absolute deviation allowed for height

    Returns:
        list of dash html components consisting of a title, figure, and table of differences
        for all samples
    """
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


def make_dash_table_from_dataframe(
    table,
    with_slash=None,
    threshold=None,
    threshold_position=None,
    threshold_fwhm=None,
    threshold_height=None,
    style_data_conditional=None,
    style_header=TABLE_HEADER,
):
    """Render a dash_table with highlights based on thresholds supplied

    Args:
        table (pd.DataFrame): table to be made into a dash table
        with_slash (int): takes value 1, 2, or 3 depending on which tab is rendering
            a table; see Notes for more details.
        threshold (float): generic threshold (see Notes)
        threshold_position (float): threshold for peak positions (default is 3s)
        threshold_fwhm (float): threshold for full-width-at-half-maximum
        threshold_height (float): threshold for the height of the peak
        style_data_conditional (dict): see formatting guide [here](
            https://dash.plotly.com/datatable/conditional-formatting)
        style_header (dict): formatting for the header row (similar to
            style_data_conditional)

    Returns:
        dash_table.DataTable (html string)

    Notes:
        with_slash: This can probably be made into something cleaner but for now,
    this is a good compromise on repeated code vs readability. If rendering a table
    from tab 1, it only applies a highlighting to alternate rows since this is only a
    reference file and we have no other files to compare to. If rendering tables in
    tab 2, it applies a conditional highlighting rule that is calculated separately
    for each table depending on the thresholds provided (arg threshold is used
    instead of the individual thresholds). Finally, if rendering tables in tab 3,
    the highlight rules incorporate splitting each cell's contents by the slash (/)
    and then comparing the right hand side with the suppled threshold.

    """
    if with_slash == 1:  # for table in tab 1
        style_data_conditional = [ALTERNATE_ROW_HIGHLIGHTING]
    elif with_slash == 3:  # for tables in tab 3
        style_data_conditional = [ALTERNATE_ROW_HIGHLIGHTING] + highlight_cells(
            table, threshold_position, threshold_fwhm, threshold_height
        )
    elif with_slash == 2:  # for tables in tab 2
        style_data_conditional = [
            ALTERNATE_ROW_HIGHLIGHTING
        ] + highlight_cells_without_slash(table, threshold)

    return dbc.Row(
        dbc.Col(
            dash_table.DataTable(
                columns=[{"name": i, "id": i} for i in table.columns],
                data=table.to_dict("records"),
                style_data_conditional=style_data_conditional,
                style_header=style_header,
            ),
            width=12,
        ),
        align="center",
    )


def highlight_cells(table, threshold_position, threshold_fwhm, threshold_height):
    """Highlight cells if rendering a table in tab 3

    Args:
        table (pd.DataFrame): the table to be rendered
        threshold_position (float): threshold for peak positions (default is 3s)
        threshold_fwhm (float): threshold for full-width-at-half-maximum
        threshold_height (float): threshold for the height of the peak

    Returns:
        highlighting rule (list of dict)
    """
    columns = table.filter(regex="Peak*").columns.to_list()
    return (
        hightlight_helper(table, threshold_position, ["Position"], columns)
        + hightlight_helper(table, threshold_height, ["Height"], columns)
        + hightlight_helper(table, threshold_fwhm, ["FWHM"], columns)
    )


def hightlight_helper(table, threshold, rows, columns):
    """Helper function to apply conditional highlighting for tab 3 tables

    Args:
        table (pd.DataFrame): the table to be rendered
        threshold (float): generic threshold
        rows (list): the row to apply highlighting to
        columns (list): the columns to apply the highlighting to

    Returns:
        list of dict of highlighting rules

    Notes:
        This is one big conditional expression ( https://stackoverflow.com/a/9987533)
        and sort of looks like a list comprehension but it's not. I've used an
        additional helper function to return the various parts of the list to make
        the code more readable.
    """
    highlight = [
        {
            "if": {
                "column_id": col,
                "filter_query": '{{Parameter}} contains "{}"'.format(row),
            },
            "color": "tomato",
            "fontWeight": "bold",
        }
        if abs(float(str(table.loc[row, col]).split("/")[1])) >= threshold
        else {}
        for col in columns
        for i, row in enumerate(rows)
    ]

    return highlight


def highlight_cells_without_slash(table, threshold):
    """Helper function for tab 2 highlighting

    Args:
        table (pd.DataFrame): table being highlighted
        threshold (float): generic threshold to compare each cell against

    Returns:
        list of dict of highlight rules
    """
    highlight = [
        {
            "if": {
                "column_id": col,
                "row_index": r,
            },
            "color": "tomato",
            "fontWeight": "bold",
        }
        if abs(float(table.iloc[r, c])) >= threshold
        else {}
        for c, col in enumerate(table.columns)
        for r, row in enumerate(table.index)
    ]
    return highlight
