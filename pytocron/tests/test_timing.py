# Copyright (c) 2025 Sebastian Pipping <sebastian@pipping.org>
#
# Licensed under GNU Affero General Public License v3.0 or later
# SPDX-License-Identifier: AGPL-3.0-or-later

import datetime
import time
from unittest import TestCase

from .._timing import (
    _get_local_timezone,
    epoch_to_local_datetime,
    localtime_epoch,
    without_micros,
)


def _without_micros_and_timezone(dt: datetime.datetime) -> datetime.datetime:
    return dt.replace(microsecond=0).replace(tzinfo=None)


class LocaltimeEpochTest(TestCase):
    def test(self):
        self.assertAlmostEqual(localtime_epoch(), time.time(), places=3)


class GetLocalTimezoneTest(TestCase):
    def test(self):
        local_time_zone = _get_local_timezone()

        naive_local_now = datetime.datetime.now()  # noqa: DTZ005
        aware_local_now = naive_local_now.replace(tzinfo=local_time_zone)

        self.assertTrue(aware_local_now.isoformat().startswith(naive_local_now.isoformat()))


class EpochToLocalDatetime(TestCase):
    def test(self):
        expected_naive_dt = datetime.datetime.now()  # noqa: DTZ005
        self.assertIsNone(expected_naive_dt.tzinfo)  # self-test

        actual_naive_dt = epoch_to_local_datetime(localtime_epoch())

        self.assertEqual(actual_naive_dt.tzinfo, _get_local_timezone())
        self.assertEqual(
            _without_micros_and_timezone(actual_naive_dt),
            _without_micros_and_timezone(expected_naive_dt),
        )


class WithoutMicrosTest(TestCase):
    def test(self):
        original_dt = datetime.datetime.fromisoformat("2011-11-04T00:05:23.123456+04:00")
        expected_dt = datetime.datetime.fromisoformat("2011-11-04T00:05:23+04:00")

        actual_dt = without_micros(original_dt)

        self.assertEqual(actual_dt, expected_dt)
