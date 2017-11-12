import unittest
import time
import logging.config

from jco.appprocessor.notify import *


class TestEmailsSending(unittest.TestCase):
    _logger = logging.getLogger('unittest')

    def testEmails(self):
        recipient = "victor@jibrel.network"

        #
        # First proposal
        #

        p1 = Proposal()
        p1.id = 130
        p1.fullname = "John Doe"
        p1.email = recipient
        p1.country = "Germany"
        p1.citizenship = "Singapore"
        p1.currency = CurrencyType.eth
        p1.amount = 30
        p1.proposal_id = generate_request_id()
        p1.created = datetime(year=2017, month=10, day=10, hour=3, minute=39, second=51)
        p1.set_notified(False)

        a1 = Address()
        a1.id = 270
        a1.address = '0xF89b090614e75Bd3A0F11C9956c78A5c3c6Cc3e2'
        a1.type = CurrencyType.eth
        a1.proposal_id = 130
        a1.proposal = p1

        t10 = Transaction()
        t10.id = 310
        t10.transaction_id = '0xe90cb6cce493729dc42d1af2c12b91abf5a922cb1d450cff2dcd6c95bdad80bb'
        t10.value = 30
        t10.mined = datetime(year=2017, month=10, day=10, hour=10, minute=39, second=51)
        t10.set_notified(False)
        t10.address_id = 270
        t10.address = p1.address

        jnt_purchase_10 = JNT()
        jnt_purchase_10.id = 310
        jnt_purchase_10.purchase_id = generate_purchase_id()
        jnt_purchase_10.currency_to_usd_rate = 298.1876
        jnt_purchase_10.usd_value = t10.value * jnt_purchase_10.currency_to_usd_rate
        jnt_purchase_10.jnt_to_usd_rate = 0.225
        jnt_purchase_10.jnt_value = jnt_purchase_10.usd_value / jnt_purchase_10.jnt_to_usd_rate
        jnt_purchase_10.active = True
        jnt_purchase_10.created = datetime(year=2017, month=10, day=10, hour=10, minute=39, second=51)
        jnt_purchase_10.transaction_id = 310
        jnt_purchase_10.transaction = t10

        #
        # Second proposal
        #

        p2 = Proposal()
        p2.id = 131
        p2.fullname = "John Doe"
        p2.email = recipient
        p2.country = "Germany"
        p2.citizenship = "Singapore"
        p2.currency = CurrencyType.usd
        p2.amount = 5000
        p2.proposal_id = generate_request_id()
        p2.created = datetime.now()
        p2.set_notified(False)

        #
        # Third proposal
        #

        p3 = Proposal()
        p3.id = 132
        p3.fullname = "John Doe"
        p3.email = recipient
        p3.country = "Germany"
        p3.citizenship = "Singapore"
        p3.currency = CurrencyType.eth
        p3.amount = 300
        p3.proposal_id = generate_request_id()
        p3.created = datetime(year=2017, month=10, day=9, hour=8, minute=39, second=51)
        p3.set_notified(False)

        a3 = Address()
        a3.id = 275
        a3.address = '0x4C34aE54Dc716808e94Af3d1d638b8EA3A23fA9B'
        a3.type = CurrencyType.eth
        a3.proposal_id = 132
        a3.proposal = p3
        a3.transactions = []

        t30 = Transaction()
        t30.id = 313
        t30.transaction_id = '0xc5a57cb0ae72a26846c10448743c12d16f3d479a20ae005db21a77a381785885'
        t30.value = 3.22148
        t30.mined = datetime(year=2017, month=10, day=10, hour=11, minute=27, second=32)
        t30.set_notified(False)
        t30.address_id = 275
        t30.address = p3.address

        jnt_purchase_30 = JNT()
        jnt_purchase_30.id = 313
        jnt_purchase_30.purchase_id = generate_purchase_id()
        jnt_purchase_30.currency_to_usd_rate = 315.1
        jnt_purchase_30.usd_value = t30.value * jnt_purchase_30.currency_to_usd_rate
        jnt_purchase_30.jnt_to_usd_rate = 0.225
        jnt_purchase_30.jnt_value = jnt_purchase_30.usd_value / jnt_purchase_30.jnt_to_usd_rate
        jnt_purchase_30.active = True
        jnt_purchase_30.created = datetime(year=2017, month=10, day=10, hour=11, minute=27, second=32)
        jnt_purchase_30.transaction_id = 313
        jnt_purchase_30.transaction = t30

        t31 = Transaction()
        t31.id = 314
        t31.transaction_id = '0x3068f278710838160cc66c4d043735404076bcfe2c79edf0743565632ac51506'
        t31.value = 1.0758
        t31.mined = datetime(year=2017, month=10, day=10, hour=11, minute=46, second=11)
        t31.set_notified(False)
        t31.address_id = 275
        t31.address = p3.address

        jnt_purchase_31 = JNT()
        jnt_purchase_31.id = 314
        jnt_purchase_31.purchase_id = generate_purchase_id()
        jnt_purchase_31.currency_to_usd_rate = 290
        jnt_purchase_31.usd_value = t31.value * jnt_purchase_31.currency_to_usd_rate
        jnt_purchase_31.jnt_to_usd_rate = 0.225
        jnt_purchase_31.jnt_value = jnt_purchase_31.usd_value / jnt_purchase_31.jnt_to_usd_rate
        jnt_purchase_31.active = True
        jnt_purchase_31.created = datetime(year=2017, month=10, day=10, hour=11, minute=46, second=11)
        jnt_purchase_31.transaction_id = 314
        jnt_purchase_31.transaction = t31

        t32 = Transaction()
        t32.id = 315
        t32.transaction_id = '0x94caee00e198be7ca52f348239b18ef95b4f4569e79057fb47f45dd55a1e469f'
        t32.value = 18.45351888
        t32.mined = datetime(year=2017, month=10, day=10, hour=11, minute=44, second=45)
        t32.set_notified(False)
        t32.address_id = 275
        t32.address = p3.address

        jnt_purchase_32 = JNT()
        jnt_purchase_32.id = 315
        jnt_purchase_32.purchase_id = generate_purchase_id()
        jnt_purchase_32.currency_to_usd_rate = 327
        jnt_purchase_32.usd_value = t32.value * jnt_purchase_32.currency_to_usd_rate
        jnt_purchase_32.jnt_to_usd_rate = 0.225
        jnt_purchase_32.jnt_value = jnt_purchase_32.usd_value / jnt_purchase_32.jnt_to_usd_rate
        jnt_purchase_32.active = True
        jnt_purchase_32.created = datetime(year=2017, month=10, day=10, hour=11, minute=46, second=11)
        jnt_purchase_32.transaction_id = 315
        jnt_purchase_32.transaction = t32

        t33 = Transaction()
        t33.id = 316
        t33.transaction_id = '0x542e4ce0ac64fc63886abd14a6d394c48c60a17dcb1fcc6d131a9f2c84d77d5b'
        t33.value = 13784
        t33.mined = datetime(year=2017, month=10, day=10, hour=12, minute=16, second=31)
        t33.set_notified(False)
        t33.address_id = 275
        t33.address = p3.address

        jnt_purchase_33 = JNT()
        jnt_purchase_33.id = 316
        jnt_purchase_33.purchase_id = generate_purchase_id()
        jnt_purchase_33.currency_to_usd_rate = 342
        jnt_purchase_33.usd_value = t33.value * jnt_purchase_33.currency_to_usd_rate
        jnt_purchase_33.jnt_to_usd_rate = 0.225
        jnt_purchase_33.jnt_value = jnt_purchase_33.usd_value / jnt_purchase_33.jnt_to_usd_rate
        jnt_purchase_33.active = True
        jnt_purchase_33.created = datetime(year=2017, month=10, day=10, hour=12, minute=16, second=31)
        jnt_purchase_33.transaction_id = 316
        jnt_purchase_33.transaction = t33

        #
        # Fourth proposal
        #

        p4 = Proposal()
        p4.id = 137
        p4.fullname = "John Doe"
        p4.email = recipient
        p4.country = "Germany"
        p4.citizenship = "Singapore"
        p4.currency = CurrencyType.eth
        p4.amount = 300
        p4.proposal_id = generate_request_id()
        p4.created = datetime(year=2017, month=10, day=8, hour=1, minute=12, second=13)
        p4.set_notified(False)

        a4 = Address()
        a4.id = 280
        a4.address = '0x4C34aE54Dc716808e94Af3d1d638b8EA3A23fA9B'
        a4.type = CurrencyType.eth
        a4.proposal_id = 137
        a4.proposal = p4
        a4.transactions = []

        t40 = Transaction()
        t40.id = 323
        t40.transaction_id = '0x61939a1d6749206a2b688dd04dc058c7e82df797248a3100e77889b4999855d4'
        t40.value = 21895
        t40.mined = datetime(year=2017, month=10, day=8, hour=17, minute=15, second=34)
        t40.set_notified(False)
        t40.address_id = 280
        t40.address = p4.address

        jnt_purchase_40 = JNT()
        jnt_purchase_40.id = 323
        jnt_purchase_40.purchase_id = generate_purchase_id()
        jnt_purchase_40.currency_to_usd_rate = 317.1234
        jnt_purchase_40.usd_value = t40.value * jnt_purchase_40.currency_to_usd_rate
        jnt_purchase_40.jnt_to_usd_rate = 0.225
        jnt_purchase_40.jnt_value = jnt_purchase_40.usd_value / jnt_purchase_40.jnt_to_usd_rate
        jnt_purchase_40.active = True
        jnt_purchase_40.created = datetime(year=2017, month=10, day=8, hour=17, minute=15, second=34)
        jnt_purchase_40.transaction_id = 323
        jnt_purchase_40.transaction = t40

        #
        # send emails
        #

        success, message_id = send_email_payment_data_crypto(p1, config.INVESTMENTS__USD__MIN_LIMIT)
        self.assertEqual(success, True)
        self.assertIsNotNone(message_id)
        time.sleep(1)

        success, message_id = send_email_investment_received_1(p1.address.transactions[0])
        self.assertEqual(success, True)
        self.assertIsNotNone(message_id)
        time.sleep(1)

        success, message_id = send_email_payment_data_fiat(p2, config.INVESTMENTS__USD__MIN_LIMIT)
        self.assertEqual(success, True)
        self.assertIsNotNone(message_id)
        time.sleep(1)

        success, message_id = send_email_investment_received_3(p3.address.transactions[0],
                                                   config.INVESTMENTS__USD__MIN_LIMIT,
                                                   config.INVESTMENTS__PUBLIC_SALE__START_DATE,
                                                   config.INVESTMENTS__PUBLIC_SALE__END_DATE)
        self.assertEqual(success, True)
        self.assertIsNotNone(message_id)
        time.sleep(1)

        success, message_id = send_email_investment_received_4(p3.address.transactions[1],
                                                   [p3.address.transactions[0],
                                                    p3.address.transactions[1]],
                                                   config.INVESTMENTS__USD__MIN_LIMIT,
                                                   config.INVESTMENTS__PUBLIC_SALE__START_DATE,
                                                   config.INVESTMENTS__PUBLIC_SALE__END_DATE)
        self.assertEqual(success, True)
        self.assertIsNotNone(message_id)
        time.sleep(1)

        success, message_id = send_email_investment_received_2(p3.address.transactions[2],
                                                   [p3.address.transactions[0],
                                                    p3.address.transactions[1],
                                                    p3.address.transactions[2]])
        self.assertEqual(success, True)
        self.assertIsNotNone(message_id)
        time.sleep(1)

        success, message_id = send_email_investment_received_6(p3.address.transactions[3],
                                                   [p3.address.transactions[0],
                                                    p3.address.transactions[1],
                                                    p3.address.transactions[2],
                                                    p3.address.transactions[3]],
                                                   config.INVESTMENTS__USD__MAX_LIMIT,
                                                   config.INVESTMENTS__PUBLIC_SALE__START_DATE,
                                                   config.INVESTMENTS__PUBLIC_SALE__END_DATE)
        self.assertEqual(success, True)
        self.assertIsNotNone(message_id)
        time.sleep(1)

        success, message_id = send_email_investment_received_5(p4.address.transactions[0],
                                                   config.INVESTMENTS__USD__MAX_LIMIT,
                                                   config.INVESTMENTS__PUBLIC_SALE__START_DATE,
                                                   config.INVESTMENTS__PUBLIC_SALE__END_DATE)
        self.assertEqual(success, True)
        self.assertIsNotNone(message_id)


if __name__ == '__main__':
    unittest.main()
