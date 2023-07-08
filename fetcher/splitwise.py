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


def fetch_credentials() -> Credentials:
    """Fetches credentials from my 1Password vault."""
    from . import op
    consumer_key = op.read("Private", "splitwise.com", "consumer key")
    consumer_secret = op.read("Private", "splitwise.com", "consumer secret")
    api_key = op.read("Private", "splitwise.com", "api key")
    return Credentials(consumer_key=consumer_key,
                       consumer_secret=consumer_secret,
                       api_key=api_key)


class Money(NamedTuple):
    amount: str
    currency_code: str


def fetch_balance(friend: splitwise.Friend) -> Tuple[str, str, List[Money]]:
    return (friend.first_name, friend.last_name, [
        Money(amount=b.amount, currency_code=b.currency_code)
        for b in friend.getBalances()
    ])


def fetch_balances(creds: Credentials) -> List[Tuple[str, str, Money]]:
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


def export_balances_to_csv(bs: List[Tuple[str, str, Money]]) -> bytes:
    """Exports balances to a CSV file."""
    with io.StringIO() as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["fname", "lname", "amount", "currency"],
            delimiter=',')
        writer.writeheader()
        for (fn, ln, money) in bs:
            writer.writerow({
                'fname': fn,
                "lname": ln,
                "amount": money.amount,
                "currency": money.currency_code
            })
        return f.getvalue().encode('utf8')
