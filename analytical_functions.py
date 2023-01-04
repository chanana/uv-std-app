import numpy as np
import pandas as pd
from scipy.signal import find_peaks, peak_widths


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


def calculate_ref_table_and_differences(peaks, heights, fwhm, ref_df=None):
    """Generate sample table and table with differences from reference sample

    Args:
        peaks (numpy.ndarray): 1D vector of peak positions
        heights (numpy.ndarray): 1D vector of peak heights
        fwhm (numpy.ndarray): 1D vector of peak widths at half maximum height
        ref_df (pandas.DataFrame): table of Peaks, Heights, FWHM of reference sample

    Returns:
        two pandas DataFrames:
        1. Sample
        2. Differences; where each cell is "sample[i,j] / difference[i,j]"
    """
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
