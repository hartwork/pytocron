# Copyright (c) 2025 Sebastian Pipping <sebastian@pipping.org>
#
# Licensed under GNU Affero General Public License v3.0 or later
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import sys

LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "ERROR": logging.ERROR,
    "INFO": logging.INFO,
}


def configure_logging(level_name: str) -> None:
    logging.basicConfig(
        level=LOG_LEVELS[level_name],
        stream=sys.stderr,
        format="pytocron [%(asctime)s] %(levelname)s: %(message)s",
    )
