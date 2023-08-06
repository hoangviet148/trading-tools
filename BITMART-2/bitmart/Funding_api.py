from .client import Client
from .consts import *


class FundingAPI(Client):

    def __init__(self, api_key, api_secret_key, memo):
        Client.__init__(self, api_key, api_secret_key, memo)

    # Get Deposit Address
    def get_deposit_address(self, currency):
        params = {
            "currency": currency        }
        return self._request_with_params(GET, DEPOSIT_ADDRESS, params)

    # Get Balance
    def get_balances(self, currency):
        params = {'currency': currency}
        return self._request_with_params(GET, GET_BALANCES, params)

    # Get Account Configuration
    def funds_transfer(self, nonce, asset, amount, From, to):
        params = {"nonce": nonce, "asset": asset, "amount": amount, "from": From, "to": to}
        return self._request_with_params(POST, FUNDS_TRANSFER, params)

    # Withdrawal

    #def coin_withdraw(self, nonce, asset, key, amount):
        #params = {'nonce': nonce, 'asset': asset, 'key': key, 'amount': amount}
        #return self._request_with_params(POST, WITHDRAWAL_COIN, params)

    '''
    {
        "currency": "USDT-TRC20",
        "amount": "100.000",
        "destination": "To Digital Address",
        "address": "0x1EE6FA5A3803608fc22a1f3F76********",
        "address_memo": ""
    }'
    '''

    # Withdrawal

    def coin_withdraw(self, token, amount, destination, address):
        params = {"currency": token, "amount": amount,  'destination': destination, "address": address, "address_memo": ""}
        return self._request_with_params(POST, WITHDRAWAL_COIN, params)

    # Get Deposit History
    def get_deposit_history(self, currency, operation_type, N):
        params = {
            "currency": currency,
            "operation_type": operation_type,
            "N": N
        }
        return self._request_with_params(GET, DEPOSIT_WITHDRAW_HISTORIY, params)

    # def get_deposit_history(self, txId):
    #     params = {'txId': txId, 'limit': 50}
    #     return self._request_with_params(GET, DEPOSIT_HISTORIY, params)

    # Get Withdrawal History
    def get_withdrawal_history(self, operation_type, N):
        params = {
            "operation_type": operation_type,
            "N": N
        }
        return self._request_with_params(GET, DEPOSIT_WITHDRAW_HISTORIY, params)

    # def get_withdrawal_history(self, wdId):
    #     params = {'wdId': wdId}
    #     return self._request_with_params(GET, WITHDRAWAL_HISTORIY, params)

    # Get Currencies
    def get_currency(self):
        print("=== Funding_api.get_currency ===")
        return self._public_request(GET, CURRENCY_INFO)

    def get_withdrawal_info(self, nonce=None, asset=None, key=None, amount=None):
        params = {'nonce': nonce, 'asset': asset, 'key': key, 'amount': amount}
        return self._request_with_params(POST, WITHDRAWAL_INFO, params)

    # PiggyBank Purchase/Redemption
    def purchase_redempt(self, ccy, amt, side):
        params = {'ccy': ccy, 'amt': amt, 'side': side}
        return self._request_with_params(POST, PURCHASE_REDEMPT, params)

    # Get Withdrawal History
    def get_bills(self, ccy=None, type=None, after=None, before=None, limit=None):
        params = {'ccy': ccy, 'type': type, 'after': after,
                  'before': before, 'limit': limit}
        return self._request_with_params(GET, BILLS_INFO, params)
