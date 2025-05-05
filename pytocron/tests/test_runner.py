# Copyright (c) 2025 Sebastian Pipping <sebastian@pipping.org>
#
# Licensed under GNU Affero General Public License v3.0 or later
# SPDX-License-Identifier: AGPL-3.0-or-later

import signal
import time
from functools import partial
from multiprocessing import Process
from unittest import TestCase
from unittest.mock import Mock, patch

import requests
from parameterized import parameterized

from .._crontab_parser import CrontabEntry, _frequency_seven
from .._runner import (
    _ATTRIBUTE_STARTED,
    _HARD_KILL_TOLERANCE_SECONDS,
    _create_cronjob_argv,
    _notify_healthchecks_io,
    _PingingFailedError,
    _run_single_cron_job_forever,
    _run_single_cron_job_until_sigint,
    _shutdown_gracfully,
    run_cron_jobs,
)


class CreateCronjobArgvTest(TestCase):
    @parameterized.expand(
        [
            (
                _HARD_KILL_TOLERANCE_SECONDS,
                [
                    "setsid",
                    "--wait",
                    "timeout",
                    "--signal=KILL",
                    f"{_HARD_KILL_TOLERANCE_SECONDS}s",
                    "bash",
                    "-euc",
                    "one two",
                ],
            ),
            (
                _HARD_KILL_TOLERANCE_SECONDS + 1,
                [
                    "setsid",
                    "--wait",
                    "timeout",
                    f"--kill-after={2 * _HARD_KILL_TOLERANCE_SECONDS + 1}s",
                    "--signal=INT",
                    f"{_HARD_KILL_TOLERANCE_SECONDS + 1}s",
                    "bash",
                    "-euc",
                    "one two",
                ],
            ),
        ],
    )
    def test(self, tolerated_runtime_seconds, expected_argv):
        actual_argv = _create_cronjob_argv("one two", tolerated_runtime_seconds)
        self.assertEqual(actual_argv, expected_argv)


class NotifyHealthchecksIo(TestCase):
    @parameterized.expand(
        [
            (0, "https://host.invalid/path"),
            (123, "https://host.invalid/path/123"),
        ],
    )
    def test(self, exit_code, expected_request_url):
        with (
            patch(
                "requests.get",
                return_value=Mock(
                    raise_for_status=Mock(side_effect=requests.exceptions.HTTPError),
                ),
            ) as requests_get_mock,
            self.assertRaises(_PingingFailedError) as caught,
        ):
            _notify_healthchecks_io("https://host.invalid/path", exit_code)

        self.assertEqual(requests_get_mock.call_args.args, (expected_request_url,))
        self.assertEqual(caught.exception.args, (f"Pinging URL {expected_request_url!r} failed.",))


class RunCronJobsTest(TestCase):
    def test_empty(self):
        with patch("signal.pause"):
            run_cron_jobs(crontab_entries=[], pretend=False)

    def test_processes_started(self):
        crontab_entries = [
            CrontabEntry(
                frequency=_frequency_seven("1 * * * * * *"),
                command="false 1",
                hc_ping_url=None,
            ),
            CrontabEntry(
                frequency=_frequency_seven("2 * * * * * *"),
                command="false 2",
                hc_ping_url=None,
            ),
        ]

        with (
            patch("signal.signal", autospec=True),
            patch("signal.pause"),
            patch.object(Process, "start") as start_process_mock,
        ):
            run_cron_jobs(crontab_entries=crontab_entries, pretend=True)

        self.assertEqual(start_process_mock.call_count, 2)


class ShutdownGracfullyTest(TestCase):
    @parameterized.expand(
        [
            (True, signal.SIGINT),
            (False, signal.SIGINT),
            (None, signal.SIGINT),
            (True, signal.SIGTERM),
            (False, signal.SIGTERM),
            (None, signal.SIGTERM),
        ],
    )
    def test(self, started, signal_number):
        expected_exit_code = 128 + signal_number
        p1 = Process(target=partial(time.sleep, 0.5))
        p2 = Process(target=partial(time.sleep, 0.5))
        processes = [p1, p2]
        if started:
            p1.start()
        if started is not None:
            setattr(p1, _ATTRIBUTE_STARTED, started)

        with self.assertRaises(SystemExit) as caught:
            _shutdown_gracfully(processes, signal_number, None)

        self.assertEqual(caught.exception.args, (expected_exit_code,))

        if started and signal_number == signal.SIGINT:
            p1.terminate()


class RunSingleCronJobForever(TestCase):
    _HC_PING_URL = "https://test.invalid/path"

    def test_good(self):
        crontab_entry = CrontabEntry(
            frequency=_frequency_seven("* * * * * * 2070"),
            command="true 1 2 3",
            hc_ping_url=self._HC_PING_URL,
        )

        with (
            patch("time.sleep", autospec=True) as sleep_mock,
            patch(
                "pytocron._runner._notify_healthchecks_io",
                autospec=True,
            ) as notify_healthchecks_io_mock,
        ):
            _run_single_cron_job_forever(crontab_entry, pretend=False, _times=3)

        self.assertEqual(sleep_mock.call_count, 3)
        for i in range(3):
            self.assertGreaterEqual(sleep_mock.call_args_list[i].args[0], 1)

        self.assertEqual(notify_healthchecks_io_mock.call_count, 3)
        for i in range(3):
            self.assertEqual(
                notify_healthchecks_io_mock.call_args_list[i].args,
                (self._HC_PING_URL, 0),
            )

    def test_bad(self):
        crontab_entry = CrontabEntry(
            frequency=_frequency_seven("* * * * * * 2070"),
            command="false 1 2 3",
            hc_ping_url=self._HC_PING_URL,
        )

        with (
            patch("time.sleep", autospec=True) as sleep_mock,
            patch(
                "pytocron._runner._notify_healthchecks_io",
                side_effect=_PingingFailedError("did not work :)"),
            ) as notify_healthchecks_io_mock,
        ):
            _run_single_cron_job_forever(crontab_entry, pretend=False, _times=3)

        self.assertEqual(sleep_mock.call_count, 3)
        for i in range(3):
            self.assertGreaterEqual(sleep_mock.call_args_list[i].args[0], 1)

        self.assertEqual(notify_healthchecks_io_mock.call_count, 3)
        for i in range(3):
            self.assertEqual(
                notify_healthchecks_io_mock.call_args_list[i].args,
                (self._HC_PING_URL, 1),
            )


class RunSingleCronJobUntilSigint(TestCase):
    def test(self):
        with patch("pytocron._runner._run_single_cron_job_forever", side_effect=KeyboardInterrupt):
            _run_single_cron_job_until_sigint(crontab_entry=None, pretend=True)
