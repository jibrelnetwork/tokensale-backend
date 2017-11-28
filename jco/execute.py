from typing import Optional

import click

from jco.commonutils.app_init import initialize_app
from jco.appprocessor.app_create import flask_app
from jco.appprocessor import commands

app = flask_app


@app.cli.command()
@click.option('--mnemonic', required=True, prompt=True, confirmation_prompt=True, hide_input=True)
@click.option('--key_count', help="Number of keys", type=click.INT, required=True)
@click.option('--offset', help='Offset from the start', type=click.INT, required=True)
@click.option('--is_usable', help='True if address is allowed to assign to the new proposals',
              type=click.BOOL, required=True)
@initialize_app
def generate_eth_addresses(mnemonic, key_count, offset, is_usable):
    return commands.generate_eth_addresses(mnemonic, key_count, offset=offset, is_usable=is_usable)


@app.cli.command()
@click.option('--mnemonic', required=True, prompt=True, confirmation_prompt=True, hide_input=True)
@click.option('--key_count', help="Number of keys", type=click.INT, required=True)
@click.option('--offset', help='Offset from the start', type=click.INT, required=True)
@click.option('--is_usable', help='True if address is allowed to assign to the new proposals',
              type=click.BOOL, required=True)
@initialize_app
def generate_btc_addresses(mnemonic, key_count, offset, is_usable):
    return commands.generate_btc_addresses(mnemonic, key_count, offset=offset, is_usable=is_usable)


@app.cli.command()
@initialize_app
def fetch_tickers_price():
    return commands.fetch_tickers_price()


@app.cli.command()
@click.argument('start_offset', type=click.INT)
@click.argument('end_offset', type=click.INT)
@initialize_app
def fill_fake_tickers_price(start_offset, end_offset):
    return commands.fill_fake_tickers_price(start_offset=start_offset, end_offset=end_offset)


@app.cli.command()
@initialize_app
def scan_addresses():
    return commands.scan_addresses()


@app.cli.command()
@initialize_app
def calculate_jnt_purchases():
    return commands.calculate_jnt_purchases()


@app.cli.command()
@initialize_app
def check_withdraw_addresses():
    return commands.check_withdraw_addresses()
