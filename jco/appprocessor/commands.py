import random
import string
import time
import sys
import traceback
from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict, List
import requests
import logging
import random

from mnemonic import Mnemonic
from pycoin.key.BIP32Node import BIP32Node
from sqlalchemy.sql.expression import not_, or_, and_
from sqlalchemy.types import Boolean, Integer
from sqlalchemy.sql import func
from sqlalchemy.orm.util import aliased
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.sql import func
from psycopg2 import tz

from jco.appdb.db import session
from jco.appdb.models import *
from jco.commonutils.crypto import HDPrivateKey, HDKey
from jco.commonutils.bitfinex import Bitfinex
from jco.commonconfig.config import (INVESTMENTS__TOKEN_PRICE_IN_USD,
                                     INVESTMENTS__PUBLIC_SALE__START_DATE,
                                     INVESTMENTS__PUBLIC_SALE__END_DATE,
                                     EMAIL_NOTIFICATIONS__MAX_ATTEMPTS,
                                     BITFINEX__TIMEOUT,
                                     CRAWLER_PROXY__ENABLED,
                                     CRAWLER_PROXY__USER,
                                     CRAWLER_PROXY__PASS,
                                     CRAWLER_PROXY__URLS,
                                     FORCE_SCANNING_ADDRESS__ENABLED,
                                     CHECK_MAIL_DELIVERY__ENABLED,
                                     CHECK_MAIL_DELIVERY__DAYS_DEPTH,
                                     RAISED_TOKENS_SHIFT,
                                     TOKENS__TOTAL_SUPPLY,
                                     EMAIL_NOTIFICATIONS__SUPPORT_ADDRESS)
from jco.commonconfig.config import ETHERSCAN_API_KEY, ETHERSCAN_TIMEOUT, BLOCKCHAININFO_TIMEOUT
from jco.commonutils.utils import *
from jco.commonutils.ga_integration import *
from jco.commonutils.formats import *
from jco.commonutils.ethaddress_verify import is_valid_address
from jco.commonutils.contract import mintJNT, getTransactionInfo, ETH_CONTRACT__MAX_PENDING_COUNT


#
# Generate btc/eth addresses
#

def generate_eth_addresses(mnemonic: str, key_count: int, *, offset: int = 0, is_usable: bool = True) -> bool:
    logging.getLogger(__name__).info("Start to generate ETH addresses")

    master_key = HDPrivateKey.master_key_from_mnemonic(mnemonic)
    root_keys = HDKey.from_path(master_key, "m/44'/60'/0'")
    acct_priv_key = root_keys[-1]
    acct_pub_key = acct_priv_key.public_key

    # print('Account Master Public Key (Hex): ' + acct_pub_key.to_hex())
    # print('XPUB format: ' + acct_pub_key.to_b58check())

    # Generate addresses for external chain (not change address)
    change = 0
    for index in range(offset, key_count + offset):
        keys = HDKey.from_path(acct_pub_key, '{change}/{index}'.format(change=change, index=index))
        address = Address()
        address.address = checksum_encode(keys[-1].address()[2:])
        address.type = CurrencyType.eth
        address.is_usable = is_usable
        session.add(address)
    session.commit()

    logging.getLogger(__name__).info("Finished to generate ETH addresses")
    return True


def generate_btc_addresses(mnemonic: str, key_count: int, *, offset: int = 0, is_usable: bool = True) -> bool:
    logging.getLogger(__name__).info("Start to generate BTC addresses")

    node = BIP32Node.from_master_secret(Mnemonic.to_seed(mnemonic), 'BTC')

    # print('xprv', node.wallet_key(True))
    # print('XPUB format:', node.wallet_key())

    # Generate addresses
    for index in range(offset, key_count + offset):
        subnode = node.subkey_for_path("44'/0'/0'/0/%d" % index)
        address = Address()
        address.address = subnode.address()
        address.type = CurrencyType.btc
        address.is_usable = is_usable
        session.add(address)

    session.commit()

    logging.getLogger(__name__).info("Finished to generate BTC addresses")
    return True


#
# Fetch btc/eth prices
#

def fetch_tickers_price():
    logging.getLogger(__name__).info("Start to fetch last prices from the exchange")
    fetch_ticker_price(CurrencyType.btc, CurrencyType.usd, "btcusd")
    time.sleep(BITFINEX__TIMEOUT)
    fetch_ticker_price(CurrencyType.eth, CurrencyType.usd, "ethusd")
    logging.getLogger(__name__).info("Finished to fetch last prices from the exchange")


def fetch_ticker_price(db_fixed_currency: str, db_variable_currency: str, bitfinex_symbol: str):
    # noinspection PyBroadException
    try:
        logging.getLogger(__name__).info("Start to fetch {}/{} conversion rate from the Bitfinex"
                                         .format(db_fixed_currency, db_variable_currency))

        bitfinex = Bitfinex()
        ticker_data = bitfinex.get_ticker(bitfinex_symbol)
        if "bid" in ticker_data.keys() and "timestamp" in ticker_data.keys():
            price_datetime = datetime.utcfromtimestamp(ticker_data["timestamp"])
            price = Price(fixed_currency=db_fixed_currency,
                          variable_currency=db_variable_currency,
                          value=ticker_data["bid"],
                          created=price_datetime)
            session.add(price)
            session.commit()
            logging.getLogger(__name__).info("success for symbol '{}'.".format(bitfinex_symbol))
        else:
            logging.getLogger(__name__).error("invalid response from Bitfinex API for symbol '{}'."
                                              .format(bitfinex_symbol))

        logging.getLogger(__name__).info("Finished to fetch {}/{} conversion rate from the Bitfinex"
                                         .format(db_fixed_currency, db_variable_currency))

    except Exception:
        exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
        logging.getLogger(__name__).error("Finished to fetch {}/{} conversion rate from the Bitfinex due to error:\n{}"
                                          .format(db_fixed_currency, db_variable_currency, exception_str))
        session.rollback()


def fill_fake_tickers_price(*, start_offset: Optional[int] = 2, end_offset: Optional[int] = 2):
    logging.getLogger(__name__).info("Start to set test fake prices BTC/USD and ETH/USD")

    start_date = datetime.now() - timedelta(days=start_offset)
    end_date = datetime.now() + timedelta(days=end_offset)
    timestep = timedelta(minutes=1)
    base_price_btc = 4500
    base_price_eth = 300

    current_date = start_date
    price_change = 0
    while current_date < end_date:
        price_btc = Price(fixed_currency=CurrencyType.btc,
                          variable_currency=CurrencyType.usd,
                          value=base_price_btc + price_change,
                          created=current_date)
        price_eth = Price(fixed_currency=CurrencyType.eth,
                          variable_currency=CurrencyType.usd,
                          value=base_price_eth + price_change,
                          created=current_date)
        session.add(price_btc)
        session.add(price_eth)
        session.commit()
        current_date += timestep
        price_change += 0.1

    logging.getLogger(__name__).info("Finished to set test fake prices BTC/USD and ETH/USD")



#
# Send emails with the payment data
#

def send_email_payment_data():
    # noinspection PyBroadException
    try:
        logging.getLogger(__name__).info("Start to send emails with the payment data")

        proposals = session.query(Proposal) \
            .filter(or_(not_(Proposal.meta.has_key(Proposal.meta_key_notified)),
                        Proposal.meta[Proposal.meta_key_notified].astext.cast(Boolean) == False)) \
            .filter(or_(not_(Proposal.meta.has_key(Proposal.meta_key_failed_notifications)),
                        Proposal.meta[Proposal.meta_key_failed_notifications].astext.cast(
                            Integer) < EMAIL_NOTIFICATIONS__MAX_ATTEMPTS)) \
            .all()  # type: List[Proposal]

        for proposal in proposals:
            # noinspection PyBroadException
            try:
                if proposal.currency in [CurrencyType.btc, CurrencyType.eth]:
                    success, message_id = send_email_payment_data_crypto(proposal, INVESTMENTS__USD__MIN_LIMIT)
                else:
                    success, message_id = send_email_payment_data_fiat(proposal, INVESTMENTS__USD__MIN_LIMIT)

                if success:
                    proposal.set_notified(True)
                    proposal.set_mailgun_message_id(message_id)
                    session.commit()
                    logging.getLogger(__name__).info("Payment data successfully sent for proposal: {}".format(proposal))
                else:
                    failed_notifications = proposal.get_failed_notifications()
                    if failed_notifications is None:
                        failed_notifications = 0
                    failed_notifications += 1
                    proposal.set_failed_notifications(failed_notifications)
                    session.commit()
                    if failed_notifications < EMAIL_NOTIFICATIONS__MAX_ATTEMPTS:
                        logging.getLogger(__name__).warning("Failed to send payment data for proposal: {}"
                                                            .format(proposal))
                    else:
                        logging.getLogger(__name__).error("All attempts to send payment data for proposal exhausted: {}"
                                                          .format(proposal))
            except Exception:
                exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
                logging.getLogger(__name__).error("Failed to send email with the payment data due to exception:\n{}\n{}"
                                                  .format(proposal, exception_str))
                session.rollback()

        logging.getLogger(__name__).info("Finished to send emails with the payment data")

    except Exception:
        exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
        logging.getLogger(__name__).error("Failed to send emails with the payment data due to exception:\n{}"
                                          .format(exception_str))
        session.rollback()


#
# Get list of eth addresses with a balance over than zero
#

def get_eth_addresses_with_positive_balance(addresses: List[Address]) -> List[Address]:
    """
    Get Ether Balance for multiple Addresses in a single call

    :param addresses: Target addresses
    :type addresses: List[Address]
    :return: List of addresses, otherwise exception
    :rtype: List[Address
    """
    proxies = get_proxies()

    url_base = 'http://api.etherscan.io/api?'

    addresses_in_batch = 20
    result = list()

    for batch_number in range(0, (len(addresses) // addresses_in_batch) + 1):
        batch_addresses = addresses[batch_number * addresses_in_batch:
                                    batch_number * addresses_in_batch + addresses_in_batch]

        # Separate addresses by comma, up to a maxium of 20 accounts in a single batch
        url_balances = 'module=account&action=balancemulti&address={}&startblock=0&tah=latest&apikey={}' \
            .format(",".join([address.address for address in batch_addresses]), ETHERSCAN_API_KEY)
        url_request = url_base + url_balances

        try:
            if CRAWLER_PROXY__ENABLED:
                balances_response = requests.get(url_request, proxies=proxies)
            else:
                balances_response = requests.get(url_request)

            balances_response.raise_for_status()
        except Exception:
            logging.getLogger(__name__).warning("Bad response from blockexplorer")
            continue

        balances_response_json = balances_response.json()

        try:
            positive_accounts = [x['account'] for x in balances_response_json['result'] if x.get('balance') and float(x['balance'])>0]
        except Exception:
            exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
            logging.getLogger(__name__).error(
                "Failed to get eth addresses that have positive balance due to exception:\nblockexplorer response:\n{}\n{}"
                    .format(balances_response.text, exception_str))

        positive_addresses = [x for x in addresses if x.address in positive_accounts]
        result.extend(positive_addresses)

    return result


#
# Get list of btc addresses with a balance over than zero
#

def get_btc_addresses_with_positive_balance(addresses: List[Address]) -> List[Address]:
    """
    Get list of BTC transactions for the given addresses

    :param addresses: Target addresses
    :type addresses: List[str]
    :return: List of transactions, otherwise exception
    :rtype: list
    """
    proxies = get_proxies()

    url_base = 'https://blockchain.info/multiaddr?'

    addresses_in_batch = 50
    result = list()

    for batch_number in range(0, (len(addresses) // addresses_in_batch) + 1):
        batch_addresses = addresses[batch_number * addresses_in_batch:
                                    batch_number * addresses_in_batch + addresses_in_batch]

        # Separate addresses by '|'
        url_balances = 'active={}'.format("|".join([address.address for address in batch_addresses]))
        url_request = url_base + url_balances

        try:
            if CRAWLER_PROXY__ENABLED:
                balances_response = requests.get(url_request, proxies=proxies)
            else:
                balances_response = requests.get(url_request)

            balances_response.raise_for_status()
        except Exception:
            logging.getLogger(__name__).warning("Bad response from blockexplorer")
            continue

        balances_response_json = balances_response.json()

        if "addresses" not in balances_response_json \
                or type(balances_response_json['addresses']) != list:
            logging.getLogger(__name__).error("Wrong 'addresses' in response of Blockchain.info for BTC transactions:\n{}"
                         .format(balances_response_json))
            continue

        try:
            positive_accounts = [x['address'] for x in balances_response_json['addresses'] if x.get('n_tx') and float(x['n_tx']) > 0]
        except Exception:
            exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
            logging.getLogger(__name__).error(
                "Failed to get btc addresses that have positive balance due to exception:\nblockexplorer response:\n{}\n{}"
                    .format(balances_response.text, exception_str))

        positive_addresses = [x for x in addresses if x.address in positive_accounts]
        result.extend(positive_addresses)

    return result


#
# Scan for the new transactions
#

def scan_addresses(*, full_scan: bool = False,
                   w_transactions: bool = False,
                   wo_transactions: bool = False,
                   address_type: str = '',
                   is_even_rows: bool = False):
    # noinspection PyBroadException
    try:
        logging.getLogger(__name__).info(
            "Start to scan for the new transactions. full_scan: {}, w_tr: {}, wo_tr: {}, is_even: {}"
                .format(str(full_scan), str(w_transactions), str(wo_transactions), str(is_even_rows))
        )

        transaction_counts = session.query(Transaction.address_id, func.count(Transaction.id).label('count')) \
            .group_by(Transaction.address_id) \
            .subquery()

        addresses_with_transaction = list()
        addresses_eth_wo_transaction = list()
        addresses_btc_wo_transaction = list()

        addresses = list()
        if full_scan:
            addresses = session.query(Address) \
                .outerjoin(transaction_counts, transaction_counts.c.address_id == Address.id) \
                .filter(Address.user_id.isnot(None)) \
                .all()  # type: List[Address]
            logging.getLogger(__name__).info("scan all addresses len(addresses): {}"
                                             .format(str(len(addresses))))
        elif w_transactions:
            addresses_with_transaction = session.query(Address) \
                .outerjoin(transaction_counts, transaction_counts.c.address_id == Address.id) \
                .filter(Address.user_id.isnot(None)) \
                .filter(func.coalesce(transaction_counts.c.count, 0) > 0) \
                .all()  # type: List[Address]
            logging.getLogger(__name__).info("scan_addresses len(addresses_with_transaction): {}"
                                             .format(str(len(addresses_with_transaction))))
        elif wo_transactions:
            if address_type == CurrencyType.eth:
                addresses_eth_wo_transaction = session.query(Address) \
                    .outerjoin(Account, Account.user_id == Address.user_id) \
                    .outerjoin(transaction_counts, transaction_counts.c.address_id == Address.id) \
                    .filter(Address.user_id.isnot(None)) \
                    .filter(or_(Account.document_url != "", Account.is_document_skipped == True)) \
                    .filter(Address.type == CurrencyType.eth) \
                    .filter(func.coalesce(transaction_counts.c.count, 0) == 0) \
                    .filter(Address.id % 2 == 0 if is_even_rows else Address.id % 2 != 0) \
                    .all()  # type: List[Address]

                logging.getLogger(__name__).info("scan_addresses len(addresses_eth_wo_transaction): {}, is_even_rows: {}"
                                                 .format(str(len(addresses_eth_wo_transaction)), is_even_rows))

                addresses_eth_wo_transaction = get_eth_addresses_with_positive_balance(addresses_eth_wo_transaction)
            elif address_type == CurrencyType.btc:
                addresses_btc_wo_transaction = session.query(Address) \
                    .outerjoin(Account, Account.user_id == Address.user_id) \
                    .outerjoin(transaction_counts, transaction_counts.c.address_id == Address.id) \
                    .filter(or_(Account.document_url != "", Account.is_document_skipped == True)) \
                    .filter(Address.type == CurrencyType.btc) \
                    .filter(Address.user_id.isnot(None)) \
                    .filter(func.coalesce(transaction_counts.c.count, 0) == 0) \
                    .filter(Address.id % 2 == 0 if is_even_rows else Address.id % 2 != 0) \
                    .all()  # type: List[Address]

                logging.getLogger(__name__).info("scan_addresses len(addresses_btc_wo_transaction): {}, is_even_rows: {}"
                                                 .format(str(len(addresses_btc_wo_transaction)), is_even_rows))

                addresses_btc_wo_transaction = get_btc_addresses_with_positive_balance(addresses_btc_wo_transaction)


        addresses.extend(addresses_eth_wo_transaction)
        addresses.extend(addresses_btc_wo_transaction)
        addresses.extend(addresses_with_transaction)

        error_addresses = []  # type: list[Address]
        previous_call_time = {}  # type: Dict[str, time]
        for address in addresses:
            # sleep to meet requirements of blockexplorers
            if address.type not in previous_call_time:
                previous_call_time[address.type] = 0

            if address.type == CurrencyType.eth:
                target_timeout = ETHERSCAN_TIMEOUT
            elif address.type == CurrencyType.btc:
                target_timeout = BLOCKCHAININFO_TIMEOUT
            else:
                logging.getLogger(__name__).error("Unknown currency, not able to figure out sleep timeout. Skip it: {}"
                                                  .format(address))
                continue
            if time.time() - previous_call_time[address.type] < target_timeout:
                time.sleep(time.time() - previous_call_time[address.type])

            previous_call_time[address.type] = time.time()

            # Fetch data
            # noinspection PyBroadException
            try:
                if address.type == CurrencyType.eth:
                    transactions = get_eth_investments(address.address)
                elif address.type == CurrencyType.btc:
                    transactions = get_btc_investments(address.address)
                else:
                    logging.getLogger(__name__).error("Cryptocurrency address of unknown type. Skip it: {}"
                                                      .format(address))
                    continue
            except Exception:
                error_addresses.append(address)
                exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
                logging.getLogger(__name__).warning(
                    "Failed fetch new transactions for the {} address {} for due to exception:\n{}"
                    .format(address.type, address.address, exception_str))
                session.rollback()
                continue

            # Persist data to the database
            # noinspection PyBroadException
            try:
                if len(transactions) > 0:
                    for tx in transactions:
                        is_exist = session.query(Transaction) \
                            .filter(Transaction.transaction_id == tx.transaction_id) \
                            .count()  # type: int
                        if is_exist > 0:
                            continue

                        logging.getLogger(__name__).info("Transaction for {} address {} discovered: '{}'"
                                                         .format(address.type, address.address, tx.transaction_id))
                        tx.address = address
                        tx.status = TransactionStatus.success
                        session.add(tx)
                    session.commit()
            except Exception:
                error_addresses.append(address)
                exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
                logging.getLogger(__name__).error(
                    "Failed to persist new transactions for the {} address {} due to exception:\n{}"
                    .format(address.type, address.address, exception_str))
                session.rollback()

        if len(error_addresses) > 0:
            btc_addresses = [a.address for a in error_addresses if a.type == CurrencyType.btc]
            eth_addresses = [a.address for a in error_addresses if a.type == CurrencyType.eth]
            logging.getLogger(__name__).warning("Failed to scan {} addresses because blockexplorer rejected requests:\n{}"
                                              .format(len(error_addresses),
                                                      '\n'.join(btc_addresses + eth_addresses)))

        logging.getLogger(__name__).info("Finished to scan for the new transactions")
    except Exception:
        exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
        logging.getLogger(__name__).error("Failed to scan for new transactions due to exception:\n{}"
                                          .format(exception_str))
        session.rollback()


def get_proxies() -> Dict:
    proxy_url = random.choice(CRAWLER_PROXY__URLS)
    http_url = 'http://{}:{}@{}'.format(CRAWLER_PROXY__USER, CRAWLER_PROXY__PASS, proxy_url)
    https_url = 'https://{}:{}@{}'.format(CRAWLER_PROXY__USER, CRAWLER_PROXY__PASS, proxy_url)
    return {'http': http_url, 'https': https_url}


def get_btc_investments(address_str: str) -> List[Transaction]:
    """
    Get list of BTC transactions for the given address

    :param address_str: Target address
    :type address_str: str
    :return: List of transactions, otherwise exception
    :rtype: list
    """
    proxies = get_proxies()

    txlist_request = 'https://blockchain.info/rawaddr/{}'.format(address_str)
    if CRAWLER_PROXY__ENABLED:
        txlist_response = requests.get(txlist_request, proxies=proxies)
    else:
        txlist_response = requests.get(txlist_request)
    txlist_response.raise_for_status()
    txlist_response_json = txlist_response.json()

    # validate response
    if "address" not in txlist_response_json \
            or type(txlist_response_json['address']) != str \
            or txlist_response_json["address"] != address_str:
        raise ValueError("Wrong 'address' field in response of Blockchain.info for BTC transactions '{}':\n{}"
                         .format(address_str, txlist_response_json))
    if "n_tx" not in txlist_response_json \
            or type(txlist_response_json['n_tx']) != int \
            or "txs" not in txlist_response_json \
            or type(txlist_response_json['txs']) != list \
            or len(txlist_response_json["txs"]) != txlist_response_json["n_tx"]:
        raise ValueError("Wrong 'n_tx'&'txs' fields in response of Blockchain.info for BTC transactions '{}':\n{}"
                         .format(address_str, txlist_response_json))
    for tx in txlist_response_json['txs']:
        if 'hash' not in tx or type(tx['hash']) != str or len(tx['hash']) != 64 \
                or 'vout_sz' not in tx or type(tx['vout_sz']) != int or tx['vout_sz'] < 1 \
                or 'out' not in tx or type(tx['out']) != list or len(tx['out']) != tx['vout_sz'] \
                or 'block_height' not in tx or type(tx['block_height']) != int or tx['block_height'] < 1 \
                or 'time' not in tx or type(tx['time']) != int or tx['time'] < 1:
            raise ValueError("Wrong TX data in response of Blockchain.info for BTC transactions '{}':\n{}"
                             .format(address_str, tx))

        for tx_out in tx['out']:
            if 'value' not in tx_out or type(tx_out['value']) != int or tx_out['value'] < 0:
                raise ValueError("Wrong TX output data in response of Blockchain.info for BTC transactions '{}':\n{}"
                                  .format(address_str, tx_out))

    latestblock_request = 'https://blockchain.info/latestblock'
    if CRAWLER_PROXY__ENABLED:
        latestblock_response = requests.get(latestblock_request, proxies=proxies)
    else:
        latestblock_response = requests.get(latestblock_request)
    latestblock_response.raise_for_status()
    latestblock_response_json = latestblock_response.json()

    # validate response
    if 'hash' not in latestblock_response_json \
            or type(latestblock_response_json['hash']) != str \
            or len(latestblock_response_json['hash']) != 64 \
            or 'height' not in latestblock_response_json \
            or type(latestblock_response_json['height']) != int \
            or latestblock_response_json['height'] < 1:
        raise ValueError("Wrong data in response of Blockchain.info for latest block:\n{}"
                         .format(latestblock_response_json))

    # latest block height
    latestblock = latestblock_response_json['height']

    # get list of transactions
    tx_list = []
    for tx in txlist_response_json['txs']:
        is_investment = False
        for tx_out in tx['out']:
            if 'addr' in tx_out and type(tx_out['addr']) == str and tx_out['addr'].lower() == address_str.lower():
                is_investment = True
                break
        if not is_investment:
            continue

        tx_hash = tx['hash']
        tx_block_height = int(tx['block_height'])
        tx_value = sum(tx_out['value'] for tx_out in tx['out'] if 'addr' in tx_out and tx_out['addr'].lower() == address_str.lower())
        tx_timestamp = datetime.utcfromtimestamp(tx['time'])

        if tx_block_height + 3 > latestblock:
            # not fully confirmed TX
            continue

        transaction_record = Transaction()
        transaction_record.transaction_id = tx_hash
        transaction_record.value = tx_value
        transaction_record.value /= (10 ** 8)
        transaction_record.mined = tx_timestamp
        transaction_record.block_height = tx_block_height
        tx_list.append(transaction_record)

    tx_list = sorted(tx_list, key=lambda x: x.mined)

    return tx_list



def get_eth_investments(address_str: str) -> List[Transaction]:
    """
    Get list of ETH transactions for the given address

    :param address_str: Target address
    :type address_str: str
    :return: List of transactions, otherwise exception
    :rtype: list
    """
    proxies = get_proxies()

    url_base = 'http://api.etherscan.io/api?'
    url_txlist = 'module=account&action=txlist&address={}&startblock=0&endblock=99999999&sort=asc&apikey={}' \
        .format(address_str, ETHERSCAN_API_KEY)
    url_request = url_base + url_txlist

    if CRAWLER_PROXY__ENABLED:
        txlist_response = requests.get(url_request, proxies=proxies)
    else:
        txlist_response = requests.get(url_request)
    txlist_response.raise_for_status()
    txlist_response_json = txlist_response.json()

    # validate
    if 'result' not in txlist_response_json or type(txlist_response_json['result']) != list:
        raise ValueError("Wrong 'result' field in response from Etherscan for ETH transactions '{}':\n{}"
                         .format(address_str, txlist_response_json))
    for tx in txlist_response_json['result']:
        if 'hash' not in tx or type(tx['hash']) != str or len(tx['hash']) == 0 \
                or 'confirmations' not in tx or type(tx['confirmations']) != str or len(tx['confirmations']) == 0 \
                or 'blockNumber' not in tx or type(tx['blockNumber']) != str or len(tx['blockNumber']) == 0 \
                or 'value' not in tx or type(tx['value']) != str or len(tx['value']) == 0 \
                or 'to' not in tx or type(tx['to']) != str or len(tx['to']) == 0 \
                or 'timeStamp' not in tx or type(tx['timeStamp']) != str or len(tx['timeStamp']) == 0:
            raise ValueError("Wrong TX data in response from Etherscan for ETH transactions '{}':\n{}"
                             .format(address_str, tx))

    # get list of transactions
    tx_list = []
    for tx in txlist_response_json['result']:
        tx_hash = tx['hash']
        tx_confirmations = int(tx['confirmations'])
        tx_block_number = int(tx['blockNumber'])
        tx_value = float(tx['value'])
        tx_to = tx['to']
        tx_timestamp = datetime.utcfromtimestamp(int(tx['timeStamp']))

        if tx_confirmations < 12:
            continue
        if tx_block_number < 1:
            continue
        if tx_value <= 0:
            continue
        if tx_to.lower() != address_str.lower():
            continue
        if tx_timestamp < datetime(year=2015, month=7, day=9):
            continue

        transaction_record = Transaction()
        transaction_record.transaction_id = tx_hash
        transaction_record.value = tx_value
        transaction_record.value /= (10 ** 18)
        transaction_record.mined = tx_timestamp
        transaction_record.block_height = tx_block_number
        tx_list.append(transaction_record)

    tx_list = sorted(tx_list, key=lambda x: x.mined)

    return tx_list


#
# Get total JNT tokens
#
def get_total_jnt_amount() -> float:
    total_presale_jnt = session.query(func.coalesce(func.sum(PresaleJnt.jnt_value), 0)) \
        .filter(PresaleJnt.is_sale_allocation == True).as_scalar()

    total_ico_jnt = session.query(func.coalesce(func.sum(JNT.jnt_value), 0)) \
        .filter(JNT.is_sale_allocation == True).as_scalar()

    jnt_sum = session.query(total_presale_jnt + total_ico_jnt) \
        .one()  # type: tuple[float]
    return RAISED_TOKENS_SHIFT + jnt_sum[0]


#
# Create JNT records and notify about new transactions
#

def calculate_jnt_purchases():
    # noinspection PyBroadException
    try:
        logging.getLogger(__name__).info("Start to calculate JNT purchases")

        current_time = datetime.utcnow()

        #if current_time < INVESTMENTS__PUBLIC_SALE__START_DATE:
        #    logging.getLogger(__name__).info("Finished to calculate JNT purchases")
        #    return

        processed_tx_ids = session.query(JNT.transaction_id).subquery()
        records = session.query(Transaction, Account) \
            .outerjoin(Address, Address.id == Transaction.address_id) \
            .outerjoin(Account, Account.user_id == Address.user_id) \
            .filter(not_(Transaction.id.in_(processed_tx_ids))) \
            .filter(not_(and_(Transaction.meta.has_key(Transaction.meta_key_skip_jnt_calculation),
                              Transaction.meta[Transaction.meta_key_skip_jnt_calculation].astext.cast(Boolean) == True))) \
            .all()  # type: List[Tuple[Transaction, Account]]

        for tx, account in records:
            # noinspection PyBroadException
            try:
                if tx.mined >= INVESTMENTS__PUBLIC_SALE__END_DATE.replace(tzinfo=tz.FixedOffsetTimezone(offset=0, name=None)):
                    send_email_transaction_received_sold_out(tx.address.user.email, tx.address.user_id, tx.as_dict())
                    tx.set_skip_jnt_calculation(True)
                    session.commit()
                    continue
                #elif tx.mined < INVESTMENTS__PUBLIC_SALE__START_DATE.replace(tzinfo=tz.FixedOffsetTimezone(offset=0, name=None)):
                #    continue

                currency_to_usd_rate = get_ticker_price(tx.address.type, CurrencyType.usd, tx.mined)
                if currency_to_usd_rate is None:
                    logging.getLogger(__name__).error("Failed to get currency exchange rate. Skip transaction: {}"
                                                      .format(tx))
                    tx.set_skip_jnt_calculation(True)
                    session.commit()
                    continue

                tx_usd_value = tx.value * currency_to_usd_rate
                tx_jnt_value = tx_usd_value / 0.25

                if get_total_jnt_amount() + tx_jnt_value > TOKENS__TOTAL_SUPPLY:
                    send_email_transaction_received_sold_out(tx.address.user.email, tx.address.user_id, tx.as_dict())
                    tx.set_skip_jnt_calculation(True)
                    session.commit()
                    continue

                jnt = JNT()
                jnt.currency_to_usd_rate = currency_to_usd_rate
                jnt.usd_value = tx_usd_value
                jnt.jnt_to_usd_rate = 0.25
                jnt.jnt_value = tx_jnt_value
                jnt.transaction = tx
                jnt.is_sale_allocation = account.is_sale_allocation if account else True

                session.commit()

                send_email_transaction_received(tx.address.user.email, tx.address.user_id,
                                                tx.as_dict(), jnt.as_dict())

                try:
                    on_transaction_received(tx.address.user.account, tx, jnt)
                except Exception:
                    exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
                    logging.getLogger(__name__).error(
                        "Failed GA tracking for TX {} due to exception:\n{}"
                        .format(tx.id, exception_str))

                logging.getLogger(__name__).info("New JNT purchase persisted: {}".format(jnt))
            except Exception:
                exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
                logging.getLogger(__name__).error("Failed to calculate JNT purchases for TX {} due to exception:\n{}"
                                                  .format(tx.id, exception_str))
                session.rollback()

        logging.getLogger(__name__).info("Finished to calculate JNT purchases")
    except Exception:
        exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
        logging.getLogger(__name__).error("Failed to calculate JNT purchases due to exception:\n{}"
                                          .format(exception_str))
        session.rollback()


def get_ticker_price(fixed_currency: str, variable_currency: str, _time) -> Optional[float]:
    td = timedelta(minutes=5)

    price = session.query(Price.value) \
        .filter(Price.fixed_currency == fixed_currency) \
        .filter(Price.variable_currency == variable_currency) \
        .filter(Price.created <= _time + td) \
        .filter(Price.created >= _time - td) \
        .order_by(Price.created.desc()) \
        .first()  # type: Optional[Tuple[float]]

    if price is None:
        return None
    else:
        return price[0]


#
# Notify about docs receiving
#

def scan_docs_received():
    logging.getLogger(__name__).info("Start notify about docs receiving")

    accounts = session.query(Account) \
        .filter(Account.docs_received == True) \
        .filter(Account.notified == False) \
        .order_by(Account.created) \
        .all()

    for account in accounts:
        if send_email_docs_received(account):
            try:
                account.notified = True
                session.commit()
                logging.getLogger(__name__).info("Docs receiving info successfully sent for account '{}'.".format(account.id))
            except Exception as e:
                exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
                logging.getLogger(__name__).error("scan_docs_received: exception :\n{}"
                                                  .format(exception_str))
                session.rollback()
        else:
            logging.getLogger(__name__).error("Failed to send notify about docs receiving '{}'.".format(account.id))

    logging.getLogger(__name__).info("Finished notify about docs receiving")


def get_account_list() -> List[Dict]:
    accounts = session.query(Account) \
        .order_by(Account.created.desc()) \
        .all()  # type: List[Tuple[Account]]

    result = []
    for account in accounts:
        result.append(account.as_dict())

    return result


def get_all_proposals() -> List[Dict]:
    proposals = session.query(Proposal) \
        .order_by(Proposal.created.desc()) \
        .all()  # type: List[Tuple[Proposal]]

    result = []
    for proposal in proposals:
        result.append(proposal.as_dict())

    return result


def get_account_proposals(email: str) -> Tuple[Dict, List[Dict]]:
    records = session.query(Proposal, Account) \
        .join(Account, Account.email == Proposal.email) \
        .filter(Proposal.email == email) \
        .order_by(Proposal.created.desc()) \
        .all()  # type: List[Tuple[Proposal]]

    proposals = []
    account = records[0][1].as_dict() if len(records) > 0 else None

    for record in records:
        proposals.append(record[0].as_dict())

    return account, proposals


def get_all_transactions() -> List[Dict]:
    records = session.query(Transaction, Address, User) \
        .join(Address, Address.id == Transaction.address_id) \
        .join(User, User.id == Address.user_id) \
        .order_by(Transaction.mined.desc()) \
        .all()  # type: List[Tuple[Transaction, Address, User]]

    result = []
    for record in records:
        result.append(record[0].as_dict())

    return result


def get_proposal_transactions(proposal_id: int) -> Tuple[Dict, List[Dict]]:
    records = session.query(Transaction, Address, Proposal) \
        .join(Address, Address.id == Transaction.address_id) \
        .join(Proposal, Proposal.id == Address.proposal_id) \
        .filter(Proposal.id == proposal_id) \
        .order_by(Transaction.mined.desc()) \
        .all()  # type: List[Tuple[Proposal]]

    transactions = []
    proposal = records[0][2].as_dict() if len(records) > 0 else None

    for record in records:
        transactions.append(record[0].as_dict())

    return proposal, transactions


def set_docs_received(account_id: int) -> bool:
    try:
        session.query(Account) \
            .filter(Account.id == account_id) \
            .update({Account.docs_received: True}, synchronize_session=False)
        session.commit()

        return True

    except Exception as e:

        exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
        logging.getLogger(__name__).error("set_docs_received: exception:\n{}"
                                          .format(exception_str))
        session.rollback()

        return False


def fill_address_from_proposal():
    try:
        account_alias = aliased(Account)

        proposalIdSubquery = session.query(func.min(Proposal.id)) \
            .outerjoin(account_alias, Proposal.email == account_alias.email) \
            .filter(account_alias.id.is_(None)) \
            .group_by(Proposal.email)

        subquery = session.query(Proposal.fullname, Proposal.email, Proposal.country, Proposal.citizenship) \
            .filter(Proposal.id.in_(proposalIdSubquery))

        insert_query = insert(Account) \
            .from_select((Account.fullname, Account.email, Account.country, Account.citizenship), subquery)

        session.execute(insert_query)
        session.commit()

    except Exception:

        exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
        logging.getLogger(__name__).error("fill_address_from_proposal: exception:\n{}"
                                          .format(exception_str))
        session.rollback()


#
# Set force_scanning flag to manually issued addresses
#

def set_force_scanning(start_address_id: int, end_address_id: int, is_enable: bool):
    try:
        logging.getLogger(__name__).info("Start to set_force_scanning")

        addresses = session.query(Address) \
            .filter(Address.id >= start_address_id) \
            .filter(Address.id <= end_address_id) \
            .filter(Address.is_usable == False) \
            .order_by(Address.id) \
            .all()

        for address in addresses:
            address.set_force_scanning(is_enable)

        session.commit()
    except Exception:
        exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
        logging.getLogger(__name__).error("Failed to set_force_scanning due to exception:\n{}"
                                          .format(exception_str))
        session.rollback()


#
# Notify about new force_scanning transactions
#

def notify_force_scanning_transactions():
    # noinspection PyBroadException
    try:
        logging.getLogger(__name__).info("Start to notify about force_scanning transactions")

        records = session.query(Address, Transaction) \
            .join(Transaction, Transaction.address_id == Address.id) \
            .filter(Address.is_usable == False) \
            .order_by(Transaction.mined) \
            .all()  # type: List[Tuple[Address, Transaction]]

        for record in records:
            address, transaction = record

            # noinspection PyBroadException
            try:
                if (transaction.get_notified() is False or transaction.get_notified() is None) \
                        and (transaction.get_failed_notifications() is None
                             or transaction.get_failed_notifications() < EMAIL_NOTIFICATIONS__MAX_ATTEMPTS):
                    # notify managers about received tx
                    if (send_email_investment_received_7(transaction)):
                        transaction.set_notified(True)
                        session.commit()
                        logging.getLogger(__name__).info("Managers successfully notified that we received payment: {}"
                                                         .format(transaction))
                    else:
                        failed_notifications = transaction.get_failed_notifications()
                        if failed_notifications is None:
                            failed_notifications = 0
                        failed_notifications += 1
                        transaction.set_failed_notifications(failed_notifications)
                        session.commit()
                        if failed_notifications < EMAIL_NOTIFICATIONS__MAX_ATTEMPTS:
                            logging.getLogger(__name__).warning("Failed to notify managers about received payment: {}"
                                                                .format(transaction))
                        else:
                            logging.getLogger(__name__).error(
                                "All attempts to notify managers about received payment exhausted: {}"
                                    .format(transaction))
            except Exception:
                exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
                logging.getLogger(__name__).error("Failed to notify managers about transaction {} due to exception:\n{}"
                                                  .format(transaction.id, exception_str))
                session.rollback()

        logging.getLogger(__name__).info("Finished to notify managers about force_scanning transactions")
    except Exception:
        exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
        logging.getLogger(__name__).error(
            "Failed to notify managers about force_scanning transactions due to exception:\n{}"
            .format(exception_str))
        session.rollback()


def check_mail_delivery():
    if not CHECK_MAIL_DELIVERY__ENABLED:
        return

    failed_mail_list = get_failed_mails()

    limit_dt = datetime.utcnow() - timedelta(days=CHECK_MAIL_DELIVERY__DAYS_DEPTH)

    proposals = session.query(Proposal) \
        .filter(Proposal.meta[Proposal.meta_key_notified].astext.cast(Boolean) == True) \
        .filter(Proposal.meta[Proposal.meta_key_mailgun_message_id].astext != "") \
        .filter(Proposal.created >= limit_dt) \
        .all()  # type: List[Proposal]

    for proposal in proposals:
        # noinspection PyBroadException
        try:
            if proposal.get_mailgun_message_id() in failed_mail_list:
                proposal.set_mailgun_delivered("failed")
                session.commit()
                logging.getLogger(__name__).error(
                    "Mail delivery failed. Message_id: {}\nProposal: {}".format(proposal.get_mailgun_message_id(), proposal))

        except Exception:

            exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
            logging.getLogger(__name__).error(
                "Failed to check mail delivery due to exception:\n{}".format(exception_str))
            session.rollback()

    transactions = session.query(Transaction) \
        .filter(Transaction.meta[Transaction.meta_key_notified].astext.cast(Boolean) == True) \
        .filter(Transaction.meta[Transaction.meta_key_mailgun_message_id].astext != "") \
        .filter(Transaction.mined >= limit_dt) \
        .all()  # type: List[Transaction]

    for transaction in transactions:
        # noinspection PyBroadException
        try:
            if transaction.get_mailgun_message_id() in failed_mail_list:
                transaction.set_mailgun_delivered("failed")
                session.commit()
                logging.getLogger(__name__).error(
                    "Mail delivery failed. Message_id: {}\nProposal: {}".format(proposal.get_mailgun_message_id(), proposal))

        except Exception:

            exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
            logging.getLogger(__name__).error(
                "Failed to check mail delivery due to exception:\n{}".format(exception_str))
            session.rollback()


#
# Assign BTC/ETH addresses for a user
#

def assign_addresses(user_id: int) -> bool:
    # noinspection PyBroadException
    try:
        logging.getLogger(__name__).info("Start assign addresses for a user with ID '{}'"
                                         .format(user_id))

        user = session.query(User) \
            .filter(User.id == user_id) \
            .one()  # type: User

        if user is None:
            return False

        for currency in [CurrencyType.btc, CurrencyType.eth]:
            addressIdSubquery = session.query(Address.id) \
                .filter(Address.type == currency) \
                .filter(Address.is_usable == True) \
                .filter(Address.user_id.is_(None)) \
                .order_by(Address.id) \
                .limit(1) \
                .subquery()
            session.query(Address) \
                .filter(Address.id.in_(addressIdSubquery)) \
                .update({Address.user_id: user_id}, synchronize_session=False)

        session.commit()

        logging.getLogger(__name__).info("Addresses assigned for a user with ID '{}'"
                                         .format(user_id))

        return True

    except Exception:
        exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
        logging.getLogger(__name__).error("Failed assign addresses due to error:\n{}"
                                          .format(exception_str))

        session.rollback()

        return False


def withdraw_processing():
    # noinspection PyBroadException
    try:
        logging.getLogger(__name__).info("Start to process new withdraws")

        pending_withdraws = session.query(Withdraw) \
            .filter(Withdraw.status == TransactionStatus.pending) \
            .filter(Withdraw.transaction_id != "") \
            .order_by(Withdraw.id) \
            .all()  # type: List[Withdraw]

        _limit_count = ETH_CONTRACT__MAX_PENDING_COUNT - len(pending_withdraws)

        if _limit_count <= 0:
            logging.getLogger(__name__).info("Finished to process new withdraws. Over the limit.")
            return

        withdraws = session.query(Withdraw) \
            .filter(Withdraw.status == TransactionStatus.confirmed) \
            .filter(or_(Withdraw.transaction_id == "",
                        Withdraw.transaction_id.is_(None))) \
            .order_by(Withdraw.id) \
            .limit(_limit_count)  # type: List[Withdraw]

        for withdraw in withdraws:
            try:
                tx_id = mintJNT(withdraw.to, withdraw.value)
                if tx_id:
                    withdraw.transaction_id = tx_id
                    withdraw.status = TransactionStatus.pending
                    session.commit()
                    logging.getLogger(__name__).info(
                            "Process withdraw. withdraw_id: {}".format(withdraw.id))
                else:
                    logging.getLogger(__name__).error(
                        "Process withdraw failed. withdraw_id: {}".format(withdraw.id))
            except Exception:
                exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
                logging.getLogger(__name__).error(
                    "Failed to process withdraw due to exception:\n{}".format(exception_str))
                session.rollback()

        logging.getLogger(__name__).info("Finished to process new withdraws")
    except Exception:
        exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
        logging.getLogger(__name__).error("Failed to process withdraws due to exception:\n{}"
                                          .format(exception_str))
        session.rollback()


def check_withdraw_transactions():
    """
    Check Contract Execution Status
    """
    # noinspection PyBroadException
    try:
        logging.getLogger(__name__).info("Start to check withdraw transactions")

        withdraws = session.query(Withdraw) \
            .filter(Withdraw.status == TransactionStatus.pending) \
            .filter(Withdraw.transaction_id != "") \
            .order_by(Withdraw.id) \
            .all()  # type: List[Withdraw]

        for withdraw in withdraws:
            tx_info = getTransactionInfo(withdraw.transaction_id)

            if tx_info and tx_info.get("status"):
                if tx_info["status"] == '0x1':
                    send_email_withdrawal_request_succeeded(withdraw.user.email,
                                                            withdraw.user_id,
                                                            withdraw.as_dict())
                    withdraw.status = TransactionStatus.success
                elif tx_info["status"] == '0x0':
                    withdraw.status = TransactionStatus.fail
            try:
                session.commit()
            except Exception:
                exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
                logging.getLogger(__name__).error(
                    "Failed to check withdraw transaction status due to exception:\n{}".format(exception_str))
                session.rollback()

        logging.getLogger(__name__).info("Finished checking withdraw transactions")
    except Exception:
        exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
        logging.getLogger(__name__).error("Failed to check withdraw transactions due to exception:\n{}"
                                          .format(exception_str))
        session.rollback()


#
# Persist withdraw operation of JNT to the database
#

def add_withdraw_jnt(user_id: int) -> Optional[int]:
    # noinspection PyBroadException
    try:
        logging.getLogger(__name__).info("Start persist withdraw operation of JNT to the database. account_id: {}"
                                         .format(user_id))
        account = session.query(Account) \
            .filter(Account.user_id == user_id) \
            .one()  # type: Account

        addresses = session.query(Address) \
            .filter(Address.user_id == user_id).all()
        assert len(addresses) == 2, 'User has {} addresses, not 2'.format(len(addresses))
        addresses_ids = [a.id for a in addresses]

        if not account or not addresses:
            logging.getLogger(__name__).error(
                "Invalid user_id: {}".format(user_id))
            session.rollback()
            return None

        total_jnt = session.query(func.coalesce(func.sum(JNT.jnt_value), 0)) \
            .outerjoin(Transaction, Transaction.id == JNT.transaction_id) \
            .outerjoin(Address, Address.id == Transaction.address_id) \
            .filter(Address.id.in_(addresses_ids), Transaction.status == TransactionStatus.success).as_scalar()

        total_presale_jnt = session.query(func.coalesce(func.sum(PresaleJnt.jnt_value), 0)) \
            .filter(PresaleJnt.user_id == user_id).as_scalar()

        total_withdraw_jnt = session.query(func.coalesce(func.sum(Withdraw.value), 0)) \
            .filter(Withdraw.user_id == user_id).as_scalar()

        withdrawable_balance = session.query(total_jnt + total_presale_jnt - total_withdraw_jnt).one()
        if withdrawable_balance[0] <= 0.0:
            session.rollback()
            return None

        insert_query = insert(Withdraw) \
            .values(user_id=user_id,
                    status=TransactionStatus.not_confirmed,
                    to=account.withdraw_address,
                    value=total_jnt + total_presale_jnt - total_withdraw_jnt,
                    transaction_id='')

        result = session.execute(insert_query)
        session.commit()

        logging.getLogger(__name__).info("Finished to persist withdraw operation of JNT to the database. account_id: {}"
                                         .format(user_id))

        return result.inserted_primary_key[0]
    except Exception:
        exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
        logging.getLogger(__name__).error(
            "Failed to persist withdraw operation to the database due to exception:\n{}".format(exception_str))
        session.rollback()
        return None


#
# Persist notification to the database
#

def add_notification(email: str, type: str, user_id: Optional[int] = None, data: Optional[dict] = None):
    # noinspection PyBroadException
    try:
        logging.getLogger(__name__).info("Start persist notification to the database. email: {}, user_id: {}"
                                         .format(email, user_id))

        if user_id:
            user = session.query(User) \
                .filter(User.id == user_id) \
                .all()  # type: User
            assert len(user) == 1, 'Invalid user_id: {}'.format(user_id)

        notification = Notification(user_id=user_id if user_id else None,
                                    type=type,
                                    email=email,
                                    meta=data if data else {})

        session.add(notification)
        session.commit()

        logging.getLogger(__name__).info("Finished to persist notification to the database. email: {}, account_id: {}"
                                         .format(email, user_id))

        return True
    except Exception:
        exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
        logging.getLogger(__name__).error(
            "Failed to persist notification to the database due to exception:\n{}".format(exception_str))
        session.rollback()
        return False


def send_email_transaction_received(email: str, user_id: int, transaction: dict,
                                    jnt: dict, type: Optional[str] = NotificationType.transaction_received) -> bool:
    ctx = {
        'jnt_id': jnt['id'],
        'transaction_id': transaction['id'],
        'transaction_jnt_amount': format_jnt_value(jnt['jnt_value']),
        'transaction_usd_amount': format_fiat_value(jnt['usd_value']),
        'transaction_currency_amount': format_coin_value(transaction['value']),
        'transaction_currency_name': transaction['currency'],
        'transaction_currency_conversion_rate': format_conversion_rate(jnt['currency_to_usd_rate']),
    }

    return add_notification(email, user_id=user_id, type=type, data=ctx)


def send_email_withdrawal_request(email: str, user_id: int, withdraw: dict,
                                  type: Optional[str] = NotificationType.withdrawal_request) -> bool:
    ctx = {
        'withdraw_id': withdraw['id'],
        'withdraw_address': withdraw['to'],
        'withdraw_jnt_amount': format_jnt_value(withdraw['value']),
    }
    return add_notification(email, user_id=user_id, type=type, data=ctx)


def send_email_transaction_received_sold_out(email: str, user_id: int, transaction: dict) -> bool:
    ctx = {
        'transaction_id': transaction['id'],
        'account_email': email,
        'transaction_currency_amount': format_coin_value(transaction['value']),
        'transaction_currency_name': transaction['currency'],
    }

    success_user = add_notification(email, user_id=user_id, type=NotificationType.transaction_received_sold_out, data=ctx)
    success_support = add_notification(EMAIL_NOTIFICATIONS__SUPPORT_ADDRESS, user_id=user_id, type=NotificationType.transaction_received_sold_out_admin, data=ctx)

    return success_user and success_support


def send_email_withdrawal_request_succeeded(email: str, user_id: int, withdraw: dict) -> bool:
    return send_email_withdrawal_request(email=email, user_id=user_id, withdraw=withdraw,
                                         type=NotificationType.withdrawal_succeeded)


#
# Build invalid withdraw addresses report
#

def check_withdraw_addresses() -> int:
    logging.getLogger(__name__).info("Start checking withdraw addresses.")

    accounts = session.query(Account) \
        .filter(Account.withdraw_address.isnot(None)) \
        .filter(Account.withdraw_address != "") \
        .order_by(Account.id) \
        .all()  # type: List[Account]

    print(" *** Results ***")
    print("id\temail\twithdraw_address\n")

    invalid_addresses_count = 0
    for account in accounts:
        if not is_valid_address(account.withdraw_address):
            print(account.id, "\t", account.user.username, "\t", account.withdraw_address)
            invalid_addresses_count += 1

    print("\nTotal number of invalid addresses is : {}".format(invalid_addresses_count))

    logging.getLogger(__name__).info("Finished checking withdraw addresses.")
    return invalid_addresses_count
