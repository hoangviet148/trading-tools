from .client import Client
from .consts import *


class FundingAPI(Client):

    def __init__(self, api_key, api_secret_key):
        Client.__init__(self, api_key, api_secret_key)

    def get_list_deposit_address(self, currency):
        request_path = f"{LIST_DEPOSIT_ADDRESS}/{currency}"
        return self._request_without_params(GET, request_path)

    # Get Deposit Address
    def get_deposit_address(self, currencyBinding):
        params = {
            "currencyBinding": currencyBinding        
        }
        return self._request_with_params(POST, DEPOSIT_ADDRESS, params)

    # Get Balance
    def get_balances(self, currency, type_):
        request_path = f"{GET_BALANCES}/{currency}/{type_}"
        print(f"test=== {request_path}")
        return self._request_without_params(GET, request_path)

    # Get Account Configuration
    def funds_transfer(self, nonce, asset, amount, From, to):
        params = {"nonce": nonce, "asset": asset, "amount": amount, "from": From, "to": to}
        return self._request_with_params(POST, FUNDS_TRANSFER, params)

    # Withdrawal

    def coin_withdraw(self, currencyBinding, amount, destinationAddress):
        params = {
            'currencyBinding': currencyBinding, 
            'amount': amount, 
            'recipientAddress': destinationAddress
        }
        return self._request_with_params(POST, WITHDRAWAL_COIN, params)

    # Get Deposit History
    def get_deposit_withdrawal_history(self, id):
        request_path = f"{DEPOSIT_WITHDRAW_HISTORIY}/{id}"
        return self._request_without_params(GET, request_path)

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
