import unittest
import time
import logging.config

from jco.commonutils.bitfinex import Bitfinex


class TestBitfinexWrapper(unittest.TestCase):
    _logger = logging.getLogger('unittest')

    def testGetTicker(self):
        self._logger.info('Start to test Bitfinex wrapper')
        startTime = time.time()

        bitfinexWrapper = Bitfinex()

        btcusdTickerData = bitfinexWrapper.get_ticker('btcusd')
        self.assertIsInstance(btcusdTickerData, dict, 'Ticker data should be an dict')
        self.assertEqual({'ask', 'timestamp', 'bid', 'last_price', 'mid'}, set(btcusdTickerData.keys()),
                         'Ticker data should contain all expected fields')
        self.assertLess(btcusdTickerData['bid'], 15000, 'BTC/USD conversion rate should be less than 15000 BTC/USD')
        self.assertGreater(btcusdTickerData['bid'], 1000, 'BTC/USD conversion rate should be greater than 1000 BTC/USD')

        ethusdTickerData = bitfinexWrapper.get_ticker('ethusd')
        self.assertIsInstance(ethusdTickerData, dict, 'Ticker data should be an dict')
        self.assertEqual({'ask', 'timestamp', 'bid', 'last_price', 'mid'}, set(ethusdTickerData.keys()),
                         'Ticker data should contain all expected fields')
        self.assertLess(ethusdTickerData['bid'], 1000, 'ETH/USD conversion rate should be less than 1000 ETH/USD')
        self.assertGreater(ethusdTickerData['bid'], 100, 'ETH/USD conversion rate should be greater than 100 ETH/USD')

        finishTime = time.time()
        testTime = finishTime - startTime
        self._logger.info('Finished to test Bitfinex wrapper in {} seconds.'.format(testTime))
