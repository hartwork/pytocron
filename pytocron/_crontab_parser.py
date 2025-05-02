# Copyright (c) 2025 Sebastian Pipping <sebastian@pipping.org>
#
# Licensed under GNU Affero General Public License v3.0 or later
# SPDX-License-Identifier: AGPL-3.0-or-later

import re
from dataclasses import dataclass
from typing import IO

import croniter

_NAMED_FREQUENCY = {
    # second, minute, hour, day, month, weekday, year
    "hourly": "0 0 * * * * *",  # once an hour at the beginning of the hour
    "midnight": "0 0 0 * * * *",  # once a day at midnight
    "minutely": "0 * * * * * *",  # once a minute at the beginning of the minute
    "monthly": "0 0 0 1 * * *",  # once a month at midnight morning of the first of the month
    "secondly": "* * * * * * *",  # once a second
    "weekly": "0 0 0 * * 0 *",  # once a week at midnight in the morning of Sunday
    "yearly": "0 0 0 1 1 * *",  # once a year at midnight in the morning of January 1
}
_NAMED_FREQUENCY["annually"] = _NAMED_FREQUENCY["yearly"]
_NAMED_FREQUENCY["daily"] = _NAMED_FREQUENCY["midnight"]


_MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
_WEEKDAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
_ATOM_PATTERN = f"(?:[0-9*/,-]|{'|'.join(_MONTHS)}|{'|'.join(_WEEKDAYS)})"
_FREQUENCY_SIX_PATTERN = "\\s+".join(f"{_ATOM_PATTERN}+" for _ in range(7))
_FREQUENCY_SIX_LINE_PATTERN = (
    f"^(?P<_frequency_seven>{_FREQUENCY_SIX_PATTERN})\\s+(?P<command>[^*].*)$"
)
_NAMED_FREQUENCY_LINE_PATTERN = (
    f"^@(?P<name>{'|'.join(k for k in _NAMED_FREQUENCY)})\\s+(?P<command>\\S.*)$"
)


@dataclass
class CrontabEntry:
    frequency: croniter.croniter
    command: str
    hc_ping_url: str | None

    def __eq__(self, other):
        if other is self:
            return True
        if not isinstance(other, CrontabEntry):
            return False
        return (
            self.frequency.expressions == other.frequency.expressions
            and self.command == other.command
            and self.hc_ping_url == other.hc_ping_url
        )

    def __ne__(self, other):
        return not self == other


class CrontabEntrySyntaxError(Exception):
    def __str__(self) -> str:
        return f"Syntax {self.args[0]!r} is not valid."


def _frequency_seven(text: str) -> croniter.croniter:
    try:
        return croniter.croniter(text, second_at_beginning=True)
    except croniter.CroniterBadCronError as e:
        raise CrontabEntrySyntaxError(text) from e


def _parse_crontab_line(line: str) -> tuple[croniter.croniter, str]:
    frequency: croniter.croniter

    if (m := re.match(_NAMED_FREQUENCY_LINE_PATTERN, line, flags=re.IGNORECASE)) is not None:
        name = m.group("name")
        frequency = _frequency_seven(_NAMED_FREQUENCY[name])
    elif (m := re.match(_FREQUENCY_SIX_LINE_PATTERN, line)) is not None:
        frequency = _frequency_seven(m.group("_frequency_seven"))
    else:
        raise CrontabEntrySyntaxError(line)

    command = m.group("command")

    return frequency, command


def iterate_crontab_entries(filelike: IO):
    hc_ping_url = None

    for line in filelike:
        line = line.rstrip()  # noqa: PLW2901

        # Whitespace-only line?
        if not line:
            continue

        # Is this a comment line?
        if re.search("^#", line):
            # Is this a hc-ping comment line?
            if (
                m := re.search("^# hc-ping: (?P<hc_ping_url>https://\\S+)\\s*$", line)
            ) is not None:
                hc_ping_url = m.group("hc_ping_url")
            else:
                hc_ping_url = None
        else:
            # Assume "<frequency> <command>" line
            frequency, command = _parse_crontab_line(line)  # may raise
            yield CrontabEntry(
                frequency=frequency,
                command=command,
                hc_ping_url=hc_ping_url,
            )
            hc_ping_url = None
