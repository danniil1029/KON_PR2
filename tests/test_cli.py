"""Проверки параметров командной строки."""

import contextlib
import io
import unittest

from src.main import DEFAULT_SOURCE, parse_args

USAGE_ERROR = 2


class CliTests(unittest.TestCase):
    """Проверить правильные и неправильные параметры."""

    def test_defaults(self):
        """Прочитать настройки обычного запуска."""
        args = parse_args(["--package", "Example.Package"])
        self.assertEqual(args.repo, DEFAULT_SOURCE)
        self.assertEqual(args.output.name, "graph.svg")
        self.assertFalse(args.tree)
        self.assertFalse(args.test)

    def test_invalid_options(self):
        """Проверить диагностику для каждого параметра из задания."""
        cases = [
            (["--package", "bad name"], "--package"),
            (["--repo", "not-a-url"], "--repo"),
            (["--repo="], "--repo"),
            (["--test", "true"], "unrecognized arguments"),
            (["--test"], "--repo"),
            (["--output", "graph.png"], "--output"),
            (["--output", "missing-folder/graph.svg"], "--output"),
            (["--tree", "true"], "unrecognized arguments"),
            (["--depth", "-1"], "--depth"),
            (["--depth", "one"], "--depth"),
            (["--exclude="], "--exclude"),
            (["--version", "invalid"], "--version"),
            (["--framework="], "--framework"),
        ]
        for options, expected in cases:
            with self.subTest(options=options):
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    with self.assertRaises(SystemExit) as error:
                        parse_args(["--package", "A", *options])
                self.assertEqual(error.exception.code, USAGE_ERROR)
                self.assertIn(expected, stderr.getvalue())
