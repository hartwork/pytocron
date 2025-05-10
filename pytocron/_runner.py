# Copyright (c) 2025 Sebastian Pipping <sebastian@pipping.org>
#
# Licensed under GNU Affero General Public License v3.0 or later
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import functools
import logging
import math
import shlex
import signal
import subprocess
import sys
import time
from contextlib import suppress
from multiprocessing import Process
from typing import TYPE_CHECKING

import croniter
import requests

if TYPE_CHECKING:
    from typing import Never

    from ._crontab_parser import CrontabEntry


from ._timing import epoch_to_local_datetime, localtime_epoch, without_micros

_ATTRIBUTE_STARTED = "_started"

_HARD_KILL_TOLERANCE_SECONDS = 5

_SHELL_ARGV = ["bash", "-euc"]
_SETSID_ARGV = ["setsid", "--wait"]

_log = logging.getLogger(__name__)


class _PingingFailedError(Exception): ...


def _notify_healthchecks_io(hc_ping_url: str, exit_code: int) -> None:
    url = hc_ping_url if exit_code == 0 else f"{hc_ping_url}/{exit_code}"
    try:
        response = requests.get(url, timeout=2.0)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        message = f"Pinging URL {url!r} failed."
        raise _PingingFailedError(message) from e


def _create_cronjob_argv(command: str, tolerated_runtime_seconds: int | None) -> list[str]:
    if tolerated_runtime_seconds is None:
        timeout_argv = []
    elif tolerated_runtime_seconds <= _HARD_KILL_TOLERANCE_SECONDS:
        timeout_argv = [
            "timeout",
            "--signal=KILL",
            f"{tolerated_runtime_seconds}s",
        ]
    else:
        soft_kill_seconds = tolerated_runtime_seconds
        hard_kill_seconds = soft_kill_seconds + _HARD_KILL_TOLERANCE_SECONDS
        timeout_argv = [
            "timeout",
            f"--kill-after={hard_kill_seconds}s",
            "--signal=INT",
            f"{soft_kill_seconds}s",
        ]
        del soft_kill_seconds
        del hard_kill_seconds

    return _SETSID_ARGV + timeout_argv + _SHELL_ARGV + [command]


def _run_single_cron_job(  # noqa: C901
    crontab_entry: CrontabEntry,
    *,
    pretend: bool,
) -> None:
    next_run_epoch: float | None
    try:
        next_run_epoch = crontab_entry.frequency.get_next()
    except croniter.CroniterBadDateError:
        return

    second_next_run_epoch: float | None
    try:
        second_next_run_epoch = crontab_entry.frequency.get_next()
    except croniter.CroniterBadDateError:
        second_next_run_epoch = None

    while True:
        next_run_datetime = epoch_to_local_datetime(next_run_epoch)
        sleep_seconds = next_run_epoch - localtime_epoch()

        _log.info(
            f"Command {crontab_entry.command!r} now scheduled"
            f" for {without_micros(next_run_datetime)}"
            f" ({math.ceil(sleep_seconds)} seconds from now).",
        )

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

        if second_next_run_epoch is None:
            tolerated_runtime_seconds = None  # i.e. unlimited
        else:
            tolerated_runtime_seconds = max(
                1,
                math.ceil(second_next_run_epoch - next_run_epoch),
            )

        argv = _create_cronjob_argv(crontab_entry.command, tolerated_runtime_seconds)

        _log.info(f"Running {crontab_entry.command!r}...")
        _log.debug(f"Running: {' '.join(shlex.quote(a) for a in argv)}")

        exit_code = 0 if pretend else subprocess.call(argv)  # noqa: S603

        if exit_code != 0:
            _log.error(f"Command {crontab_entry.command!r} failed with exit code {exit_code}.")

        if crontab_entry.hc_ping_url is not None and not pretend:
            try:
                _notify_healthchecks_io(crontab_entry.hc_ping_url, exit_code)
            except _PingingFailedError as e:
                # NOTE: This is not .error or .warning because depending on user configuration,
                #       the healthchecks.io setup will classify this as a problem and send an
                #       alert or not.
                _log.info(e.args[0])

        next_run_epoch = second_next_run_epoch

        if next_run_epoch is None:
            break

        try:
            second_next_run_epoch = crontab_entry.frequency.get_next()
        except croniter.CroniterBadDateError:
            second_next_run_epoch = None


def _run_single_cron_job_until_sigint(crontab_entry: CrontabEntry, *, pretend: bool) -> None:
    with suppress(KeyboardInterrupt):
        _run_single_cron_job(crontab_entry=crontab_entry, pretend=pretend)


def _shutdown_gracfully(processes: list[Process], signal_number: int, _frame: object):
    signal_name = signal.Signals(signal_number).name
    _log.info(f"Received {signal_name}, shutting down...")

    for process in processes:
        started = getattr(process, _ATTRIBUTE_STARTED, False)
        if signal_number == signal.SIGINT:
            if started:
                process.join()
            _log.debug(f"Joined {process.name}.")
        else:
            if started:
                process.terminate()
            _log.debug(f"Terminated {process.name}.")

    _log.info("Done.")

    sys.exit(128 + signal_number)


def run_cron_jobs(crontab_entries: list[CrontabEntry], *, pretend: bool) -> Never:
    for signal_code in (signal.SIGUSR1, signal.SIGUSR2):
        signal.signal(signal_code, signal.SIG_IGN)

    processes = [
        Process(
            target=_run_single_cron_job_until_sigint,
            kwargs=dict(  # noqa: C408
                crontab_entry=crontab_entry,
                pretend=pretend,
            ),
        )
        for crontab_entry in crontab_entries
    ]

    for process in processes:
        _log.debug(f"Starting {process.name}...")
        process.start()
        setattr(process, _ATTRIBUTE_STARTED, True)

    shutdown_gracfully = functools.partial(_shutdown_gracfully, processes)

    for signal_code in (signal.SIGHUP, signal.SIGINT, signal.SIGQUIT, signal.SIGTERM):
        signal.signal(signal_code, shutdown_gracfully)

    signal.pause()
