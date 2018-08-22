from datetime import datetime


def format_token_value(value: float) -> str:
    return "{0:.0f}".format(int(value))


def format_token_value_subject(value: float) -> str:
    return "{0:.0f}".format(int(value))


def format_fiat_value(value: float) -> str:
    return "{0:.2f}".format(value)


def format_coin_value(value: float) -> str:
    return "{0:.2f}".format(value)


def format_conversion_rate(value: float) -> str:
    return "{0:.2f}".format(value)


def format_date_period(start_date: datetime, end_date: datetime) -> str:
    return '{0:%d %b %Y} - {1:%d %b %Y}'.format(start_date, end_date)