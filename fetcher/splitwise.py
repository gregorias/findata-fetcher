# -*- coding: utf-8 -*-
"""Fetches current balance from Splitwise."""
import csv
import io
from typing import List, NamedTuple, Tuple

import splitwise  # type: ignore


class Credentials(NamedTuple):
    consumer_key: str
    consumer_secret: str
    api_key: str


def fetch_balance(
        friend: splitwise.Friend) -> Tuple[str, str, List[Tuple[str, str]]]:
    return (friend.first_name, friend.last_name,
            [(b.amount, b.currency_code) for b in friend.getBalances()])


def fetch_balances(
        creds: Credentials) -> List[Tuple[str, str, Tuple[str, str]]]:
    """Fetches Splitwise balance.

    Returns:
        A list of non-zero balance entries.
    """
    s = splitwise.Splitwise(creds.consumer_key,
                            creds.consumer_secret,
                            api_key=creds.api_key)
    balances = []
    for f in s.getFriends():
        (fn, ln, bs) = fetch_balance(f)
        for b in bs:
            balances.append((fn, ln, b))
    return balances


def export_balances(bs: List[Tuple[str, str, Tuple[str, str]]]) -> bytes:
    """Exports balances to a CSV file."""
    with io.StringIO() as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["fname", "lname", "amount", "currency"],
            delimiter=',')
        writer.writeheader()
        for (fn, ln, (amount, currency_code)) in bs:
            writer.writerow({
                'fname': fn,
                "lname": ln,
                "amount": amount,
                "currency": currency_code
            })
        return f.getvalue().encode('utf8')
