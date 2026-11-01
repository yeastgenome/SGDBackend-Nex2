"""log2 ratios for expression values, shared by load_expression_data.py and
fix_log_scale_log_ratios.py.

2-channel PCL files hold log2 ratios ('ratio'), except a few that hold
intensities instead ('log': no negative values and a median >=
TWO_CHANNEL_INTENSITY_MEDIAN; the 3 such datasets in SGD, GSE26617, GSE26618
and GSE33971, have medians 27-28, while all 366 ratio datasets have
|median| <= 1.62). 1-channel PCL files hold one of:
  - 'ratio':  log ratios already (each sample against a reference): stored
              as is, like 2-channel values
  - 'log':    log2 intensities (or rates): ratio = value - mean of the gene's
              row, since taking log2 of log2 values compresses the ratios
              towards 0 (the 2017 rule did that for ~300 datasets)
  - 'linear': linear intensities: ratio = log2(value / mean of the positive
              values in the gene's row), 0 when the value is <= 0 (2017 rule)

Classification (calibrated on the 323 single-channel datasets in SGD, 2026-10):
  - negative values in >= LOG_SCALE_NEGATIVE of the values, the median
    |sample mean| <= RATIO_CENTER (every sample centred on 0: the 10 such
    datasets <= 0.034, other log datasets with negatives >= 0.192), and little
    gene-specific level, i.e. removing each gene's mean leaves at least
    RATIO_GENE_SPREAD of the spread: 'ratio' (8 datasets, 0.88-1.00; centred
    log intensities, where abundant genes stay high in every sample, keep
    0.17-0.39, e.g. Caba_2005, Rudra_2005, GSE28213's GPL14666 file)
  - otherwise negative values: 'log'
  - all values < LOG_SCALE_MAX and median >= LOG_SCALE_MEDIAN: 'log' (log
    datasets: medians >= 2.04, maxima <= 28.6)
  - otherwise 'linear' (linear datasets centre on 1, medians 0.85-1.03, or
    run into the thousands, maxima >= 3,884)
A spread criterion (p90/p10) was tried and rejected: log2 data with a tail
near 0 looks wide.
"""
import math

LOG_SCALE_MAX = 100
LOG_SCALE_MEDIAN = 1.5
LOG_SCALE_NEGATIVE = 0.01
RATIO_CENTER = 0.1
RATIO_GENE_SPREAD = 0.7
TWO_CHANNEL_INTENSITY_MEDIAN = 5

RATIO = 'ratio'
LOG = 'log'
LINEAR = 'linear'


class ValueScale:
    """Summary of one file's (or dataset's) values, built row by row (a row is
    a gene's values across the samples). Per-sample (column) means are kept to
    recognise files that are already centred ratios."""

    def __init__(self, count=0, negative=0, at_least_median=0, maximum=float('-inf'), sample_means=None,
                 gene_spread=None, at_least_intensity=0):
        self.count = count
        self.negative = negative
        self.at_least_median = at_least_median
        self.at_least_intensity = at_least_intensity
        self.max = maximum
        self._sample_means = sample_means
        self._gene_spread = gene_spread
        self.column_sums = []
        self.column_counts = []
        self.total = 0.0
        self.total_squares = 0.0
        self.within_gene_squares = 0.0

    def add_row(self, values):
        if len(self.column_sums) < len(values):
            grow = len(values) - len(self.column_sums)
            self.column_sums += [0.0] * grow
            self.column_counts += [0] * grow
        present = [v for v in values if v is not None]
        mean = sum(present) / len(present) if present else 0.0
        for i, v in enumerate(values):
            if v is None:
                continue
            self.count += 1
            self.negative += v < 0
            self.at_least_median += v >= LOG_SCALE_MEDIAN
            self.at_least_intensity += v >= TWO_CHANNEL_INTENSITY_MEDIAN
            self.max = max(self.max, v)
            self.column_sums[i] += v
            self.column_counts[i] += 1
            self.total += v
            self.total_squares += v * v
            self.within_gene_squares += (v - mean) ** 2

    def sample_means(self):
        if self._sample_means is not None:
            return self._sample_means
        return [s / n for s, n in zip(self.column_sums, self.column_counts) if n]

    def gene_spread(self):
        """SD after removing each gene's mean / overall SD (1 = no gene-specific level)."""
        if self._gene_spread is not None:
            return self._gene_spread
        variance = self.total_squares / self.count - (self.total / self.count) ** 2
        return math.sqrt(self.within_gene_squares / self.count / variance) if variance > 0 else 0.0

    def kind(self, channel_count=1):
        if channel_count == 2:
            intensities = (self.count and self.negative < LOG_SCALE_NEGATIVE * self.count
                           and 2 * self.at_least_intensity >= self.count)
            return LOG if intensities else RATIO
        if not self.count:
            return LINEAR
        if self.negative >= LOG_SCALE_NEGATIVE * self.count:
            centres = sorted(abs(m) for m in self.sample_means())
            if centres and centres[len(centres) // 2] <= RATIO_CENTER and self.gene_spread() >= RATIO_GENE_SPREAD:
                return RATIO
            return LOG
        if self.max <= LOG_SCALE_MAX and 2 * self.at_least_median >= self.count:
            return LOG
        return LINEAR


def row_mean(values, scale):
    """Mean of a gene's PCL row: all values for log-scale files, the positive
    values for linear files (as in 2017); not used for ratio files."""
    present = [x for x in values if x is not None]
    if scale == LOG:
        return sum(present) / len(present) if present else 0.0
    positive = [x for x in present if x > 0]
    return sum(positive) / len(positive) if positive else 0.0


def log_ratio(value, mean, channel_count, scale):
    """log2 ratio of a value, rounded to 2 decimals (see the module docstring).
    channel_count only matters for callers that do not classify 2-channel
    files: their values are then taken as ratios."""
    if scale == RATIO or (channel_count == 2 and scale != LOG):
        return value
    if scale == LOG:
        return round(value - mean, 2)
    if value <= 0 or mean <= 0:
        return 0.0
    return round(math.log(value / mean, 2), 2)
