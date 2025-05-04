# Copyright (c) 2025 Sebastian Pipping <sebastian@pipping.org>
#
# Licensed under GNU Affero General Public License v3.0 or later
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import argparse
import logging
import shutil
import signal
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Never

from ._crontab_parser import iterate_crontab_entries
from ._runner import run_cron_jobs
from ._version import __version__

_LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "ERROR": logging.ERROR,
    "INFO": logging.INFO,
}


def _require_single_command(command: str, software_package_hint: str) -> None:
    if shutil.which(command) is None:
        sys.exit(
            f"Required command {command!r} not found, aborted."
            f" Is {software_package_hint} installed and in ${{PATH}}?",
        )


def _require_commands() -> None:
    for command, software_package_hint in [
        ("bash", "GNU Bash"),
        ("setsid", "util-linux"),
        ("timeout", "GNU coreutils"),
    ]:
        _require_single_command(command=command, software_package_hint=software_package_hint)


def _inner_main() -> Never:
    parser = argparse.ArgumentParser(
        prog="pytocron",
        description="Container cron with seconds resolution",
    )
    parser.add_argument(
        "--log-level",
        choices=_LOG_LEVELS.keys(),
        default="INFO",
        help="Logging level (default: %(default)s)",
    )
    parser.add_argument(
        "--pretend",
        default=False,
        action="store_true",
        help="Do not actually run commands (default: do run commands)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument("crontab_path", metavar="CRONTAB", help="Path to crontab file")
    config = parser.parse_args()

    logging.basicConfig(
        level=_LOG_LEVELS[config.log_level],
        stream=sys.stderr,
        format="pytocron [%(asctime)s] %(levelname)s: %(message)s",
    )

    _require_commands()

    with open(config.crontab_path) as f:
        crontab_entries = list(iterate_crontab_entries(f))

    run_cron_jobs(crontab_entries, pretend=config.pretend)


def main() -> Never:
    exit_code = 1
    try:
        _inner_main()
    except KeyboardInterrupt:
        exit_code = 128 + signal.SIGINT
    except Exception as e:  # noqa: BLE001
        _log.error(e)
    sys.exit(exit_code)
