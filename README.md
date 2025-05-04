[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![Run the test suite](https://github.com/hartwork/pytocron/actions/workflows/run-tests.yml/badge.svg)](https://github.com/hartwork/pytocron/actions/workflows/run-tests.yml)


# pytocron

**pytocron** is a cron implementation
targeting containers,
written in Python,
with seconds and year resolution,
native support for [Healthchecks.io](https://healthchecks.io/) and
&gt;90% test coverage.
It is licensed under
[GNU Affero General Public License v3.0 or later](https://spdx.org/licenses/AGPL-3.0-or-later.html) and
is meant to remain simple and maintainable.

One particular prime use case is to feed uptime monitoring.
For example, here is how I monitor availability of [my blog](https://blog.hartwork.org/):

```crontab
# Check blog availability every 30 seconds
# hc-ping: https://hc-ping.com/00000000-0000-0000-0000-000000000000
*/30 * * * * * * wget -qO- -T2 https://blog.hartwork.org/ | grep -qF 'Hartwork Blog'
```

Regarding name "pytocron":
It was inspired by the term [pytosquatting](https://pytosquatting.overtag.dk/) and
it had no search results on Google.

If you like **pytocron**, please support it with a star!


# Installation

```console
# pip3 install pytocron
```

or

```console
# pipx install pytocron
```


# Comparison with other crons

| &nbsp; | [pytocron](#) | [Supercronic](https://github.com/aptible/supercronic) | [Vixie Cron](https://github.com/vixie/cron) |
| -- | -- | -- | -- |
| Written in | Python | Go | C |
| Container support | &nbsp; | &nbsp; | &nbsp; |
| ∟ Targets | containers | containers | non-container systems |
| ∟ Environment variables | kept | kept | ? |
| ∟ Multi-user mode | ✘ | ✘ | ✔ |
| ∟ Logging target | stdout, stderr | stdout, stderr | syslog *or* log file |
| ∟ Log rotation support | ✘ | ✔ | ✔ |
| ∟ Command shell | `bash -e -u` | `/bin/sh` | `/bin/sh` |
| ∟ Daemonization | ✘ | ✘ | ✔ |
| ∟ Crontab reloading | ✘ | ✔ | ✔ |
| Integrations | &nbsp; | &nbsp; | &nbsp; |
| ∟ Support for [Healthchecks.io](https://healthchecks.io/) | ✔ | ✘ | ✘ |
| ∟ Support for [Sentry](https://sentry.io/) | ✔ | ✔ | ✘ |
| Crontab syntax | &nbsp; | &nbsp; | &nbsp; |
| ∟ Seconds and year resolution | ✔ (forced) | ✔ (optional) | ✘ |
| ∟ Implementation | [croniter](https://github.com/pallets-eco/croniter) | [cronexpr](https://github.com/aptible/supercronic/tree/master/cronexpr) | [custom](https://github.com/vixie/cron/blob/9cc8ab1087bb9ab861dd5595c41200683c9f6712/user.c#L41) |
| Exceeded job runtime handling | auto-kill | overlapping or skips | ? |
| Handling of [daylight saving time](https://en.wikipedia.org/wiki/Daylight_saving_time) | ? | ? | ? |
| Signal handling | &nbsp; | &nbsp; | &nbsp; |
| ∟ `SIGHUP` | shutdown | shutdown | log file reopen |
| ∟ `SIGUSR2` | shutdown | crontab file reload | shutdown |


# Contributing

Prior to opening pull requests, please [create an issue](https://github.com/hartwork/pytocron/issues) to discuss the matter first.
Thank you!


# Security

If you believ to have found a security issue within **pytocron**, please [reach out via e-mail](mailto:sebastian@pipping.org).
Thank you!


# Support

Please [report any bugs](https://github.com/hartwork/pytocron/issues) that you find.

Like this tool? Support it with a star!
