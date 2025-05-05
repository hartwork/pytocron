# Copyright (c) 2025 Sebastian Pipping <sebastian@pipping.org>
#
# Licensed under GNU Affero General Public License v3.0 or later
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import sys

from ._timing import epoch_to_local_datetime

LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "ERROR": logging.ERROR,
    "INFO": logging.INFO,
}


class _CustomFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):  # noqa: ARG002, N802
        dt = epoch_to_local_datetime(record.created)
        return dt.isoformat(sep=" ", timespec="milliseconds")


def configure_logging(level_name: str) -> None:
    format_ = "pytocron [%(asctime)s] %(levelname)s: %(message)s"

    logging.basicConfig(
        level=LOG_LEVELS[level_name],
        stream=sys.stderr,
        format=format_,
    )

    formatter = _CustomFormatter(fmt=format_)

    for handler in logging.root.handlers:
        handler.setFormatter(formatter)
