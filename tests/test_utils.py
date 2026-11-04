import unittest

from utils import format_bytes_to_mb, generate_filename, generate_sihsus_filename


class UtilsTests(unittest.TestCase):
    def test_formats_megabytes(self):
        self.assertEqual(format_bytes_to_mb(1_048_576), "1.00 MB")

    def test_generates_pasp_filename(self):
        self.assertEqual(generate_filename("2026", "05", "c"), "PASP2605c.dbc")

    def test_generates_sihsus_filenames_for_sao_paulo(self):
        self.assertEqual(
            generate_sihsus_filename("RD", "2026", "02"), "RDSP2602.dbc"
        )
        self.assertEqual(
            generate_sihsus_filename("SP", "2026", "02"), "SPSP2602.dbc"
        )


if __name__ == "__main__":
    unittest.main()
