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


#@app.cli.command()
#@click.argument('fullname')
#@click.argument('email')
#@click.argument('country')
#@click.argument('citizenship')
#@click.argument('currency')
#@click.argument('amount', type=click.FLOAT)
#@click.option('--reference_id')
#@initialize_app
#def add_proposal(fullname: str, email: str, country: str, citizenship: str,
#                 currency: str, amount: float, reference_id: Optional[str] = None):
#    return commands.add_proposal(fullname, email, country, citizenship, currency, amount, reference_id)


#@app.cli.command()
#@initialize_app
#def send_email_payment_data():
#    return commands.send_email_payment_data()


@app.cli.command()
@initialize_app
def scan_addresses():
    return commands.scan_addresses()


@app.cli.command()
@initialize_app
def calculate_jnt_purchases():
    return commands.calculate_jnt_purchases()


#@app.cli.command()
#@initialize_app
#def transaction_processing():
#    return commands.transaction_processing()


#@app.cli.command()
#@initialize_app
#def fill_address_from_proposal():
#    return commands.fill_address_from_proposal()


#@app.cli.command()
#@click.argument('start_address_id', type=click.INT)
#@click.argument('end_address_id', type=click.INT)
#@click.argument('is_enable', type=click.BOOL)
#@initialize_app
#def set_force_scanning(start_address_id: int, end_address_id: int, is_enable: bool):
#    return commands.set_force_scanning(start_address_id, end_address_id, is_enable)
