# Copyright (c) 2025 Sebastian Pipping <sebastian@pipping.org>
#
# Licensed under GNU Affero General Public License v3.0 or later
# SPDX-License-Identifier: AGPL-3.0-or-later

import argparse


def main():
    parser = argparse.ArgumentParser(
        prog="pytocron",
        description="Container cron with seconds resolution",
    )
    parser.parse_args()
