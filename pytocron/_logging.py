# Copyright (c) 2025 Sebastian Pipping <sebastian@pipping.org>
#
# Licensed under GNU Affero General Public License v3.0 or later
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import os
import sys

from colorama import Fore

from ._timing import epoch_to_local_datetime

LOG_LEVELS = {
    # NOTE: There is no WARNING/WARN or CRITICAL/FATAL or NOTSET in here
    #       because pytocron does not use these levels by itself
    "DEBUG": logging.DEBUG,
    "ERROR": logging.ERROR,
    "INFO": logging.INFO,
}

_FALLBACK_FOREGROUND_COLOR = Fore.CYAN
_FOREGROUND_COLOR_OF_LEVEL = {
    # NOTE: All other levels are handled via fallback
    logging.CRITICAL: Fore.RED,
    logging.DEBUG: Fore.GREEN,
    logging.ERROR: Fore.RED,
    logging.WARNING: Fore.MAGENTA,
}


class _CustomFormatter(logging.Formatter):
    color_enabled = False

    def formatTime(self, record, datefmt=None):  # noqa: ARG002, N802
        dt = epoch_to_local_datetime(record.created)
        return dt.isoformat(sep=" ", timespec="milliseconds")

    def format(self, record):
        formatted = super().format(record)

        if not self.color_enabled:
            return formatted

        fore_color = _FOREGROUND_COLOR_OF_LEVEL.get(record.levelno, _FALLBACK_FOREGROUND_COLOR)
        return f"{fore_color}{formatted}{Fore.RESET}"


def configure_logging(level_name: str) -> None:
    format_ = "pytocron [%(asctime)s] %(levelname)s: %(message)s"

    logging.basicConfig(
        level=LOG_LEVELS[level_name],
        stream=sys.stderr,
        format=format_,
    )

    formatter = _CustomFormatter(fmt=format_)
    formatter.color_enabled = not os.environ.get("NO_COLOR") and os.isatty(sys.stderr.fileno())

    for handler in logging.root.handlers:
        handler.setFormatter(formatter)
