import tempfile
import unittest
from pathlib import Path

from downloader import DATASUSDownloader, DownloadSummary


class FakeFTP:
    def __init__(self, files, fail_on=None):
        self.files = files
        self.fail_on = fail_on

    def nlst(self, pattern=None):
        return list(self.files)

    def size(self, filename):
        return len(self.files[filename])

    def retrbinary(self, command, callback, blocksize=8192):
        filename = command.split(" ", 1)[1]
        if filename == self.fail_on:
            raise OSError("falha simulada")
        data = self.files[filename]
        for offset in range(0, len(data), blocksize):
            callback(data[offset : offset + blocksize])

    def quit(self):
        pass


class DownloaderTests(unittest.TestCase):
    def make_downloader(self, files, fail_on=None):
        downloader = DATASUSDownloader()
        downloader.ftp = FakeFTP(files, fail_on=fail_on)
        return downloader

    def test_discovers_periods_and_ignores_unrelated_files(self):
        downloader = self.make_downloader(
            {
                "PASP2501a.dbc": b"a",
                "PASP2501b.dbc": b"b",
                "PASP2605a.dbc": b"c",
                "PAAB2605.dbc": b"x",
            }
        )
        self.assertEqual(
            downloader.list_available_periods(),
            [("2025", "01"), ("2026", "05")],
        )

    def test_discovers_periods_for_each_sihsus_type(self):
        downloader = self.make_downloader(
            {
                "RDSP2512.dbc": b"rd-antigo",
                "RDSP2602.dbc": b"rd-atual",
                "SPSP2601.dbc": b"sp-atual",
                "RDRJ2603.dbc": b"outra-uf",
            }
        )
        self.assertEqual(
            downloader.list_available_periods("RD", "SP"),
            [("2025", "12"), ("2026", "02")],
        )
        self.assertEqual(
            downloader.list_available_periods("SP", "SP"), [("2026", "01")]
        )

    def test_download_uses_partial_file_and_reports_categories(self):
        files = {
            "PASP2601a.dbc": b"conteudo-a",
            "PASP2601b.dbc": b"conteudo-b",
            "PASP2601c.dbc": b"conteudo-c",
        }
        downloader = self.make_downloader(files, fail_on="PASP2601c.dbc")

        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            destination = base / "2026" / "01"
            destination.mkdir(parents=True)
            (destination / "PASP2601b.dbc").write_bytes(files["PASP2601b.dbc"])

            summary = downloader.download_monthly_files("2026", "01", base)

            self.assertEqual(
                summary,
                DownloadSummary(downloaded=1, existing=1, failed=1),
            )
            self.assertEqual(
                (destination / "PASP2601a.dbc").read_bytes(), files["PASP2601a.dbc"]
            )
            self.assertFalse((destination / "PASP2601c.dbc").exists())
            self.assertFalse((destination / "PASP2601c.dbc.part").exists())

    def test_replaces_local_file_when_size_differs(self):
        files = {"PASP2601a.dbc": b"arquivo-completo"}
        downloader = self.make_downloader(files)

        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            destination = base / "2026" / "01"
            destination.mkdir(parents=True)
            target = destination / "PASP2601a.dbc"
            target.write_bytes(b"parcial")

            summary = downloader.download_monthly_files("2026", "01", base)

            self.assertEqual(summary.downloaded, 1)
            self.assertEqual(summary.unavailable, 0)
            self.assertEqual(target.read_bytes(), files["PASP2601a.dbc"])

    def test_downloads_every_pasp_part_published_for_selected_month(self):
        files = {
            "PASP2602a.dbc": b"a",
            "PASP2602c.dbc": b"c",
            "PASP2602e.dbc": b"e",
            "PASP2603a.dbc": b"outro-mes",
        }
        downloader = self.make_downloader(files)

        with tempfile.TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory)
            summary = downloader.download_monthly_files("2026", "02", destination)

            self.assertEqual(summary, DownloadSummary(downloaded=3))
            downloaded = {path.name for path in (destination / "2026" / "02").iterdir()}
            self.assertEqual(
                downloaded, {"PASP2602a.dbc", "PASP2602c.dbc", "PASP2602e.dbc"}
            )

    def test_rejects_invalid_period(self):
        downloader = self.make_downloader({})
        with self.assertRaises(ValueError):
            downloader.download_monthly_files("26", "01")
        with self.assertRaises(ValueError):
            downloader.download_monthly_files("2026", "13")

    def test_downloads_single_sihsus_file_in_its_own_category(self):
        files = {"RDSP2602.dbc": b"aih-reduzida"}
        downloader = self.make_downloader(files)

        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            summary = downloader.download_sihsus_file("RD", "2026", "02", "SP", base)

            self.assertEqual(summary, DownloadSummary(downloaded=1))
            self.assertEqual(
                (base / "RD" / "2026" / "02" / "RDSP2602.dbc").read_bytes(),
                files["RDSP2602.dbc"],
            )

    def test_sigtap_discovers_competence_and_downloads_latest_version(self):
        latest = "TabelaUnificada_202610_v2610271043.zip"
        downloader = self.make_downloader({
            latest: b"zip-atual",
            "TabelaUnificada_202610_v2610011000.zip": b"zip-antigo",
            "TabelaUnificada_202609_v2610261311.zip": b"outro-mes",
            "TabelaUnificada_202613_v2610271043.zip": b"mes-invalido",
            "outro.zip": b"outro",
        })
        self.assertEqual(downloader.list_available_periods("SIGTAP"),
                         [("2026", "09"), ("2026", "10")])
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            target = base / "SIGTAP" / "2026" / "10" / latest
            self.assertEqual(downloader.download_sigtap_file("2026", "10", base),
                             DownloadSummary(downloaded=1))
            self.assertEqual(target.read_bytes(), b"zip-atual")
            self.assertEqual(len(list(target.parent.iterdir())), 1)
            self.assertEqual(downloader.download_sigtap_file("2026", "10", base),
                             DownloadSummary(existing=1))
            target.write_bytes(b"parcial")
            self.assertEqual(downloader.download_sigtap_file("2026", "10", base),
                             DownloadSummary(downloaded=1))

    def test_sigtap_unavailable_and_failed_download(self):
        filename = "TabelaUnificada_202610_v2610271043.zip"
        downloader = self.make_downloader({filename: b"zip"}, fail_on=filename)
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            self.assertEqual(downloader.download_sigtap_file("2026", "11", base),
                             DownloadSummary(unavailable=1))
            self.assertEqual(downloader.download_sigtap_file("2026", "10", base),
                             DownloadSummary(failed=1))
            self.assertFalse(list(base.rglob("*.part")))
            self.assertFalse(list(base.rglob("*.zip")))
        with self.assertRaises(ValueError):
            downloader.download_sigtap_file("26", "10")
        with self.assertRaises(ValueError):
            downloader.download_sigtap_file("2026", "13")

    def test_reports_unavailable_sihsus_file(self):
        downloader = self.make_downloader({})
        with tempfile.TemporaryDirectory() as temporary_directory:
            summary = downloader.download_sihsus_file(
                "SP", "2026", "02", "SP", Path(temporary_directory)
            )
        self.assertEqual(summary, DownloadSummary(unavailable=1))


if __name__ == "__main__":
    unittest.main()
