#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import argparse
import logging
import socket
import time

import cmk.utils.render
from cmk.plugins.emailchecks.lib.ac_args import parse_trx_arguments, Scope
from cmk.plugins.emailchecks.lib.connections import make_fetch_connection, POP3
from cmk.plugins.emailchecks.lib.utils import active_check_main, Args, CheckResult


def create_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--warn-age-oldest",
        type=int,
        help="warn if the oldest message is older than this value (in seconds)",
    )
    parser.add_argument(
        "--crit-age-oldest",
        type=int,
        help="crit if the oldest message is older than this value (in seconds)",
    )

    parser.add_argument(
        "--warn-age-newest",
        type=int,
        help="warn if the newest message is older than this value (in seconds)",
    )
    parser.add_argument(
        "--crit-age-newest",
        type=int,
        help="crit if the newest message is older than this value (in seconds)",
    )

    parser.add_argument(
        "--warn-count",
        type=int,
        help="number of mails above which the check will warn",
    )
    parser.add_argument(
        "--crit-count",
        type=int,
        help="number of mails above which the check will become critical",
    )

    parser.add_argument(
        "--mailbox",
        type=str,
        nargs="+",
        action="extend",
        help="mailbox to check. Can appear repeatedly to monitor multiple mailboxes",
    )

    parser.add_argument(
        "--retrieve-max",
        metavar="COUNT",
        type=int,
        help="limit the number of mails retrieved per mailbox. Only relevant when checking age",
    )
    return parser


def check_mailboxes(args: Args) -> CheckResult:
    fetch = parse_trx_arguments(args, Scope.FETCH)
    timeout = int(args.connect_timeout)

    if fetch.protocol == "POP3":
        raise RuntimeError("check_mailboxes does not operate on POP servers, sorry.")
    if type(args.crit_age_newest) is not type(args.warn_age_newest):
        raise RuntimeError("--warn-age-newest and --crit-age-newest must be provided together")
    if type(args.crit_age_oldest) is not type(args.warn_age_oldest):
        raise RuntimeError("--warn-age-oldest and --crit-age-oldest must be provided together")

    socket.setdefaulttimeout(timeout)
    status_icon = {0: "", 1: "(!) ", 2: "(!!) "}
    messages = []
    now = time.time()

    with make_fetch_connection(fetch, timeout) as mailbox:
        logging.info("connected..")
        assert not isinstance(mailbox, POP3)

        logging.info("connected, fetch mailbox folders..")
        available_mailboxes = list(mailbox.folders())

        logging.debug("Found %d mailbox folders", len(available_mailboxes))
        logging.debug("Mailboxes to check: %r", args.mailbox)
        if args.mailbox and any(folder not in available_mailboxes for folder in args.mailbox):
            return (
                3,
                "Some mailbox names are not available: %r"
                % (set(args.mailbox) - set(available_mailboxes)),
                [],
            )

        for i, folder in enumerate(args.mailbox or available_mailboxes):
            logging.debug("Check folder %r (%d/%d)", folder, i, len(available_mailboxes))
            mail_count = mailbox.select_folder(folder)
            logging.debug("%d mails", mail_count)

            if args.crit_count and args.warn_count and mail_count >= args.warn_count:
                messages.append(
                    (
                        2 if mail_count >= args.crit_count else 1,
                        "%r has %d messages (warn/crit at %d/%d)"
                        % (folder, mail_count, args.warn_count, args.crit_count),
                    )
                )

            if args.crit_age_oldest is not None and args.warn_age_oldest is not None:
                old_mails = sorted(mailbox.mails_by_date(before=now - args.warn_age_oldest))
                logging.debug("timestamps fetched from folder %r: %s", folder, old_mails)
                if old_mails and (oldest := now - old_mails[0]) >= args.warn_age_oldest:
                    status = 2 if oldest >= args.crit_age_oldest else 1
                    messages.append(
                        (
                            status,
                            f"Oldest mail in {folder!r} is at least "
                            f"{cmk.utils.render.Age(oldest)} old "
                            f"{status_icon[status]}"
                            f"(warn/crit at {cmk.utils.render.Age(args.warn_age_oldest)}"
                            f"/{cmk.utils.render.Age(args.crit_age_oldest)})",
                        )
                    )

            if args.crit_age_newest is not None and args.warn_age_newest is not None:
                new_mails = sorted(mailbox.mails_by_date(after=now - args.crit_age_newest))
                logging.debug("timestamps fetched from folder %r: %s", folder, new_mails)

                if new_mails and (newest := now - new_mails[-1]) >= args.warn_age_newest:
                    status = 2 if newest >= args.crit_age_newest else 1
                    messages.append(
                        (
                            status,
                            f"Newest mail in {folder!r} is at least "
                            f"{cmk.utils.render.Age(newest)} old "
                            f"{status_icon[status]}"
                            f"(warn/crit at {cmk.utils.render.Age(args.warn_age_newest)}"
                            f"/{cmk.utils.render.Age(args.crit_age_newest)})",
                        )
                    )
                elif not new_mails:
                    # crit in case there are no new mails
                    status = 2
                    messages.append(
                        (
                            status,
                            f"No new mails found in {folder!r} {status_icon[status]}"
                            f"(warn/crit at {cmk.utils.render.Age(args.warn_age_newest)}"
                            f"/{cmk.utils.render.Age(args.crit_age_newest)})",
                        )
                    )

        if messages:
            return max(m[0] for m in messages), ", ".join([m[1] for m in messages]), None

        return 0, "all mailboxes fine", None


def main() -> None:
    logging.getLogger().name = "check_mailboxes"
    active_check_main(create_argument_parser(), check_mailboxes)
