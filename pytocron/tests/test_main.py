# Copyright (c) 2025 Sebastian Pipping <sebastian@pipping.org>
#
# Licensed under GNU Affero General Public License v3.0 or later
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import signal
from io import StringIO
from tempfile import NamedTemporaryFile
from unittest import TestCase
from unittest.mock import patch

from parameterized import parameterized

from .._logging import LOG_LEVELS
from .._main import (
    _initialize_sentry,
    _inner_main,
    _log,
    _require_commands,
    _require_single_command,
    main,
)
from .._version import __version__


class InitializeSentryTest(TestCase):
    def test_good_do(self):
        with (
            patch("sentry_sdk.init") as sentry_sdk_init_mock,
            patch.dict(os.environ, {"SENTRY_DSN": "https://host.invalid/"}),
        ):
            _initialize_sentry()

        self.assertEqual(sentry_sdk_init_mock.call_args.kwargs["default_integrations"], False)
        self.assertCountEqual(
            sentry_sdk_init_mock.call_args.kwargs.keys(),
            [
                "default_integrations",
                "integrations",
            ],
        )

    def test_good_noop(self):
        with (
            patch("sentry_sdk.init") as sentry_sdk_init_mock,
            patch.dict(os.environ, {"SENTRY_DSN": ""}),
        ):
            _initialize_sentry()

        self.assertEqual(sentry_sdk_init_mock.call_count, 0)

    def test_bad(self):
        with (
            patch.object(_log, "error") as log_error_mock,
            patch("builtins.__import__", side_effect=ImportError),
            patch.dict(os.environ, {"SENTRY_DSN": "https://host.invalid/"}),
            self.assertRaises(SystemExit) as caught,
        ):
            _initialize_sentry()

        self.assertEqual(caught.exception.args, (2,))
        self.assertEqual(
            log_error_mock.call_args.args,
            (
                "Use of Sentry requested via setting SENTRY_DSN but "
                "Python package 'sentry_sdk' is not installed, aborted.",
            ),
        )


class InnerMainTest(TestCase):
    def test_help(self):
        with (
            patch("sys.argv", ["pytocron", "--help"]),
            patch("sys.stdout", StringIO()) as stdout,
            self.assertRaises(SystemExit),
        ):
            _inner_main()

        self.assertIn("https://github.com/hartwork/pytocron/issues", stdout.getvalue())

    def test_version(self):
        with (
            patch("sys.argv", ["pytocron", "--version"]),
            patch("sys.stdout", StringIO()) as stdout,
            self.assertRaises(SystemExit),
        ):
            _inner_main()

        self.assertIn(f"pytocron {__version__}", stdout.getvalue())

    @parameterized.expand(LOG_LEVELS.items())
    def test_log_level(self, log_level_name, expected_log_level):
        with (
            NamedTemporaryFile() as empty_file,
            patch("sys.argv", ["pytocron", "--log-level", log_level_name, empty_file.name]),
            patch(
                "logging.basicConfig",
                side_effect=SystemExit,
                autospec=True,
            ) as logging_config_mock,
            self.assertRaises(SystemExit),
        ):
            _inner_main()

        self.assertEqual(logging_config_mock.call_args.kwargs["level"], expected_log_level)

    @parameterized.expand(
        [
            (["--pretend"], True),
            ([], False),
        ],
    )
    def test_pretend(self, extra_argv, expected_pretend):
        with (
            NamedTemporaryFile() as empty_file,
            patch("sys.argv", ["pytocron", *extra_argv, empty_file.name]),
            patch("logging.basicConfig", autospec=True),
            patch("pytocron._main.run_cron_jobs", autospec=True) as run_cron_jobs_mock,
        ):
            _inner_main()

        self.assertEqual(run_cron_jobs_mock.call_args.kwargs["pretend"], expected_pretend)


class MainTest(TestCase):
    def test(self):
        with (
            patch("pytocron._main._inner_main", side_effect=KeyboardInterrupt),
            self.assertRaises(SystemExit) as caught,
        ):
            main()

        self.assertEqual(caught.exception.args, (128 + signal.SIGINT,))


class RequireSingleCommandTest(TestCase):
    def test_good(self):
        _require_single_command("sh", "POSIX shell")

    def test_bad(self):
        with self.assertRaises(SystemExit) as caught:
            _require_single_command("1234567890", "digits-ng")

        self.assertEqual(
            caught.exception.args,
            (
                "Required command '1234567890' not found, aborted."
                " Is digits-ng installed and in ${PATH}?",
            ),
        )


class RequireCommandsTest(TestCase):
    def test_good(self):
        _require_commands()
