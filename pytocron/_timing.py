# Copyright (c) 2025 Sebastian Pipping <sebastian@pipping.org>
#
# Licensed under GNU Affero General Public License v3.0 or later
# SPDX-License-Identifier: AGPL-3.0-or-later

import datetime
import functools


def localtime_epoch() -> float:
    return datetime.datetime.now().timestamp()  # noqa: DTZ005


@functools.cache
def _get_local_timezone() -> datetime.timezone:
    return datetime.datetime.now().astimezone().tzinfo


def epoch_to_local_datetime(epoch: float) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(epoch, tz=_get_local_timezone())


def without_micros(dt: datetime.datetime) -> datetime.datetime:
    return dt.replace(microsecond=0)
