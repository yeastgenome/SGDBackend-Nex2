import math
import unittest

from scripts.loading.dataset.expression_value_scale import LINEAR, LOG, RATIO, ValueScale, log_ratio, row_mean


def kind_of(rows):
    """rows: a gene per row, a sample per column."""
    scale = ValueScale()
    for row in rows:
        scale.add_row(row)
    return scale.kind()


def column(values):
    return [[v] for v in values]


class ValueScaleTest(unittest.TestCase):

    def test_log2_intensities(self):
        # e.g. GSE20155: RMA-style log2 intensities, 7.5-13.7
        self.assertEqual(kind_of(column([7.49, 13.68, 12.68, 11.16, 12.05, 10.77])), LOG)

    def test_log2_with_high_baseline_or_low_tail(self):
        # e.g. GSE109435: values 16-29; GSE89875: median 6.8 with a tail near 0-1
        self.assertEqual(kind_of(column([16.8, 20.9, 24.3, 28.6, 21.0])), LOG)
        self.assertEqual(kind_of(column([0.2, 0.9, 6.5, 6.8, 7.4, 9.3, 11.8])), LOG)

    def test_low_log2_intensities(self):
        # e.g. GSE5938: median ~2, max 9.5
        self.assertEqual(kind_of(column([1.5, 1.9, 2.0, 2.1, 3.8, 9.5])), LOG)

    def test_shifted_log_values_with_negatives(self):
        # e.g. GSE72356-2 (GRO): samples centred around -1.8, not on 0
        rows = [[-7.6, -6.9], [-1.8, -2.0], [0.3, 0.1], [1.9, 1.5], [-0.7, -1.2]]
        self.assertEqual(kind_of(rows), LOG)

    def test_centred_ratios(self):
        # e.g. GSE124452: every sample centred on 0, no gene-specific level (ratios against a reference)
        rows = [[-0.30, 0.25, -0.1], [0.20, -0.15, 0.3], [0.10, -0.10, -0.2], [0.0, 0.0, 0.0]]
        self.assertEqual(kind_of(rows), RATIO)

    def test_centred_log_intensities_are_not_ratios(self):
        # e.g. Caba_2005, Rudra_2005: samples centred on 0, but abundant genes stay high in every sample
        rows = [[3.0, 3.1, 2.9], [-3.0, -2.9, -3.1], [0.5, 0.4, 0.6], [-0.5, -0.6, -0.4]]
        self.assertEqual(kind_of(rows), LOG)

    def test_linear_intensities(self):
        self.assertEqual(kind_of(column([120.0, 4500.0, 980.0, 33.5, 15000.0])), LINEAR)

    def test_linear_values_near_one(self):
        # fold-change-like linear values centred on 1 (e.g. GSE4136, GSE61244)
        self.assertEqual(kind_of(column([0.4, 1.1, 0.9, 2.3, 1.0, 0.05, 6.0])), LINEAR)
        self.assertEqual(kind_of(column([0.65, 0.8, 1.0, 1.1, 1.4, 30.4])), LINEAR)

    def test_missing_values_and_empty(self):
        self.assertEqual(kind_of([[None, 8.0], [9.0, None]]), LOG)
        self.assertEqual(ValueScale().kind(), LINEAR)

    def test_from_database_counts(self):
        self.assertEqual(ValueScale(100, 0, 90, 28.6).kind(), LOG)
        self.assertEqual(ValueScale(100, 0, 90, 3884).kind(), LINEAR)
        self.assertEqual(ValueScale(100, 0, 40, 19.5).kind(), LINEAR)
        self.assertEqual(ValueScale(100, 45, 10, 2.3, sample_means=[0.01, -0.02, 0.03], gene_spread=0.93).kind(), RATIO)
        self.assertEqual(ValueScale(100, 45, 10, 2.3, sample_means=[0.01, -0.02, 0.03], gene_spread=0.37).kind(), LOG)
        self.assertEqual(ValueScale(100, 45, 10, 5.3, sample_means=[0.19, -0.2, 0.25], gene_spread=0.95).kind(), LOG)


class LogRatioTest(unittest.TestCase):

    def test_two_channel_and_ratio_values_are_kept(self):
        self.assertEqual(log_ratio(-1.234, 5.0, 2, LINEAR), -1.234)
        self.assertEqual(log_ratio(-0.31, 0.0, 1, RATIO), -0.31)

    def test_linear_rule_unchanged(self):
        values = [100.0, 400.0, None, -5.0]
        mean = row_mean(values, LINEAR)          # mean of the positive values
        self.assertEqual(mean, 250.0)
        self.assertEqual(log_ratio(400.0, mean, 1, LINEAR), round(math.log(400 / 250, 2), 2))
        self.assertEqual(log_ratio(-5.0, mean, 1, LINEAR), 0.0)

    def test_log_scale_ratio_is_difference_from_row_mean(self):
        values = [13.68, 12.68, None, 11.68]
        mean = row_mean(values, LOG)             # all present values, negatives included
        self.assertAlmostEqual(mean, 12.68)
        self.assertEqual(log_ratio(13.68, mean, 1, LOG), 1.0)   # 2-fold up, not ~0.01
        self.assertEqual(log_ratio(11.68, mean, 1, LOG), -1.0)
        self.assertEqual(log_ratio(-2.0, row_mean([-2.0, 2.0], LOG), 1, LOG), -2.0)


if __name__ == '__main__':
    unittest.main()
