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

import bkex.Account_api as Account
import bkex.Funding_api as Funding
import bkex.Market_api as Market
import bkex.Public_api as Public
import bkex.Trade_api as Trade
import bkex.subAccount_api as SubAccount
import bkex.status_api as Status

import logging
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
# from decouple import config

scraper = cloudscraper.create_scraper()
path_file = os.path.dirname(os.path.abspath(__file__))

flag = '0'


class BKEX_FUNCTION:
    def __init__(self, keypass=None):
        print("Init")
        if keypass != None:

            # NHẬP KEY, SECRET của API
            self.api_key = '0e6c4a52ca1fdc19bcbd05602800ca962e9ac56dbf6e0e550b0b194a429596d5'
            self.api_secret = '98a649b9fd88a32683e53c20a35593773a47d763ebd31daa6a35bad1c2603dcd'

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

    def get_balances_bkex(self, currencys):  # Check số dư của 1 token trên sàn
        while True:
            try:
                res = self.FundingAPI.get_balances(currencys=currencys)
                # print("res", res)
                if not res['data']:
                    balance = 0
                else:
                    balance = res['data'][currencys]
                break
            except:
                time.sleep(1)
                continue

        # print("balance_trading ", balance_trading)
        return self.convert_number_to_smaller(float(balance))

    # Lấy danh sách các lệnh đang được đặt trên sàn
    def get_depth_bkex(self, symbol, usd, proxy, fake_ip):
        token = (symbol + "_" + usd).upper()
        states = 'submitted,partial-filled,filled'  # Order states to include
        url = "https://api.bkex.com/v2/q/depth"
        data = {
            'symbol': token,
            'states': states
        }
        try:
            if fake_ip == True:
                proxies = {
                    'http': str(proxy),
                    'https': str(proxy)
                }
                res = requests.get(url, data=data, proxies=proxies, timeout=5)
            else:
                res = requests.get(url, data=data, timeout=5).json()

            # print(f"=== {res} ===")
            if res['status'] != 0:
                return 0
            else:
                return res['data']
        except Exception as e:
            print("Exception", e)
            return 0

    # Kiểm tra nếu dùng 1 số usd thì mua được bao nhiêu đồng coin
    def get_return_buy_bkex(self, symbol, usd, amountin, proxy, fake_ip):
        result = self.get_depth_bkex(symbol, usd, proxy, fake_ip)
        # print("result ", result)
        try:
            list_asks = result['ask']
            print("list_asks ", list_asks)
        except:
            return 0
        sum_value_ask = 0
        total_volume = 0
        for ask in list_asks:
            # print(ask)
            sum_value_ask = sum_value_ask + float(ask[0])*float(ask[1])
            total_volume = total_volume + float(ask[1])
            if float(sum_value_ask) >= float(amountin):
                # print(ask)
                tien_con_thieu = amountin - \
                    (sum_value_ask - float(ask[0])*float(ask[1]))
                # print("tien_con_thieu ", tien_con_thieu)
                total_return = total_volume - \
                    float(ask[1]) + tien_con_thieu/float(ask[0])
                # print("total_return", total_return)
                return float(total_return)*(100-0.1)/100
        if float(sum_value_ask) < float(amountin):
            return (total_volume)*(100-0.26)/100

    # Kiểm tra nếu dùng 1 số coin thì bán ra được bao nhiêu đồng usd
    def get_return_sell_bkex(self, symbol, usd, amountin, proxy, fake_ip):
        result = self.get_depth_bkex(symbol, usd, proxy, fake_ip)
        try:
            list_bids = result['bid']
        except:
            return 0
        sum_value_bids = 0
        total_volume = 0
        for bid in list_bids:
            sum_value_bids = sum_value_bids + float(bid[0])*float(bid[1])
            total_volume = total_volume + float(bid[1])
            # print("sum_value_bids", sum_value_bids)
            # print("total_volume", total_volume)
            # print("------------")
            if float(total_volume) >= float(amountin):
                # print(bid)
                tien_con_thieu = amountin - (total_volume - float(bid[1]))
                # print("tien_con_thieu", tien_con_thieu)
                total_return = sum_value_bids - \
                    float(bid[0])*float(bid[1]) + tien_con_thieu*float(bid[0])
                # print("total_return", total_return)
                return float(total_return)*(100-0.26)/100
        if float(total_volume) < float(amountin):
            return float(sum_value_bids)*(100-0.26)/100

    # Tìm giá khớp lệnh cuối cùng, và lượng token có thể nhận được khi mua
    def find_quantity_price_buy_bkex(self, symbol, amountin, token_usd, proxy, fake_ip, truotgiasan):
        result = self.get_depth_bkex(symbol, token_usd, proxy, fake_ip)
        # print(result)
        try:
            list_asks = result['ask']
        except:
            return 0, 0
        # print(list_bids)
        # print(list_asks)
        sum_value_ask = 0
        total_volume = 0
        price_start = float(list_asks[0][0])
        for ask in list_asks:
            sum_value_ask = sum_value_ask + float(ask[0])*float(ask[1])
            total_volume = total_volume + float(ask[1])
            print("sum_value_ask", sum_value_ask)
            print("total_volume", total_volume)
            print("------------")
            price_find = float(ask[0])
            if float(sum_value_ask) >= float(amountin):
                # print(ask)
                tien_con_thieu = float(
                    amountin) - (float(sum_value_ask) - float(ask[0])*float(ask[1]))
                print("tien_con_thieu", tien_con_thieu)
                total_return = float(total_volume) - \
                    float(ask[1]) + tien_con_thieu/float(ask[0])
                print("total_return", total_return)
                return price_find, total_return*(100-0.1)/100
        if float(price_find) > price_start*(1+float(truotgiasan)/100):
            print("SOS bkex -buy " + str(symbol) +
                  str(price_find)+" " + str(price_start))
            return 0, 0
        print("price OK bkex price_start" +
              str(price_start) + "price_find " + (price_find))

        if float(sum_value_ask) < float(amountin):
            # 0.1 là phí giao dịch của bkex
            return price_find, total_volume*(100-0.26)/100

    # lệnh buy cần tính chuẩn với khối lượng 1000 usdt mua
    # Hàm mua theo limit
    def real_buy_in_bkex(self, token_name, token_usd, amounin, amoutoutmin, proxy, fake_ip, truotgiasan):
        symbol = token_name + "_" + token_usd
        price, quantity = self.find_quantity_price_buy_bkex(symbol=token_name, amountin=amounin, token_usd=token_usd, proxy=proxy, fake_ip=fake_ip, truotgiasan=truotgiasan)
        print("price", price)
        print("quantity", quantity)
        if quantity == 0:
            print("Do truot gia cua san qua cao")
            return "Do truot gia cua san qua cao"
        if quantity < amoutoutmin:
            print("real_buy_in_bkex quantity" + str(quantity) +
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
                type_='LIMIT', symbol=symbol, price=price, direction="ASK", volume=Klin)
            print("result", result)
        except:
            print("Lỗi ", sys.exc_info())

        if result['code'] == 0:
            order_id = result['data']
            print("Đã đặt lệnh thành công")
        else:
            print("Lỗi rồi.....", result)
            return result

        print("order_id", order_id)
        for i in range(4):
            nonce = int(time.time() * 1000)
            order_details = self.TradeAPI.get_orders(nonce, order_id)
            print("get_order_details ", order_details)
            deal_price = order_details['result'][order_id]['price']
            print("deal_fund", deal_price)
            dealSize = order_details['result'][order_id]['vol']
            print("dealSize", dealSize)
            status = order_details['result'][order_id]['status']
            print("status", status)
            if 'open' in status or 'partial' in status:
                if i > 2:
                    print("Lệnh đang buy market còn mở")
                    nonce = int(time.time() * 1000)
                    result = self.TradeAPI.cancel_order(nonce, order_id)
                    print("result_cancel_buy", result)
                    if result['result']['count'] == '1':
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
    def real_sell_in_bkex(self, token_name, token_usd, amounin, amoutoutmin, proxy, fake_ip, truotgiasan):
        symbol = token_name + token_usd

        price, quantity = self.find_quantity_price_sell_bkex(
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
            print("real_sell_in_bkex quantity" + str(quantity) +
                  " < amoutoutmin" + str(amoutoutmin))
            return "Bé hơn amoutoutmin rồi!!!"

        Klin = int(amounin*10**4)/(10**4)
        print("khối lượng vào", Klin)
        try:
            nonce = int(time.time() * 1000)
            result = self.TradeAPI.place_order(
                nonce=nonce, ordertype='limit', pair=symbol, price=price, type_='sell', volume=Klin)

        except:
            print("Lỗi ", sys.exc_info())

        if len(result['error']) == 0:
            order_id = result['result']['txid'][0]
            print("Đã đặt lệnh thành công")
        else:
            print("Lỗi rồi.....", result)
            return result

        print("order_id", order_id)
        for i in range(4):
            nonce = int(time.time() * 1000)
            order_details = self.TradeAPI.get_orders(nonce, order_id)
            print("get_order_details ", order_details)
            deal_price = order_details['result'][order_id]['price']
            print("deal_fund", deal_price)
            dealSize = order_details['result'][order_id]['vol']
            print("dealSize", dealSize)
            status = order_details['result'][order_id]['status']
            print("status", status)
            if 'open' in status or 'partial' in status:
                if i > 2:
                    print("Lệnh sell đang còn mở")
                    nonce = int(time.time() * 1000)
                    result = self.TradeAPI.cancel_order(nonce, order_id)
                    print("result_cancel_buy", result)
                    if result['result']['count'] == '1':
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
    def find_quantity_price_sell_bkex(self, symbol, amountin, token_usd, proxy, fake_ip, truotgiasan):
        result = self.get_depth_bkex(symbol, token_usd, proxy, fake_ip)
        # print(f"get_depth_bkex {result}")
        try:
            list_bids = result['bid']
        except:
            return 0
        sum_value_bids = 0
        total_volume = 0
        price_start = float(list_bids[0][0])

        for bid in list_bids:
            sum_value_bids = sum_value_bids + \
                float(bid[0])*float(bid[1])  # tiền
            total_volume = total_volume + float(bid[1])  # khối lượng
            print("sum_value_bids", sum_value_bids)
            print("total_volume", total_volume)
            print("------------")
            price_find = bid[0]

            if float(total_volume) >= float(amountin):
                tien_con_thieu = amountin - (total_volume - float(bid[1]))
                print("tien_con_thieu", tien_con_thieu)
                total_return = sum_value_bids - \
                    float(bid[0])*float(bid[1]) + tien_con_thieu*float(bid[0])
                print("total_return", total_return)
                return price_find, total_return*(100-0.1)/100
            # print("price", price_find )
        if float(price_find) < price_start/(1+float(truotgiasan)/100):
            print("SOS " + str(price_find)+" " + str(price_start))
            return 10000000, 0
        print("price OK bkex" + str(price_start) +
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

    # Lấy địa chỉ nạp tiền lên bkex
    def get_deposit_address_bkex(self, currency, chain):
        currency = currency.upper()
        if chain == "Polygon":
            chainID = "Polygon"
        elif chain == "OPT":
            chainID = "Optimism"
        elif chain == "BSC":
            chainID = "BEP"
        elif chain == "TRON":
            if "USD" not in symbol.upper():
                chainID = "Tron"
            else:
                chainID = "TRC20"
        elif chain == "AVAX":
            chainID = "Avalanche C-Chain"
        elif chain == "ETH":
            chainID = "ERC20"
        elif chain == "FTM":
            chainID = "Fantom"
        elif chain == "SOL":
            if "USD" not in symbol.upper():
                chainID = "Solana"
            else:
                chainID = "SPL"
        elif chain == "KLAY":
            chainID = "Klaytn"
        elif chain == "ARB":
            chainID = "Arbitrum"
        else:
            chainID = chain
        print("chainID", chainID)
        try:
            res = self.FundingAPI.get_deposit_address(currency=currency)
            print(f"res: {res['data']}")
            if res['status'] == 0:
                if len(res['data']) != 0:
                    return res['data'][chainID]
                else:
                    return ["No address avaiable"]
        except:
            err = str(sys.exc_info())
            print("err", err)
            print("Kiểm tra lại Chain đi người đẹp!")
            return ["No address avaiable"]

    # Lấy trạng thái khả dụng hay bị dừng nạp tiền của 1 token
    def get_status_deposit_bkex(self, currency):
        currency = currency.upper()
        try:
            res = self.FundingAPI.get_currency()
            for item in res['data']:
                if currency == item['currency']:
                    # print(item['supportDeposit'])
                    if item['supportDeposit'] != True:
                        print("Tạm dừng nạp tiền rồi. Token ", currency)
                        return None
                    else:
                        return "Nạp tiền bình thường. Token " + str(currency)
        except Exception as e:
            print(f"lỗi request {e}")

    # Lấy trạng thái khả dụng hay bị dừng rút tiền
    def get_status_withdrawal_bkex(self, symbol, key, amount):
        currency = currency.upper()
        try:
            res = self.FundingAPI.get_currency()
            for item in res['data']:
                if currency == item['currency']:
                    # print(item['supportWithdraw'])
                    status = item['supportWithdraw']
                    if status != True:
                        print("Tạm dừng rút tiền rồi ", currency)
                        return None
                    else:
                        maxWithdrawSingle = item['maxWithdrawSingle']
                        minWithdrawSingle = item['minWithdrawSingle']
                        return status, maxWithdrawSingle, minWithdrawSingle
        except Exception as e:
            print(f"lỗi request {e}")

    # Lấy lịch sử nạp tiền
    def get_deposit_history_bkex(self, currency, id):
        res = self.FundingAPI.get_deposit_history(currency=currency)
        print("res", res)
        if res['code'] == 0:
            for res_dep in res['data']['data']:
                if str(id).lower() in res_dep['id'].lower():
                    status = res_dep['state']
                    print("state", state)
                    if state == -1:
                        print("Failure " + str(currency))
                        sta = "Failure.Token: " + str(currency)
                    elif state == 0:
                        print("Acknowledged " + str(currency))
                        sta = "Acknowledged " + str(currency)
                    elif state == 3:
                        print("Confirmation in progress " + str(currency))
                        sta = "Confirmation in progress " + str(currency)
                        break
                return sta
        else:
            print("Lỗi get status deposit Kraken")
            return "Lỗi get status deposit Kraken"

    def get_withdraw_history_bkex(self, wd_id):  # Lấy lịch sử rút tiền
        try:
            res = self.FundingAPI.get_withdrawal_history()
            if res['code'] == 0:
                if res['data']['total'] == 0:
                    return ["Không có giao dịch rút tiền gần đây!"]
            for res_wd in res['data']['data']:
                if str(wd_id).lower() in str(res_wd['id']).lower():
                    state = res_wd['state']
                    print("state", state)
                    if res_wd['state'] == -1:
                        sta = "Failure"
                    elif res_wd['state'] == 0:
                        sta = "Acknowledged"
                    elif res_wd['state'] == 1:
                        sta = "Submitted"
                    elif res_wd['state'] == 2:
                        sta = "Cancelled"
                    elif res_wd['state'] == 5:
                        sta = "Awaiting confirmation"
        except:
            print("Lỗi request WD history Kraken " + str(sys.exc_info()))
            sta = "Lỗi request WD history Kraken"
        return sta

    # Hàm rút tiền từ bkex về  ví metamask
    def submit_token_withdrawal_bkex(self, asset, amount, address):
        balance = self.get_balances_bkex(asset)
        fee = self.get_status_withdrawal_bkex(asset, address, amount)
        print(f"fee {fee} {type(fee)}")
        list_fee_ruttien = [float(fee)]
        status = ''
        if float(balance) > 0 and float(balance) >= float(amount):
            for fee_rutien in list_fee_ruttien:
                try:
                    print("size ", amount)
                    nonce = int(time.time() * 1000)
                    res = self.FundingAPI.coin_withdraw(
                        nonce, asset, address, amount)
                    print("submit_token_withdrawal_bkex ", res)
                    if len(res['error']) == 0:
                        withdrawal_ID = res['result']['refid']
                        print("withdrawal_ID", withdrawal_ID)
                        print("Đã rút tiền chờ tiền về tài khoản!")
                        status = "Đã rút tiền chờ tiền về tài khoản!"
                        return True, status, withdrawal_ID
                    else:
                        print("Rút tiền thất bại! " +
                              str(res['error']) + "fee =" + str(fee_rutien))
                        status = res['error']
                        continue
                except:
                    err = str(sys.exc_info())
                    print("Lỗi submit_token_withdrawal_bkex ", err)
                    continue
            return False, status, 0
        else:
            print("Không đủ tiền để rút rồi người đẹp!")
            status = "Không đủ tiền rút rồi!!!"
            return False, status, 0


toolbkex = BKEX_FUNCTION(keypass='')

# print(f'=== {toolbkex.get_return_buy_bkex(symbol="BTC", usd="USDT", amountin=1, proxy="", fake_ip=False)}')
# print(f'=== 1 LTC sell {toolbkex.get_return_sell_bkex(symbol="ETH", usd="USDT", amountin=1, proxy="", fake_ip=False)} USDT')

# print(toolbkex.find_quantity_price_buy_bkex("ETH", 1, "USDT", "", "", 0.1))
# print(toolbkex.find_quantity_price_sell_bkex("ETH", 1, "USDT", "", "", 0.1))
# print(toolbkex.get_depth_bkex("BTC", "USDT", "", ""))

print(toolbkex.real_buy_in_bkex("BTC", "USDT", 5, 0, "", "", 0.5)) # no
# print(toolbkex.real_sell_in_bkex("FTM", "USD", 10, 0, "proxy", False, 5)) # no

# print(toolbkex.get_deposit_address_bkex("ETH", "FTM"))  # no
# print(toolbkex.get_status_deposit_bkex("BTC")) # no
# print(toolbkex.get_status_withdrawal_bkex("FTM", "metamaskARB", 2)) # no
# print(toolbkex.get_deposit_history_bkex("USDT", "1"))  # no
# print(toolbkex.get_withdraw_history_bkex("1"))  # no
# print(toolbkex.get_balances_bkex("ETH")) # no
# print(toolbkex.submit_token_withdrawal_bkex("FTM", 1, "metamaskARB")) # no
# print(toolbkex.submit_token_withdrawal_bkex("USDT", 2.5, "USDT_ARB")) # no
