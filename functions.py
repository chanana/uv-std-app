from scipy.signal import find_peaks, peak_widths


def find_peaks_scipy(x, height=None):
    """Find peaks in given 1D vector

    Args:
        x (numpy.ndarray): 1D vector of the y values of a waveform
        height ([float], optional): The minimum height required to be considered a
        peak. If no height is specified, it is taken as 10% of the maximum value in x.
        Defaults to None.
    """
    if height is None:
        height = 0.1 * max(x)

    peaks, heights = find_peaks(x=x, height=height)
    heights = heights['peak_heights']
    # fwhm = full width at half max (width of the peak at specified height)
    # hm = half max (height at which fwhm was found),
    # leftips, rightips = intersection on x axis for y=hm
    fwhm, hm, leftips, rightips = peak_widths(x=x, peaks=peaks, rel_height=0.95)

    return peaks, heights, fwhm, hm, leftips, rightips