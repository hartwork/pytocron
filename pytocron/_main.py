# Copyright (c) 2025 Sebastian Pipping <sebastian@pipping.org>
#
# Licensed under GNU Affero General Public License v3.0 or later
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import argparse
import logging
import os
import shutil
import signal
import sys
from textwrap import dedent, indent
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Never

from ._crontab_parser import iterate_crontab_entries
from ._logging import LOG_LEVELS, configure_logging
from ._runner import run_cron_jobs
from ._version import __version__

_log = logging.getLogger(__name__)


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


def _initialize_sentry() -> None:
    if os.environ.get("SENTRY_DSN"):
        _log.info("Detected SENTRY_DSN, activating Sentry...")

        try:
            import sentry_sdk
            from sentry_sdk.integrations.logging import LoggingIntegration
        except ImportError:
            _log.error(
                "Use of Sentry requested via setting SENTRY_DSN but "
                "Python package 'sentry_sdk' is not installed, aborted.",
            )
            sys.exit(2)

        sentry_sdk.init(
            default_integrations=False,
            integrations=[
                LoggingIntegration(),
            ],
        )


def _inner_main() -> Never:
    parser = argparse.ArgumentParser(
        usage=indent(
            dedent("""
            %(prog)s [OPTIONS] CRONTAB
            %(prog)s --help
            %(prog)s --version
        """),
            "  ",
        ),
        prog="pytocron",
        description="Container cron with seconds resolution",
        epilog=dedent("""\
            environment variables:
              NO_COLOR              Disable use of color (default: auto-detect)
              SENTRY_DSN            Sentry [d]ata [s]ource [n]ame URL
              SENTRY_ENVIRONMENT    Sentry Environment (default: "production")
              SENTRY_RELEASE        Version or Git SHA1 to use with Sentry

            Software libre licensed under AGPL v3 or later.
            Brought to you by Sebastian Pipping <sebastian@pipping.org>.

            Please report bugs at https://github.com/hartwork/pytocron/issues — thank you!
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--log-level",
        dest="log_level_name",
        choices=LOG_LEVELS.keys(),
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

    configure_logging(config.log_level_name)

    _require_commands()

    _initialize_sentry()

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
