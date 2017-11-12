import unittest
from datetime import datetime
import time
import logging
from hashlib import *
from base58 import *


import requests
from sqlalchemy.types import Boolean
from sqlalchemy.sql.expression import not_, or_

from jco.commonconfig.config import INVESTMENTS__TOKEN_PRICE_IN_USD, FORCE_SCANNING_ADDRESS__ENABLED
from jco.appdb.models import *
from jco.appdb.db import session
from jco.commonutils.utils import *
from jco.commonutils.app_init import initialize_app
from jco.appprocessor.commands import (
    generate_eth_addresses,
    generate_btc_addresses,
    fetch_tickers_price,
    fetch_ticker_price,
    add_proposal,
    get_ticker_price,
    send_email_payment_data,
    transaction_processing,
    get_proxies,
    get_btc_investments,
    get_eth_investments,
    fill_address_from_proposal,
    scan_addresses,
    set_force_scanning,
    notify_force_scanning_transactions,
    check_mail_delivery,
    get_account_list,
    get_all_proposals,
    get_all_transactions
)


class TestCommands(unittest.TestCase):
    def clear_all_tables(selfself):
        session.query(JNT).delete()
        session.query(Transaction).delete()
        session.query(Price).delete()
        session.query(Address).delete()
        session.query(Proposal).delete()
        session.query(Account).delete()
        session.commit()

    @initialize_app
    def setUp(self):
        self.clear_all_tables()
        self.mnemonic = "panel random cargo number belt faint pave dignity various glare able segment shy connect agent cruise service burst tenant space unhappy amused immune start"

    def tearDown(self):
        self.clear_all_tables()

    def test_generate_eth_addresses(self):
        address_num = 10
        generate_eth_addresses(self.mnemonic, address_num)
        addresses = session.query(Address) \
            .filter(Address.proposal_id.is_(None)) \
            .filter(Address.type == CurrencyType.eth) \
            .filter(Address.address != "") \
            .order_by(Address.id) \
            .all()  # type: List[Address]
        self.assertEqual(len(addresses), address_num, "count of finding address records must be 10")

        self.assertEqual(addresses[0].address, '0x7039D52049134cA39ff431bF11e439cBbe281BFF',
                         "addresses must match BIP44 specs")
        self.assertEqual(addresses[1].address, '0xf404d1942cE1e4F10fA638616c5A0F3acEc31FF8',
                         "addresses must match BIP44 specs")
        self.assertEqual(addresses[2].address, '0xA3EB7cE1D9083c7138Cff55cE7b9a442203fF2e6',
                         "addresses must match BIP44 specs")
        self.assertEqual(addresses[3].address, '0xe85D953B19ec1b3846D5F611FC7DB6dAe3676FD8',
                         "addresses must match BIP44 specs")
        self.assertEqual(addresses[4].address, '0x885809a510865320314b971A43BA436c8dff1980',
                         "addresses must match BIP44 specs")
        self.assertEqual(addresses[5].address, '0x22AF2deC86eb46e4159e389b8b27AFC3d1a8272B',
                         "addresses must match BIP44 specs")
        self.assertEqual(addresses[6].address, '0xcEe9D3f99A8EB1902a35d4EE1cD79833105F6A03',
                         "addresses must match BIP44 specs")
        self.assertEqual(addresses[7].address, '0x186Ac92f077A8C1d35EAF029D78529a8049E5937',
                         "addresses must match BIP44 specs")
        self.assertEqual(addresses[8].address, '0xBe47225AA301Ba8D59eb1AF40bC12ca63f682613',
                         "addresses must match BIP44 specs")
        self.assertEqual(addresses[9].address, '0xA22C1B0cB8BfE9AB0f54A25494100233ED989959',
                         "addresses must match BIP44 specs")
        address_types = set(address.type for address in addresses)
        self.assertEqual(len(address_types), 1, "must generate Ethereum addresses")
        self.assertEqual(address_types.pop(), 'ETH', "must generate Ethereum addresses")

    def test_generate_btc_addresses(self):
        address_num = 10
        generate_btc_addresses(self.mnemonic, address_num)
        addresses = session.query(Address) \
            .filter(Address.proposal_id.is_(None)) \
            .filter(Address.type == CurrencyType.btc) \
            .filter(Address.address != "") \
            .order_by(Address.id) \
            .all()  # type: List[Address]
        self.assertEqual(len(addresses), address_num, "count of finding address records must be 10")

        self.assertEqual(addresses[0].address, '1PXTe9LKPK7gNN997v3cQtCuNpiCRQSrdW', "addresses must match BIP44 specs")
        self.assertEqual(addresses[1].address, '1CWKsFYaTRb5UEmYagSgjB3B6J3p2YtmYe', "addresses must match BIP44 specs")
        self.assertEqual(addresses[2].address, '1Gw2TkJZhSSzJQ2dovuaGbTGYCiEJyG3BJ', "addresses must match BIP44 specs")
        self.assertEqual(addresses[3].address, '132So6N4Jk15kUFGdc5Qc2BMroo8JdJj1Z', "addresses must match BIP44 specs")
        self.assertEqual(addresses[4].address, '1E3U2h4WfyzEBXt9YMfVHTgpkYYNhs5986', "addresses must match BIP44 specs")
        self.assertEqual(addresses[5].address, '1473EW5B4EfQ1aYF77pG6PMAcjPN5CLFDD', "addresses must match BIP44 specs")
        self.assertEqual(addresses[6].address, '1FvpkA2ewvFJFRi5DyUfeVqn97KVWwWmZH', "addresses must match BIP44 specs")
        self.assertEqual(addresses[7].address, '1Gqddc2vvAW4btCCixCZnn8REuZUftymzw', "addresses must match BIP44 specs")
        self.assertEqual(addresses[8].address, '1BwZcHSKteQRzEiUR4G6y9yLd5Yv4FCJPz', "addresses must match BIP44 specs")
        self.assertEqual(addresses[9].address, '13WbDQz1tXAhfd41XYjCMx9C9wBU65yAp3', "addresses must match BIP44 specs")
        address_types = set(address.type for address in addresses)
        self.assertEqual(len(address_types), 1, "must generate Bitcoin addresses")
        self.assertEqual(address_types.pop(), 'BTC', "must generate Bitcoin addresses")

    def test_fetch_tickers_price(self):
        fetch_tickers_price()
        btc_prices = session.query(Price) \
            .filter(Price.fixed_currency == CurrencyType.btc) \
            .filter(Price.value > 0) \
            .all()  # type: List[Price]
        self.assertEqual(len(btc_prices), 1, "count of finding BTC price records must be 1")

        eth_prices = session.query(Price) \
            .filter(Price.fixed_currency == CurrencyType.eth) \
            .filter(Price.value > 0) \
            .all()  # type: List[Price]
        self.assertEqual(len(eth_prices), 1, "count of finding ETH price records must be 1")

    def test_fetch_ticker_price(self):
        fetch_ticker_price(CurrencyType.eth, CurrencyType.usd, "ethusd")
        prices = session.query(Price) \
            .filter(Price.fixed_currency == CurrencyType.eth) \
            .filter(Price.value > 0) \
            .all()  # type: List[Price]
        self.assertEqual(len(prices), 1, "Number of found ETH price records must be 1")

        # wrong ticker name
        fetch_ticker_price(CurrencyType.btc, CurrencyType.usd, "eth_usd")
        prices = session.query(Price) \
            .filter(Price.fixed_currency == CurrencyType.btc) \
            .filter(Price.value > 0) \
            .all()  # type: List[Price]
        self.assertEqual(len(prices), 0, "wrong tickers should not be allowed")

    def test_add_proposal(self):
        fullname = "John Doe"
        email = "aleksey.selikhov@gmail.com"
        country = "USA"
        citizenship = "USA"
        currency = CurrencyType.eth
        amount = 100000

        success, message = add_proposal(fullname, email, country, citizenship, currency, amount, None)
        self.assertEqual(success, False, "should have failed")

        proposals = session.query(Proposal) \
            .filter(Proposal.fullname == fullname) \
            .filter(Proposal.email == email) \
            .filter(Proposal.country == country) \
            .filter(Proposal.citizenship == citizenship) \
            .filter(Proposal.currency == currency) \
            .filter(Proposal.amount == amount) \
            .filter(Proposal.created.isnot(None)) \
            .filter(or_(not_(Proposal.meta.has_key(Proposal.meta_key_notified)),
                        Proposal.meta[Proposal.meta_key_notified].astext.cast(Boolean) == False)) \
            .all()  # type: List[Proposal]
        self.assertEqual(len(proposals), 1)

        fullname = "Freeman A"
        generate_eth_addresses(self.mnemonic, 1)

        success, address_str = add_proposal(fullname, email, country, citizenship, currency, amount, None)
        self.assertEqual(success, True, "should have succeeded")
        self.assertTrue(address_str != "", "address can not be an empty")

        proposals = session.query(Proposal) \
            .filter(Proposal.fullname == fullname) \
            .filter(Proposal.email == email) \
            .filter(Proposal.country == country) \
            .filter(Proposal.citizenship == citizenship) \
            .filter(Proposal.currency == currency) \
            .filter(Proposal.amount == amount) \
            .filter(Proposal.created.isnot(None)) \
            .filter(or_(not_(Proposal.meta.has_key(Proposal.meta_key_notified)),
                        Proposal.meta[Proposal.meta_key_notified].astext.cast(Boolean) == False)) \
            .all()  # type: List[Proposal]
        self.assertEqual(len(proposals), 1)

        addresses = session.query(Address) \
            .filter(Address.proposal_id == proposals[0].id) \
            .all()  # type: List[Address]
        self.assertEqual(len(addresses), 1)
        self.assertEqual(addresses[0].address, address_str)

    def test_get_ticker_price(self):
        fetch_tickers_price()
        current_time = datetime.utcnow()

        price = get_ticker_price(CurrencyType.eth, CurrencyType.usd, current_time)
        self.assertTrue(price > 0, "ETH price must be greater than 0")

        price = get_ticker_price(CurrencyType.btc, CurrencyType.usd, current_time)
        self.assertTrue(price > 0, "BTC price must be greater than 0")

        price = get_ticker_price("eur", CurrencyType.usd, current_time)
        self.assertTrue(price is None, "wrong currencies should not be allowed")

    def test_send_email_payment_data(self):
        fullname = "John Doe"
        email = "aleksey.selikhov@gmail.com"
        country = "USA"
        citizenship = "USA"
        currency = CurrencyType.eth
        amount = 100000

        generate_eth_addresses(self.mnemonic, 1)
        add_proposal(fullname, email, country, citizenship, currency, amount, None)

        send_email_payment_data()

        proposals = session.query(Proposal) \
            .filter(Proposal.fullname == fullname) \
            .filter(Proposal.email == email) \
            .filter(Proposal.country == country) \
            .filter(Proposal.citizenship == citizenship) \
            .filter(Proposal.currency == currency) \
            .filter(Proposal.amount == amount) \
            .filter(Proposal.created.isnot(None)) \
            .all()  # type: List[Proposal]
        # .filter(Proposal.meta[Proposal.meta_key_notified].astext.cast(Boolean) == True) \

        self.assertEqual(len(proposals), 1, "should have notified")
        self.assertIsNotNone(proposals[0].get_mailgun_message_id())

    def test_proxies_work(self):
        proxies = get_proxies()
        print('PPP', proxies)
        our_ip_request = requests.get("http://checkip.amazonaws.com/")
        our_ip_request.raise_for_status()
        our_ip = our_ip_request.text.strip()
        proxy_ip_request = requests.get("http://checkip.amazonaws.com/", proxies=proxies)
        proxy_ip_request.raise_for_status()
        proxy_ip = proxy_ip_request.text.strip()
        self.assertNotEqual(our_ip, proxy_ip, "Proxies must hide the IP address")

        https_response = requests.get("https://bitcoin.com", proxies=proxies)
        https_response.raise_for_status()
        http_response = requests.get("http://bitcoin.com", proxies=proxies)
        http_response.raise_for_status()
        self.assertTrue(True, 'test finished successfully')

    def test_get_btc_investments(self):
        btc_address_str = '1HEVUxtxGjGnuRT5NsamD6V4RdUduRHqFv'

        btc_transactions = get_btc_investments(btc_address_str)  # type: List[Transaction]

        self.assertEqual(len(btc_transactions), 4, "must be a nonempty transactions list")

        self.assertEqual(btc_transactions[0].transaction_id,
                         "57119a5ccea2bffc90d86ae28385dc21a4055d6a9d69bffab02a581c159f520d")
        self.assertEqual(btc_transactions[0].value, 11.2147)
        self.assertEqual(btc_transactions[0].mined, datetime(2015, 11, 22, 23, 59, 28))
        self.assertEqual(btc_transactions[0].block_height, 384878)

        self.assertEqual(btc_transactions[1].transaction_id,
                         "cb33f55b02859045a791e2613cdf9b7a59c0073c899b0aa29d97112d8020d068")
        self.assertEqual(btc_transactions[1].value, 0.225)
        self.assertEqual(btc_transactions[1].mined, datetime(2016, 1, 5, 18, 28, 5))
        self.assertEqual(btc_transactions[1].block_height, 391910)

        self.assertEqual(btc_transactions[2].transaction_id,
                         "2b37bc49849743232d4a40d9a9736f3f71ab3eda81915b3d69b8ae34e29d8140")
        self.assertEqual(btc_transactions[2].value, 0.52172715)
        self.assertEqual(btc_transactions[2].mined, datetime(2016, 1, 5, 21, 49, 32))
        self.assertEqual(btc_transactions[2].block_height, 391930)

        self.assertEqual(btc_transactions[3].transaction_id,
                         "66bd3b522a7bbfc970cb31ab9a0563461e3eb038a43fca9fc5850f0fc0870440")
        self.assertEqual(btc_transactions[3].value, 15.41866072)
        self.assertEqual(btc_transactions[3].mined, datetime(2016, 1, 5, 21, 51, 21))
        self.assertEqual(btc_transactions[3].block_height, 391930)

    def test_get_eth_investments(self):
        eth_address_str = '0x3BA2E2565dB2c018aDd0b24483fE99fC2cCCDa8e'

        eth_transactions = get_eth_investments(eth_address_str)  # type: List[Transaction]

        self.assertEqual(len(eth_transactions), 4, "must be a nonempty transactions list")

        self.assertEqual(eth_transactions[0].transaction_id,
                         "0xbbdb03ea3ac6dc2a65dd1f483f9637efd7aaf945acd7588aec7e5105ae798893")
        self.assertEqual(eth_transactions[0].value, 0.06017582)
        self.assertEqual(eth_transactions[0].mined, datetime(2017, 7, 7, 13, 42, 27))
        self.assertEqual(eth_transactions[0].block_height, 3988250)

        self.assertEqual(eth_transactions[1].transaction_id,
                         "0x731b0381aa22ac16a533af873c525f7d0dc8f934be2ff4de5f4d7a04fed6218a")
        self.assertEqual(eth_transactions[1].value, 0.05034514)
        self.assertEqual(eth_transactions[1].mined, datetime(2017, 7, 9, 4, 49, 20))
        self.assertEqual(eth_transactions[1].block_height, 3996534)

        self.assertEqual(eth_transactions[2].transaction_id,
                         "0x81c5e6f75e975178637e429f895dee7a7843dd95590a76c2e2fdf5aa61921fc2")
        self.assertEqual(eth_transactions[2].value, 0.05026789)
        self.assertEqual(eth_transactions[2].mined, datetime(2017, 7, 10, 20, 45, 23))
        self.assertEqual(eth_transactions[2].block_height, 4004591)

        self.assertEqual(eth_transactions[3].transaction_id,
                         "0x328ae8cfe80a5ae103b2acf8119f6e8c5e1d76b6b9ec3b5655225d10ce67d295")
        self.assertEqual(eth_transactions[3].value, 0.05038922)
        self.assertEqual(eth_transactions[3].mined, datetime(2017, 7, 12, 18, 37, 33))
        self.assertEqual(eth_transactions[3].block_height, 4013231)

    def test_transaction_processing(self):
        # fetch last prices BTC and ETH
        fetch_tickers_price()

        generate_eth_addresses(self.mnemonic, 2)

        nonusable_address = session.query(Address).limit(1).one()
        nonusable_address.is_usable = False
        session.commit()

        success, address_str = add_proposal("John Doe", "aleksey.selikhov@gmail.com", "USA", "USA", CurrencyType.eth,
                                            100000, None)
        addresses = session.query(Address) \
            .filter(Address.address == address_str) \
            .all()  # type: List[Address]

        transaction_id = "0xffaaaddcc"
        transaction_value = 20000000000000000000
        transaction_mined = datetime.utcnow()
        eth_currency_rate = get_ticker_price(CurrencyType.eth, CurrencyType.usd, transaction_mined)

        self.assertTrue(eth_currency_rate > 0, "eth_currency_rate must be greater than 0")

        jnt_usd_value = transaction_value * eth_currency_rate / (10 ** 18)

        self.assertTrue(jnt_usd_value > 0, "transaction_usd_value must be greater than 0")

        transaction_1 = Transaction(transaction_id=transaction_id,
                                    value=transaction_value,
                                    address_id=nonusable_address.id,
                                    mined=transaction_mined,
                                    block_height=2)
        session.add(transaction_1)
        session.commit()

        transaction_id = "0xffaaaddcce"
        transaction_2 = Transaction(transaction_id=transaction_id,
                                    value=transaction_value,
                                    address_id=addresses[0].id,
                                    mined=transaction_mined,
                                    block_height=2)

        jnt_2 = JNT(currency_to_usd_rate=eth_currency_rate,
                    jnt_value=jnt_usd_value / INVESTMENTS__TOKEN_PRICE_IN_USD,
                    usd_value=jnt_usd_value,
                    jnt_to_usd_rate=INVESTMENTS__TOKEN_PRICE_IN_USD,
                    purchase_id=generate_request_id())

        jnt_2.transaction = transaction_2
        session.add(transaction_2)
        session.add(jnt_2)
        session.commit()

        transaction_processing()

        transaction = session.query(Transaction) \
            .filter(Transaction.id == transaction_1.id) \
            .one()  # type: Transaction
        self.assertEqual(transaction.get_notified(), None, "should have not notified")

        transaction = session.query(Transaction) \
            .filter(Transaction.id == transaction_2.id) \
            .one()  # type: Transaction
        self.assertEqual(transaction.get_notified(), True, "should have notified")
        self.assertIsNotNone(transaction.get_mailgun_message_id())

        time.sleep(2)

        transaction_id = "0xffaaaddcd"
        transaction_mined = datetime.utcnow()
        transaction_3 = Transaction(transaction_id=transaction_id,
                                    value=transaction_value,
                                    address_id=addresses[0].id,
                                    mined=transaction_mined,
                                    block_height=3)

        jnt_3 = JNT(currency_to_usd_rate=eth_currency_rate,
                    jnt_value=jnt_usd_value / INVESTMENTS__TOKEN_PRICE_IN_USD,
                    usd_value=jnt_usd_value,
                    jnt_to_usd_rate=INVESTMENTS__TOKEN_PRICE_IN_USD,
                    purchase_id=generate_request_id())

        jnt_3.transaction = transaction_3

        session.add(transaction_3)
        session.add(jnt_3)
        session.commit()

        transaction_processing()

        transaction = session.query(Transaction) \
            .filter(Transaction.id == transaction_3.id) \
            .one()  # type: Transaction
        self.assertEqual(transaction.get_notified(), True, "should have notified")
        self.assertIsNotNone(transaction.get_mailgun_message_id())

    def test_fill_address_from_proposal(self):

        generate_eth_addresses(self.mnemonic, 4)

        address_1 = "test1@test.com"
        address_2 = "test2@test.com"
        address_3 = "test3@test.com"
        address_4 = "test4@test.com"
        address_5 = "test5@test.com"

        fullname = "John Doe"
        country = "USA"
        citizenship = "USA"

        add_proposal(fullname, address_1, country, citizenship, CurrencyType.eth, 100000, None)
        add_proposal(fullname, address_2, country, citizenship, CurrencyType.eth, 100000, None)

        proposal_3 = Proposal(fullname=fullname, email=address_3, country=country, citizenship=citizenship,
                              currency=CurrencyType.eth, amount=100000, proposal_id='JNT-PRESALE-REQUEST-1')

        proposal_4 = Proposal(fullname=fullname, email=address_4, country=country, citizenship=citizenship,
                              currency=CurrencyType.eth, amount=100000, proposal_id='JNT-PRESALE-REQUEST-2')

        proposal_5 = Proposal(fullname=fullname, email=address_5, country=country, citizenship=citizenship,
                              currency=CurrencyType.eth, amount=100000, proposal_id='JNT-PRESALE-REQUEST-3')

        proposal_6 = Proposal(fullname=fullname, email=address_5, country="GB", citizenship="GB",
                              currency=CurrencyType.eth, amount=100000, proposal_id='JNT-PRESALE-REQUEST-4')

        session.add(proposal_3)
        session.add(proposal_4)
        session.add(proposal_5)
        session.add(proposal_6)
        session.commit()

        proposals = session.query(Proposal).all()
        self.assertEqual(len(proposals), 6)

        account_1 = Account(fullname=fullname, email=address_3, country=country, citizenship=citizenship)
        account_2 = Account(fullname=fullname, email=address_4, country=country, citizenship=citizenship)

        session.add(account_1)
        session.add(account_2)
        session.commit()

        accounts = session.query(Account).all()
        self.assertEqual(len(accounts), 4)

        fill_address_from_proposal()

        accounts = session.query(Account).all()
        self.assertEqual(len(accounts), 5)

    def test_scan_addresses(self):
        nonusable_address = Address(address='0xC28142C80cFFE11086A334402ecFF4517898DCec',
                                    type=CurrencyType.eth,
                                    is_usable=False)
        nonusable_address.set_force_scanning(True)
        session.add(nonusable_address)

        usable_address = Address(address='1FctpG14EZosqFCJCKivKUtFHT7eycRpk7',
                                 type=CurrencyType.btc)
        session.add(usable_address)
        session.commit()

        success, address_str = add_proposal("John Doe", "aleksey.selikhov@gmail.com", "USA", "USA", CurrencyType.btc,
                                            100000, None)
        self.assertEqual(success, True, "proposal must be created")

        scan_addresses()

        eth_transactions = session.query(Address, Transaction) \
            .filter(Address.id > 0 if FORCE_SCANNING_ADDRESS__ENABLED else Address.proposal_id.isnot(None)) \
            .filter(Address.type == CurrencyType.eth) \
            .all()

        self.assertTrue(len(eth_transactions) > 0 if FORCE_SCANNING_ADDRESS__ENABLED else len(eth_transactions) == 0,
                        "must be a nonempty ETH transactions list" if FORCE_SCANNING_ADDRESS__ENABLED else "must be an empty ETH transactions list")

        btc_transactions = session.query(Address, Transaction) \
            .filter(Address.id > 0 if FORCE_SCANNING_ADDRESS__ENABLED else Address.proposal_id.isnot(None)) \
            .filter(Address.type == CurrencyType.eth) \
            .all()

        self.assertTrue(len(btc_transactions) > 0, "must be a nonempty BTC transactions list")

    def test_set_force_scanning(self):
        nonusable_address_1 = Address(address='0xC28142C80cFFE11086A334402ecFF4517898DCec',
                                      type=CurrencyType.eth,
                                      is_usable=False)
        nonusable_address_1.set_force_scanning(True)
        session.add(nonusable_address_1)

        nonusable_address_2 = Address(address='0xC28142C80cFFE11086A334402ecFF4517898DCed',
                                      type=CurrencyType.eth,
                                      is_usable=False)
        nonusable_address_2.set_force_scanning(True)
        session.add(nonusable_address_2)

        usable_address = Address(address='1FctpG14EZosqFCJCKivKUtFHT7eycRpk7', type=CurrencyType.btc)
        session.add(usable_address)
        session.commit()

        set_force_scanning(nonusable_address_1.id, nonusable_address_2.id, True)

        addresses = session.query(Address) \
            .filter(Address.meta[Address.meta_key_force_scanning].astext.cast(Boolean) == True) \
            .all()

        self.assertTrue(len(addresses) == 2, "should have force_scanning")

    def test_notify_force_scanning_transactions(self):
        usable_address_1 = Address(address='0x9af2351170ad84cc44549db629bf23c652450f30',
                                   type=CurrencyType.eth,
                                   is_usable=True)
        session.add(usable_address_1)
        session.commit()

        add_proposal("John Doe", "aleksey.selikhov@gmail.com", "USA", "USA", CurrencyType.eth, 100000, None)

        nonusable_address_1 = Address(address='0xC28142C80cFFE11086A334402ecFF4517898DCec',
                                      type=CurrencyType.eth,
                                      is_usable=False)
        nonusable_address_1.set_force_scanning(True)
        session.add(nonusable_address_1)

        nonusable_address_2 = Address(address='1FctpG14EZosqFCJCKivKUtFHT7eycRpk7',
                                      type=CurrencyType.btc,
                                      is_usable=False)
        session.add(nonusable_address_2)
        session.commit()

        scan_addresses()

        notify_force_scanning_transactions()

        addresses = session.query(Transaction) \
            .filter(Transaction.meta[Transaction.meta_key_notified].astext.cast(Boolean) == False) \
            .all()

        self.assertTrue(len(addresses) == 0, "all transactions should have notified")

    def test_chek_mail_delivery(self):

        proposal_1 = Proposal(fullname="John Doe",
                              email="aleksey.selikhov",
                              country="USA",
                              citizenship="USA",
                              currency=CurrencyType.eth,
                              amount=100000,
                              proposal_id="JNT-PRESALE-REQUEST-1")
        proposal_1.set_notified(True)
        proposal_1.set_mailgun_message_id("20171018133300.65429.0E4C7AB4268AB64C@mailgun.jibrel.network")
        session.add(proposal_1)
        session.commit()

        address_1 = Address(address="0xC28142C80cFFE11086A334402ecFF4517898DCec",
                            type=CurrencyType.eth,
                            is_usable=True,
                            proposal_id=proposal_1.id)
        session.add(address_1)
        session.commit()

        transaction_1 = Transaction(transaction_id="0xffaaaddcc",
                                    value=1000,
                                    address_id=address_1.id,
                                    mined=datetime.utcnow(),
                                    block_height=3)
        transaction_1.set_notified(True)
        transaction_1.set_mailgun_message_id("20171017185500.85006.5524BED71BE6AA6A@mailgun.jibrel.network")
        session.add(transaction_1)
        session.commit()

        check_mail_delivery()

        transactions = session.query(Transaction) \
            .filter(Transaction.meta[Transaction.meta_key_mailgun_delivered].astext == "failed") \
            .all()  # type: List[Transaction]

        self.assertTrue(len(transactions) == 1)

        proposals = session.query(Proposal) \
            .filter(Transaction.meta[Transaction.meta_key_mailgun_delivered].astext == "failed") \
            .all()  # type: List[Transaction]

        self.assertTrue(len(proposals) == 1)

    def test_get_account_list(self):
        generate_eth_addresses(self.mnemonic, 3)
        add_proposal("Test1", "test1@test", "USA", "USA", CurrencyType.eth, 100000, None)
        add_proposal("Test2", "test2@test", "USA", "USA", CurrencyType.eth, 100000, None)
        add_proposal("Test3", "test3@test", "USA", "USA", CurrencyType.eth, 100000, None)

        addresses = session.query(Address) \
            .all()  # type: List[Address]

        self.assertTrue(len(addresses) == 3)

        account_list = get_account_list()
        self.assertTrue(len(account_list) == 3)

        success = True

        key_list = ['id', 'fullname', 'email', 'country', 'citizenship', 'created', 'notified', 'docs_received']

        for account in account_list:
            if not all(_key in key_list for _key in account.keys()):
                success = False
                break

        self.assertTrue(success, "some keys not present in account")

    def test_get_all_proposals(self):
        generate_eth_addresses(self.mnemonic, 3)
        add_proposal("Test1", "test1@test", "USA", "USA", CurrencyType.eth, 100000, None)
        add_proposal("Test2", "test2@test", "USA", "USA", CurrencyType.eth, 100000, None)
        add_proposal("Test3", "test3@test", "USA", "USA", CurrencyType.eth, 100000, None)

        proposals = session.query(Proposal) \
            .all()  # type: List[Proposal]

        self.assertTrue(len(proposals) == 3)

        proposal_list = get_all_proposals()
        self.assertTrue(len(proposal_list) == 3)

        success = True

        key_list = ['id', 'fullname', 'email', 'country', 'citizenship', 'currency',
                    'amount', 'proposal_id', 'created', 'address',
                    'mailgun_message_id', 'mailgun_delivered']

        for prposal in proposal_list:
            if not all(_key in key_list for _key in prposal.keys()):
                success = False
                break

        self.assertTrue(success, "some keys not present in proposal")

    def test_get_all_transactions(self):
        # fetch last prices BTC and ETH
        fetch_tickers_price()

        generate_eth_addresses(self.mnemonic, 2)

        add_proposal("Test1", "test1@test", "USA", "USA", CurrencyType.eth, 100000, None)
        add_proposal("Test2", "test2@test", "USA", "USA", CurrencyType.eth, 200000, None)

        addresses = session.query(Address) \
            .all()  # type: List[Address]

        self.assertTrue(len(addresses) == 2)

        transaction_id = "0xffaaaddcc"
        transaction_value = 20000000000000000000
        transaction_mined = datetime.utcnow()
        eth_currency_rate = get_ticker_price(CurrencyType.eth, CurrencyType.usd, transaction_mined)
        jnt_usd_value = transaction_value * eth_currency_rate / (10 ** 18)

        transaction_1 = Transaction(transaction_id=transaction_id,
                                    value=transaction_value,
                                    address_id=addresses[0].id,
                                    mined=transaction_mined,
                                    block_height=2)

        transaction_id = "0xffaaaddcce"

        transaction_2 = Transaction(transaction_id=transaction_id,
                                    value=transaction_value,
                                    address_id=addresses[1].id,
                                    mined=transaction_mined,
                                    block_height=2)

        session.add(transaction_1)
        session.add(transaction_2)
        session.commit()

        transactions = session.query(Transaction) \
            .all()  # type: List[Transaction]
        self.assertTrue(len(transactions) == 2)

        transaction_list = get_all_transactions()
        self.assertTrue(len(transaction_list) == 2)

        success = True

        key_list = ['id', 'transaction_id', 'value', 'mined',
                    'block_height', 'address_id', 'address',
                    'proposal', 'mailgun_message_id', 'mailgun_delivered']

        for transaction in transaction_list:
            if not all(_key in key_list for _key in transaction.keys()):
                success = False
                break

        self.assertTrue(success, "some keys not present in transaction")


if __name__ == '__main__':
    unittest.main()
