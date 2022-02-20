# -*- coding: utf-8 -*-
"""Fetches current balance from Splitwise."""
from typing import List, NamedTuple

import splitwise  # type: ignore


class Credentials(NamedTuple):
    consumer_key: str
    consumer_secret: str
    api_key: str


def fetch_balance(friend: splitwise.Friend):
    return (friend.first_name, friend.last_name,
            [(b.amount, b.currency_code) for b in friend.getBalances()])


def fetch_balances(creds: Credentials) -> List:
    """Fetches Splitwise balance.

    Returns:
        TODO
    """
    s = splitwise.Splitwise(creds.consumer_key,
                            creds.consumer_secret,
                            api_key=creds.api_key)
    return [fetch_balance(f) for f in s.getFriends() if fetch_balance(f)[2]]
