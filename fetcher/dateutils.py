# -*- coding: utf-8 -*-
import datetime


def yesterday(day: datetime.date) -> datetime.date:
    return day - datetime.timedelta(days=1)
