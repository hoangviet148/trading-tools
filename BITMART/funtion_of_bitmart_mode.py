import sys
import datetime
import json
import requests
import time
import cloudscraper
from concurrent.futures import ThreadPoolExecutor
from lib2to3.pgen2 import token
from unittest import result
import os
# import pandas as pd

import bitmart.Account_api as Account
import bitmart.Funding_api as Funding
import bitmart.Market_api as Market
import bitmart.Public_api as Public
import bitmart.Trade_api as Trade
import bitmart.subAccount_api as SubAccount
import bitmart.status_api as Status

import logging
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
# from decouple import config

scraper = cloudscraper.create_scraper()
path_file = os.path.dirname(os.path.abspath(__file__))

flag = '0'


class BITMART_FUNCTION:
    def __init__(self, keypass=None):
        print("Init")
        if keypass != None:

            # NHẬP KEY, SECRET của API
            self.api_key = '5326ea6315dcf6901df0ab6cc40bd156473baefe'
            self.api_secret = '1f1424dfbdcc9bc36aa4b2a9cad9c6dcb9cc43f7e22302b223a4bf79ec028a03'

            self.FundingAPI = Funding.FundingAPI(
                self.api_key, self.api_secret)
            self.TradeAPI = Trade.TradeAPI(
                self.api_key, self.api_secret)
            self.AccountAPI = Account.AccountAPI(
                self.api_key, self.api_secret)
            self.MarketAPI = Market.MarketAPI(
                self.api_key, self.api_secret)
            print("Init Done")

    # Tìm xem 1 số có bao nhiêu số sau dấu phẩy
    def get_decimal_token_cefi(self, number):
        string_number = str(number)
        if "." in string_number:
            decimal_places = len(string_number) - string_number.index('.') - 1
            # print(decimal_places)
        else:
            decimal_places = 0
            # print(decimal_places)
        return decimal_places

    # Chuyển 1 số thành dạng tối đa có 3 số sau dấu phẩy
    def convert_number_to_smaller(self, number):
        decimal_places = self.get_decimal_token_cefi(number)
        if decimal_places == 0:
            return number
        if decimal_places > 3:
            decimal_places = 3
        number = int(float(number)*(10**int(decimal_places))) / \
            (10**int(decimal_places))
        return number

    def get_balances_bitmart(self, currency):  # Check số dư của 1 token trên sàn
        while True:
            try:
                res = self.FundingAPI.get_balances(currency=currency)
                print("res", res)
                if res['data']['wallet'] == []:
                    balance = 0
                else:
                    balance = res['data']['wallet']['available']
                break
            except:
                time.sleep(1)
                continue

        # print("balance_trading ", balance_trading)
        return self.convert_number_to_smaller(float(balance))

    # Lấy danh sách các lệnh đang được đặt trên sàn
    def get_depth_bitmart(self, symbol, usd, proxy, fake_ip):
        token = (symbol + "_" + usd).upper()
        url = "https://api-cloud.bitmart.com/spot/v1/symbols/book"
        params = {
            'symbol': token        
        }
        try:
            if fake_ip == True:
                proxies = {
                    'http': str(proxy),
                    'https': str(proxy)
                }
                res = requests.get(url, params=params, proxies=proxies, timeout=5)
            else:
                res = requests.get(url, params=params, timeout=5).json()

            # print(f"=== {res['data']} ===")
            if res['code'] != 1000:
                return 0
            else:
                return res['data']
        except Exception as e:
            print("Exception: ", e)
            return 0

    # Kiểm tra nếu dùng 1 số usd thì mua được bao nhiêu đồng coin
    def get_return_buy_bitmart(self, symbol, usd, amountin, proxy, fake_ip):
        result = self.get_depth_bitmart(symbol, usd, proxy, fake_ip)
        # print("result ", result)
        try:
            list_asks = result['buys']
            print("list_buys ", list_asks)
        except:
            return 0
        sum_value_ask = 0
        total_volume = 0
        for ask in list_asks:
            # print(ask)
            sum_value_ask = sum_value_ask + float(ask['price'])*float(ask['amount'])
            total_volume = total_volume + float(ask['amount'])
            if float(sum_value_ask) >= float(amountin):
                # print(ask)
                tien_con_thieu = amountin - \
                    (sum_value_ask - float(ask['price'])*float(ask['amount']))
                # print("tien_con_thieu ", tien_con_thieu)
                total_return = total_volume - \
                    float(ask['amount']) + tien_con_thieu/float(ask['price'])
                # print("total_return", total_return)
                return float(total_return)*(100-0.1)/100
        if float(sum_value_ask) < float(amountin):
            return (total_volume)*(100-0.26)/100

    # Kiểm tra nếu dùng 1 số coin thì bán ra được bao nhiêu đồng usd
    def get_return_sell_bitmart(self, symbol, usd, amountin, proxy, fake_ip):
        result = self.get_depth_bitmart(symbol, usd, proxy, fake_ip)
        try:
            list_bids = result['sells']
        except:
            return 0
        sum_value_bids = 0
        total_volume = 0
        for bid in list_bids:
            sum_value_bids = sum_value_bids + float(bid['price'])*float(bid['amount'])
            total_volume = total_volume + float(bid['amount'])
            # print("sum_value_bids", sum_value_bids)
            # print("total_volume", total_volume)
            # print("------------")
            if float(total_volume) >= float(amountin):
                # print(bid)
                tien_con_thieu = amountin - (total_volume - float(bid['amount']))
                # print("tien_con_thieu", tien_con_thieu)
                total_return = sum_value_bids - \
                    float(bid['price'])*float(bid['amount']) + tien_con_thieu*float(bid['price'])
                # print("total_return", total_return)
                return float(total_return)*(100-0.26)/100
        if float(total_volume) < float(amountin):
            return float(sum_value_bids)*(100-0.26)/100

    # Tìm giá khớp lệnh cuối cùng, và lượng token có thể nhận được khi mua
    def find_quantity_price_buy_bitmart(self, symbol, amountin, token_usd, proxy, fake_ip, truotgiasan):
        result = self.get_depth_bitmart(symbol, token_usd, proxy, fake_ip)
        # print(result)
        try:
            list_asks = result['buys']
        except:
            return 0, 0
        # print(list_bids)
        # print(list_asks)
        sum_value_ask = 0
        total_volume = 0
        price_start = float(list_asks[0]['price'])
        for ask in list_asks:
            sum_value_ask = sum_value_ask + float(ask['price'])*float(ask['amount'])
            total_volume = total_volume + float(ask['amount'])
            print("sum_value_ask", sum_value_ask)
            print("total_volume", total_volume)
            print("------------")
            price_find = float(ask['price'])
            if float(sum_value_ask) >= float(amountin):
                # print(ask)
                tien_con_thieu = float(
                    amountin) - (float(sum_value_ask) - float(ask['price'])*float(ask['amount']))
                print("tien_con_thieu", tien_con_thieu)
                total_return = float(total_volume) - \
                    float(ask['amount']) + tien_con_thieu/float(ask['price'])
                print("total_return", total_return)
                return price_find, total_return*(100-0.1)/100
        if float(price_find) > price_start*(1+float(truotgiasan)/100):
            print("SOS bitmart -buy " + str(symbol) +
                  str(price_find)+" " + str(price_start))
            return 0, 0
        print("price OK bitmart price_start" +
              str(price_start) + "price_find " + (price_find))

        if float(sum_value_ask) < float(amountin):
            # 0.1 là phí giao dịch của bitmart
            return price_find, total_volume*(100-0.26)/100

    # lệnh buy cần tính chuẩn với khối lượng 1000 usdt mua
    # Hàm mua theo limit
    def real_buy_in_bitmart(self, token_name, token_usd, amounin, amoutoutmin, proxy, fake_ip, truotgiasan):
        symbol = token_name + "_" + token_usd
        price, quantity = self.find_quantity_price_buy_bitmart(symbol=token_name, amountin=amounin, token_usd=token_usd, proxy=proxy, fake_ip=fake_ip, truotgiasan=truotgiasan)
        print("price", price)
        print("quantity", quantity)
        if quantity == 0:
            print("Do truot gia cua san qua cao")
            return "Do truot gia cua san qua cao"
        if quantity < amoutoutmin:
            print("real_buy_in_bitmart quantity" + str(quantity) +
                  " < amoutoutmin" + str(amoutoutmin))
            return "Bé hơn amoutoutmin rồi!!!"
        if "e" in str(price):
            price = f'{price:.20f}'
        else:
            price = price
        Klin = int(quantity*10**4)/(10**4)
        print("Klin ", Klin)
        print("price ", price)
        try:
            result = self.TradeAPI.place_order(
                type_='limit', symbol=symbol, price=price, side="buy", size=Klin)
            # print("result", result)
        except:
            print("Lỗi: ", sys.exc_info())

        if result['code'] == 1000:
            order_id = result['data']['orderId']
            print("Đã đặt lệnh thành công")
        else:
            print("Lỗi rồi.....", result)
            return result

        print("order_id", order_id)
        order_details = None
        for i in range(4):
            response = self.TradeAPI.get_orders(order_id)
            order_details = response['data'] 
            print("get_order_details ", order_details)
            deal_price = order_details['price']
            print("deal_fund", deal_price)
            dealSize = order_details['size']
            print("dealSize", dealSize)
            state = order_details['state']
            print("state", state)
            if 'new' in state or 'partially_filled' in state:
                if i > 2:
                    print("Lệnh đang buy market còn mở")
                    result = self.TradeAPI.cancel_order(order_id)
                    print("result_cancel_buy", result)
                    if result['code'] == '0':
                        print("ĐÃ HỦY LỆNH THÀNH CÔNG!!!")
                        if deal_price == '0':
                            result = "KHÔNG MUA ĐƯỢC__ĐÃ HỦY LỆNH THÀNH CÔNG!!!"
                        else:
                            result = "1 Phần. Nhận " + str(dealSize) + "Hết =" + str(
                                float(dealSize)*float(deal_price)) + " ĐÃ HỦY LỆNH THÀNH CÔNG"
                    else:
                        result = "HỦY LỆNH THẤT BẠI!!! Vào Hủy tay đi chị đẹp"
                    break
            else:
                result = "MUA OK. Nhận " + \
                    str(dealSize) + "Hết =" + \
                    str(float(dealSize)*float(deal_price))
                break
            time.sleep(1)
        return result

    # Hàm bán token theo limit
    def real_sell_in_bitmart(self, token_name, token_usd, amounin, amoutoutmin, proxy, fake_ip, truotgiasan):
        symbol = token_name + '_' + token_usd

        price, quantity = self.find_quantity_price_sell_bitmart(
            symbol=token_name, amountin=amounin, token_usd=token_usd, proxy=proxy, fake_ip=fake_ip, truotgiasan=truotgiasan)
        if "e" in str(price):
            price = f'{price:.20f}'
        else:
            price = price
        print("price", price)
        print("quantity", quantity)
        if quantity == 0:
            print("Do truot gia cua san qua cao")
            return "Do truot gia cua san qua cao"
        if quantity < amoutoutmin:
            print("real_sell_in_bitmart quantity" + str(quantity) +
                  " < amoutoutmin" + str(amoutoutmin))
            return "Bé hơn amoutoutmin rồi!!!"

        Klin = int(amounin*10**4)/(10**4)
        print("khối lượng vào", Klin)
        try:
            result = self.TradeAPI.place_order(
                type_='limit', symbol=symbol, price=price, side="sell", size=Klin)
        except:
            print("Lỗi ", sys.exc_info())

        if result['code'] == 1000:
            order_id = result['data']['orderId']
            print("Đã đặt lệnh thành công")
        else:
            print("Lỗi rồi.....", result)
            return result

        print("order_id", order_id)
        order_details = None
        for i in range(4):
            response = self.TradeAPI.get_orders(order_id)
            order_details = response['data'] 
            print("get_order_details ", order_details)
            deal_price = order_details['price']
            print("deal_fund", deal_price)
            dealSize = order_details['size']
            print("dealSize", dealSize)
            state = order_details['state']
            print("state", state)
            if 'new' in status or 'partially_filled' in status:
                if i > 2:
                    print("Lệnh sell đang còn mở")
                    result = self.TradeAPI.cancel_order(order_id)
                    print("result_cancel_buy", result)
                    if result['code'] == 1000:
                        print("ĐÃ HỦY LỆNH THÀNH CÔNG!!!")
                        if deal_price == '0':
                            result = "KHÔNG BÁN ĐƯỢC__ĐÃ HỦY LỆNH THÀNH CÔNG!!!"
                        else:
                            result = "Bán 1 Phần " + str(dealSize) + "Nhận được =" + str(
                                float(dealSize)*float(deal_price)) + " ĐÃ HỦY LỆNH THÀNH CÔNG"
                    else:
                        result = "HỦY LỆNH THẤT BẠI!!! Vào Hủy tay đi chị đẹp"
                    break
            else:
                result = f"THÀNH CÔNG. BÁN {Klin} {token_name} Nhận được {str(float(dealSize)*float(deal_price))} "
                break
            time.sleep(1)
        return result

    # Tìm giá khơp lệnh cuối cùng và số tiền nhận được khi bán token
    def find_quantity_price_sell_bitmart(self, symbol, amountin, token_usd, proxy, fake_ip, truotgiasan):
        result = self.get_depth_bitmart(symbol, token_usd, proxy, fake_ip)
        # print(f"get_depth_bitmart {result}")
        try:
            list_bids = result['sells']
        except:
            return 0
        sum_value_bids = 0
        total_volume = 0
        price_start = float(list_bids[0]['amount'])

        for bid in list_bids:
            sum_value_bids = sum_value_bids + \
                float(bid['price'])*float(bid['amount'])  # tiền
            total_volume = total_volume + float(bid['amount'])  # khối lượng
            print("sum_value_bids", sum_value_bids)
            print("total_volume", total_volume)
            print("------------")
            price_find = bid['price']

            if float(total_volume) >= float(amountin):
                tien_con_thieu = amountin - (total_volume - float(bid['amount']))
                print("tien_con_thieu", tien_con_thieu)
                total_return = sum_value_bids - \
                    float(bid['price'])*float(bid['amount']) + tien_con_thieu*float(bid['price'])
                print("total_return", total_return)
                return price_find, total_return*(100-0.1)/100
            # print("price", price_find )
        if float(price_find) < price_start/(1+float(truotgiasan)/100):
            print("SOS " + str(price_find)+" " + str(price_start))
            return 10000000, 0
        print("price OK bitmart" + str(price_start) +
              "price_find " + (price_find))

        if float(total_volume) < float(amountin):
            return price_find, sum_value_bids * (100-0.26)/100

    def get_chain_token(self, aset, proxy="", fake_ip=False):
        nonce = str(int(time.time() * 1000))
        res = self.FundingAPI.get_deposit_method_token(
            nonce=nonce, token=aset, proxy=proxy, fake_ip=fake_ip)
        print("res", res)
        data = res['result']
        list_chain = []
        for add in data:
            print(add)
            chain = add["method"]
            if chain not in list_chain:
                print("chain", chain)
                list_chain.append(chain)
                print("................")
        return list_chain

    # Lấy địa chỉ nạp tiền lên bitmart
    def get_deposit_address_bitmart(self, currency, chain):
        currency = currency.upper()
        if chain == "Polygon":
            chainID = "MATIC"
        elif chain == "OPT":
            chainID = "OPTIMISM"
        elif chain == "TRON":
            chainID = "TRX"
        elif chain == "AVAX":
            chainID = "AVAX"
        elif chain == "ETH":
            chainID = "ARBI"
        elif chain == "FTM":
            chainID = "Fantom"
        elif chain == "SOL":
            chainID = "SOL"
        elif chain == "KLAY":
            chainID = "Klaytn"
        elif chain == "ARB":
            chainID = "Arbitrum"
        else:
            chainID = chain
        print("chainID", chainID)
        currency = currency + '-' + chainID
        try:
            res = self.FundingAPI.get_deposit_address(currency=currency)
            print(f"res: {res['data']}")
            if res['code'] == 1000:
                return res['data']['address']
            else:
                return ["No address avaiable"]
        except:
            err = str(sys.exc_info())
            print("err", err)
            print("Kiểm tra lại Chain đi người đẹp!")
            return ["No address avaiable"]

    # Lấy trạng thái khả dụng hay bị dừng nạp tiền của 1 token
    def get_status_deposit_bitmart(self, currency):
        currency = currency.upper()
        try:
            res = self.FundingAPI.get_currency()
            for item in res['data']['currencies']:
                if currency == item['currency']:
                    # print(item['supportDeposit'])
                    if item['deposit_enabled'] != True:
                        print("Tạm dừng nạp tiền rồi. Token ", currency)
                        return None
                    else:
                        return "Nạp tiền bình thường. Token " + str(currency)
        except Exception as e:
            print(f"lỗi request {e}")

    # Lấy trạng thái khả dụng hay bị dừng rút tiền
    def get_status_withdrawal_bitmart(self, currency):
        currency = currency.upper()
        try:
            res = self.FundingAPI.get_currency()
            for item in res['data']['currencies']:
                if currency == item['currency']:
                    # print(item['supportWithdraw'])
                    status = item['withdraw_enabled']
                    if status != True:
                        print("Tạm dừng rút tiền rồi ", currency)
                        return None
                    else:
                        minWithdrawSingle = item['withdraw_minsize']
                        return status, minWithdrawSingle
        except Exception as e:
            print(f"lỗi request {e}")

    # Lấy lịch sử nạp tiền
    def get_deposit_history_bitmart(self, currency, id):
        res = self.FundingAPI.get_deposit_history(currency=currency, operation_type='deposit', N=100)
        print("res", res)
        if res['code'] == 1000:
            for res_dep in res['data']['records']:
                if str(id).lower() in res_dep['deposit_id'].lower():
                    status = res_dep['status']
                    print("status", status)
                    if status == 0:
                        print("Create " + str(currency))
                        sta = "Create.Token: " + str(currency)
                    elif status == 1:
                        print("Submitted, waiting for withdrawal " + str(currency))
                        sta = "Submitted, waiting for withdrawal " + str(currency)
                    elif status == 2:
                        print("Processing " + str(currency))
                        sta = "Processing " + str(currency)
                    elif status == 3:
                        print("Processing " + str(currency))
                        sta = "Processing " + str(currency)
                    elif status == 4:
                        print("Cancel " + str(currency))
                        sta = "Cancel " + str(currency)
                    elif status == 5:
                        print("Fail " + str(currency))
                        sta = "Fail " + str(currency)
                        break
                return sta
        else:
            print("Lỗi get status deposit Bitmart")
            return "Lỗi get status deposit Bitmart"

    def get_withdraw_history_bitmart(self, wd_id):  # Lấy lịch sử rút tiền
        try:
            res = self.FundingAPI.get_withdrawal_history(operation_type='withdraw', N=100)
            if res['code'] == 1000:
                if res['data']['records'] == []:
                    return ["Không có giao dịch rút tiền gần đây!"]
            for res_wd in res['data']['records']:
                if str(wd_id).lower() in str(res_wd['withdraw_id']).lower():
                    state = res_wd['status']
                    print("status", status)
                    if res_wd['status'] == 0:
                        sta = "Create"
                    elif res_wd['status'] == 1:
                        sta = "Submitted, waiting for withdrawal"
                    elif res_wd['status'] == 2:
                        sta = "Processing"
                    elif res_wd['status'] == 3:
                        sta = "Processing"
                    elif res_wd['status'] == 4:
                        sta = "Cancel"
                    elif res_wd['status'] == 5:
                        sta = "Fail"
        except:
            print("Lỗi request WD history Bitmart " + str(sys.exc_info()))
            sta = "Lỗi request WD history Bitmart"
        return sta

    # Hàm rút tiền từ bitmart về  ví metamask
    def submit_token_withdrawal_bitmart(self, currency, amount, destination, address):
        balance = self.get_balances_bitmart(currency)
        status = ''
        if float(balance) > 0 and float(balance) >= float(amount):
            try:
                print("size ", amount)
                res = self.FundingAPI.coin_withdraw(currency, amount, destination, address)
                print("submit_token_withdrawal_bitmart ", res)
                if res['code'] == 1000:
                    withdrawal_ID = res['data']['withdraw_id']
                    print("withdrawal_ID", withdrawal_ID)
                    print("Đã rút tiền chờ tiền về tài khoản!")
                    status = "Đã rút tiền chờ tiền về tài khoản!"
                    return True, status, withdrawal_ID
                else:
                    print("Rút tiền thất bại! " + str(res['message']))
                    status = res['message']
                    return False, status, 0
            except:
                err = str(sys.exc_info())
                print("Lỗi submit_token_withdrawal_bitmart ", err)
                status = err
                return 'False1', status, 0
        else:
            print("Không đủ tiền để rút rồi người đẹp!")
            status = "Không đủ tiền rút rồi!!!"
            return False, status, 0


toolbitmart = BITMART_FUNCTION(keypass='')

# print(toolbitmart.get_depth_bitmart("BTC", "USDT", "", ""))
# print(f'=== {toolbitmart.get_return_buy_bitmart(symbol="BMX", usd="USDT", amountin=1, proxy="", fake_ip=False)}')
# print(f'=== {toolbitmart.get_return_sell_bitmart(symbol="ETH", usd="USDT", amountin=1, proxy="", fake_ip=False)}')

# print(toolbitmart.find_quantity_price_buy_bitmart("ETH", 1, "USDT", "", "", 0.1))
# print(toolbitmart.find_quantity_price_sell_bitmart("ETH", 1, "USDT", "", "", 0.1))

# print(toolbitmart.real_buy_in_bitmart("BTC", "USDT", 100, 0, "", "", 0.5))
# print(toolbitmart.real_sell_in_bitmart("BTC", "USDT", 10, 0, "proxy", False, 5))

# print(toolbitmart.get_deposit_address_bitmart("USDT", "ERC20"))  # no
# print(toolbitmart.get_status_deposit_bitmart("BTC")) # no
# print(toolbitmart.get_status_withdrawal_bitmart("FTM")) # no
# print(toolbitmart.get_deposit_history_bitmart("USDT", "1"))  # no
# print(toolbitmart.get_withdraw_history_bitmart("1"))  # no
# print(toolbitmart.get_balances_bitmart("ETH")) # no
print(toolbitmart.submit_token_withdrawal_bitmart("FTM", 1, "To Digital Address" ,"0x1EE6FA5A3803608fc22a1f3F76")) # no
# print(toolbitmart.submit_token_withdrawal_bitmart("USDT", 2.5, "USDT_ARB")) # no
