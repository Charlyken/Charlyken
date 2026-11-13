import datetime as dt
import importlib.util
import io
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "scripts" / "generate-commits-chart.py"


class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def load_generator():
    spec = importlib.util.spec_from_file_location("generate_commits_chart", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    fake_html = b"<html><body></body></html>"
    with tempfile.TemporaryDirectory() as directory:
        previous = os.getcwd()
        os.chdir(directory)
        try:
            with mock.patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}), mock.patch(
                "urllib.request.urlopen", return_value=_FakeResponse(fake_html)
            ):
                spec.loader.exec_module(module)
        finally:
            os.chdir(previous)
    return module


GENERATOR = load_generator()


class ContributionCalendarTests(unittest.TestCase):
    def test_y_axis_uses_whole_contribution_steps_for_small_counts(self):
        self.assertEqual(GENERATOR.nice_step(1), 1)
        self.assertEqual(GENERATOR.nice_step(4), 1)

    def test_utc_date_follows_github_calendar_around_paris_midnight(self):
        utc_date = getattr(GENERATOR, "utc_date", lambda _now: None)
        paris = dt.timezone(dt.timedelta(hours=1))

        result = utc_date(dt.datetime(2026, 11, 1, 0, 30, tzinfo=paris))

        self.assertEqual(result, dt.date(2026, 10, 31))

    def test_build_days_crosses_month_boundary_with_31_dates(self):
        build_days = getattr(GENERATOR, "build_days", lambda _today: [])

        result = build_days(dt.date(2026, 11, 1))

        self.assertEqual(len(result), 31)
        self.assertEqual(result[0], dt.date(2026, 10, 2))
        self.assertEqual(result[-1], dt.date(2026, 11, 1))

    def test_extract_counts_preserves_zero_contribution_days(self):
        extract_counts = getattr(GENERATOR, "extract_counts", lambda _payload, _days: {})
        days = [dt.date(2026, 10, 31), dt.date(2026, 11, 1)]
        payload = {
            "data": {
                "user": {
                    "contributionsCollection": {
                        "contributionCalendar": {
                            "weeks": [
                                {
                                    "contributionDays": [
                                        {"date": "2026-10-31", "contributionCount": 0},
                                        {"date": "2026-11-01", "contributionCount": 4},
                                    ]
                                }
                            ]
                        }
                    }
                }
            }
        }

        result = extract_counts(payload, days)

        self.assertEqual(result, {"2026-10-31": 0, "2026-11-01": 4})

    def test_extract_counts_rejects_incomplete_calendar(self):
        extract_counts = getattr(GENERATOR, "extract_counts", lambda _payload, _days: {})
        days = [dt.date(2026, 10, 31), dt.date(2026, 11, 1)]
        payload = {
            "data": {
                "user": {
                    "contributionsCollection": {
                        "contributionCalendar": {
                            "weeks": [
                                {
                                    "contributionDays": [
                                        {"date": "2026-10-31", "contributionCount": 2}
                                    ]
                                }
                            ]
                        }
                    }
                }
            }
        }

        with self.assertRaisesRegex(ValueError, "Données incomplètes"):
            extract_counts(payload, days)

    def test_build_svg_uses_real_dates_and_keeps_points_inside_chart(self):
        build_svg = getattr(GENERATOR, "build_svg", lambda _days, _counts: "")
        days = [
            dt.date(2026, 10, 30),
            dt.date(2026, 10, 31),
            dt.date(2026, 11, 1),
        ]
        counts = {"2026-10-30": 0, "2026-10-31": 4, "2026-11-01": 123}

        svg = build_svg(days, counts)

        self.assertIn(">30/10</text>", svg)
        self.assertIn(">31/10</text>", svg)
        self.assertIn(">01/11</text>", svg)
        y_values = [float(value) for value in re.findall(r'<circle[^>]+cy="([0-9.]+)"', svg)]
        self.assertEqual(len(y_values), 3)
        self.assertTrue(all(100 <= value <= 437 for value in y_values))
        self.assertIn(437.0, y_values)


if __name__ == "__main__":
    unittest.main()
