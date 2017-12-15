import sys
import os
import json
import logging
from typing import Tuple, Optional
from decimal import Decimal
import traceback

import rlp
from ethereum import transactions
from ethereum import utils
from ethereum import abi
from eth_utils import currency, hexidecimal

from jco.commonutils.ethjsonrpc import EthJsonRpc


# Ethereum settings
ETH_NODE__ADDRESS = ""
ETH_NETWORK__ID = 3
ETH_MANAGER__PRIVATE_KEY = ""
ETH_MANAGER__ADDRESS = ""

ETH_CONTRACT__MAX_PENDING_COUNT = 50
ETH_CONTRACT__GAZ_MULTIPLICATOR = 1.2
ETH_CONTRACT__ADDRESS = ""
ETH_CONTRACT__ABI = b'[{"constant": false, "inputs": [{"name": "_account", "type": "address"},' \
                    b'{"name": "_value", "type": "uint256"}], "name": "mint", "outputs": [], "payable": false,' \
                    b'"type": "function"}]'

class Contract:
    def __init__(self, host: str, expectedNetworkId: int):
        self._host = host  # type: str
        self._networkId = int(expectedNetworkId)  # type: int
        self._ethJsonRpc = EthJsonRpc(self._host, tls=True)  # type: EthJsonRpc


    @classmethod
    def signTransaction(cls,
                        privateKey: str,
                        to: str,
                        value: int,
                        nonce: int,
                        gasPrice: int,
                        gas: int,
                        data: str = "",
                        network_id: int = 3) -> Optional[str]:
        """
        https://ethereum.stackexchange.com/questions/3386/create-and-sign-offline-raw-transactions
        """

        txObj = transactions.Transaction(nonce, gasPrice, gas, to, value, data)
        signedTxObj = txObj.sign(privateKey, network_id)
        rlpObj = rlp.encode(signedTxObj)
        hexEncoded = rlpObj.hex()
        hexEncoded = '0x' + hexEncoded

        return hexEncoded


    @classmethod
    def encodeFunctionTxData(cls, abi_json, functionName, args) -> Optional[str]:
        ct = abi.ContractTranslator(abi_json)
        txdata = ct.encode_function_call(functionName, args)

        return txdata


    def sendRawTransaction(self, txData) -> Optional[str]:
        return self._ethJsonRpc.eth_sendRawTransaction(txData)


    def getNonce(self, address: str) -> Tuple[Optional[int], Optional[int]]:
        _latest = self._ethJsonRpc.eth_getTransactionCount(address)
        _pending = self._ethJsonRpc.eth_getTransactionCount(address, 'pending')

        return (_latest, _pending)


    def getGasPrice(self) -> Decimal:
        return self._ethJsonRpc.eth_gasPrice()


    def getGasLimit(self, to_address: str, from_address: str, data: str) -> Decimal:
        return self._ethJsonRpc.eth_estimateGas(to_address=to_address, from_address=from_address, data=data)


    def sendRawTransaction(self, _sign_data: str) -> str:
        return self._ethJsonRpc.eth_sendRawTransaction(_sign_data)


    def getTransactionReceipt(self, _tx_id: str) -> Optional[dict]:
        return self._ethJsonRpc.eth_getTransactionReceipt(_tx_id)


def mintJNT(to_address: str, value: float) -> str:
    try:
        logging.getLogger(__name__).info("Start mintJNT to:{}, value:{}".format(to_address, value))

        contract = Contract(ETH_NODE__ADDRESS, ETH_NETWORK__ID)

        _value_wei = currency.to_wei(value, 'ether')

        _abi = ETH_CONTRACT__ABI
        _tx_data = Contract.encodeFunctionTxData(_abi,
                                                 "mint",
                                                 [to_address, _value_wei])

        _tx_nonce_latest, _tx_nonce_pending = contract.getNonce(ETH_MANAGER__ADDRESS)
        _tx_gas_price = int(contract.getGasPrice() * ETH_CONTRACT__GAZ_MULTIPLICATOR)
        _tx_gas_limit = contract.getGasLimit(ETH_CONTRACT__ADDRESS,
                                             ETH_MANAGER__ADDRESS,
                                             hexidecimal.encode_hex(_tx_data))

        _tx_sign_data = Contract.signTransaction(privateKey=ETH_MANAGER__PRIVATE_KEY,
                                                 to=ETH_CONTRACT__ADDRESS,
                                                 value=0,
                                                 nonce=_tx_nonce_pending,
                                                 gasPrice=_tx_gas_price,
                                                 gas=_tx_gas_limit,
                                                 data=_tx_data,
                                                 network_id=ETH_NETWORK__ID)

        try:
            _tx_id = contract.sendRawTransaction(_tx_sign_data)
        except Exception:
            exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
            logging.getLogger(__name__).error("Failed mintJNT due to exception:\n{}"
                                              .format(exception_str))
            return None

        logging.getLogger(__name__).info("Finished mintJNT to:{}, value:{}".format(to_address, value))

        return _tx_id
    except Exception:
        exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
        logging.getLogger(__name__).error("Failed mintJNT due to exception:\n{}"
                                          .format(exception_str))
        return None


def getTransactionInfo(tx_id: str) -> Optional[dict]:
    try:
        contract = Contract(ETH_NODE__ADDRESS, ETH_NETWORK__ID)

        return contract.getTransactionReceipt(tx_id)
    except Exception:
        exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
        logging.getLogger(__name__).error("Failed getTransactionInfo due to exception:\n{}"
                                          .format(exception_str))
        return None