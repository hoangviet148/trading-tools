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
            self.api_key = 'bc16321ecb6bc6066938624fbb60fa411fd5bd3530a75fc3cb2b590daee7f54a'
            self.api_secret = '94f9e375e5c697bf2a79bda9d939c9f6744bcdf1b4ab4134cf21215d7fdc8a6c'

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

    def get_balances_bkex(self, asset):  # Check số dư của 1 token trên sàn
        while True:
            try:
                nonce = int(time.time() * 1000)
                res = self.FundingAPI.get_balances(nonce=nonce)
                # print("res", res)
                balance = res['result'][asset]
                break
            except:
                time.sleep(1)
                continue

        # print("balance_trading ", balance_trading)
        return self.convert_number_to_smaller(float(balance))

    # Lấy danh sách các lệnh đang được đặt trên sàn
    def get_depth_bkex(self, symbol, usd, proxy, fake_ip):
        token = (symbol + usd).upper()
        url = "https://api.bkex.com/0/public/Depth?pair=" + token + "&count=500"
        try:
            if fake_ip == True:
                proxies = {
                    'http': str(proxy),
                    'https': str(proxy)
                }
                res = requests.get(url, proxies=proxies, timeout=5)
            else:
                res = requests.get(url, timeout=5).json()

            if res['result'] == False:
                return 0
            else:
                first_item, *rest = res['result']
                # print(res['result'][first_item])
                return res['result'][first_item]
        except Exception as e:
            print("Exception", e)
            return 0

    # Kiểm tra nếu dùng 1 số usd thì mua được bao nhiêu đồng coin
    def get_return_buy_bkex(self, symbol, usd, amountin, proxy, fake_ip):
        result = self.get_depth_bkex(symbol, usd, proxy, fake_ip)
        try:
            list_asks = result['asks']
            # print("list_asks ", list_asks)
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
            list_bids = result['bids']
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
            list_asks = result['asks']
        except:
            return 0
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
        symbol = token_name + token_usd
        price, quantity = self.find_quantity_price_buy_bkex(
            symbol=token_name, amountin=amounin, token_usd=token_usd, proxy=proxy, fake_ip=fake_ip, truotgiasan=truotgiasan)
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
        nonce = int(time.time() * 1000)
        try:
            result = self.TradeAPI.place_order(
                nonce=nonce, ordertype='limit', pair=symbol, price=price, type_='buy', volume=Klin)
            print("result", result)
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
            list_bids = result['bids']
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

    # Lấy địa chỉ nạp tiền lên bkex
    def get_deposit_address_bkex(self, symbol, chain):
        symbol = symbol.upper()
        nonce = int(time.time() * 1000)
        try:
            res = self.FundingAPI.get_deposit_address(
                nonce=nonce, asset=symbol, method=chain)
            print(f"res: {res['result'][0]['address']}")
            if len(res['error']) == 0:
                return res['result'][0]['address']
        except:
            err = str(sys.exc_info())
            print("err", err)
            print("Kiểm tra lại Chain đi người đẹp!")
            return 0, 0

    # Lấy trạng thái khả dụng hay bị dừng nạp tiền của 1 token
    def get_status_deposit_bkex(self, symbol, chain):
        symbol = symbol.upper()
        try:
            res = self.FundingAPI.get_currency()
            for data in res['result']:
                if symbol in data:
                    if res['result'][data]['status'] != 'enabled':
                        print("Tạm dừng nạp tiền rồi ", symbol, chain)
                        return 0, 0, 0
                    else:
                        add = self.get_deposit_address_bkex(
                            symbol, chain)
                        print("Đã lấy được địa chỉ nạp tiền!!!", symbol, chain)
                        return add
        except Exception as e:
            print(f"lỗi request {e}")

    # Lấy trạng thái khả dụng hay bị dừng rút tiền
    def get_status_withdrawal_bkex(self, symbol, key, amount):
        nonce = int(time.time() * 1000)
        try:
            res = self.FundingAPI.get_withdrawal_info(
                nonce=nonce, asset=symbol, key=key, amount=amount)
            print(f"res {res}")

            if len(res['error']) == 0:
                print("Mạng rút bình thường!!!")
                limit = res['result']['limit']
                fee = res['result']['fee']
                return fee
            else:
                print("Tạm dừng rút tiền rồi ", token, key)
                return 0
        except:
            err = str(sys.exc_info())
            print("Chain không khả dụng!!!" + err)
            exit()

    # Lấy lịch sử nạp tiền
    def get_deposit_history_bkex(self, asset, method):
        nonce = int(time.time() * 1000)
        res = self.FundingAPI.get_deposit_history(
            nonce=nonce, asset=asset, method=method)
        status = []
        if len(res['error']) == 0:
            for res_dep in res['result']:
                status.append(res_dep['status'])
        else:
            print(res['error'])
        return status

    def get_withdraw_history_bkex(self):  # Lấy lịch sử rút tiền
        nonce = int(time.time() * 1000)
        status = []
        try:
            res = self.FundingAPI.get_withdrawal_history(nonce=nonce)
            if len(res['result']) == 0:
                return ["No recent withdraw transaction!"]
            for res_wd in res['result']:
                if res_wd['status'] == 'canceled':
                    status.append("canceled" + str(symbol))
                elif res_wd['status'] == 'Pending':
                    status.append("Pending" + str(symbol))
        except:
            print("Lỗi lấy data" + str(sys.exc_info()))
            status.append("Lỗi " + str(sys.exc_info()))
        return status

    # Chuyển tiền trong nội bộ sàn ( Có nhiều sàn ko cần chức năng này)
    def transfer_bkex(self, asset, amount, From, to):
        nonce = int(time.time() * 1000)
        try:
            res = self.FundingAPI.funds_transfer(
                nonce, asset, amount, From, to)
            # break
        except:
            print("Lỗi transfer main to trading_bkex ", str(sys.exc_info()))
            return "Lỗi transfer main to trading_bkex " + str(sys.exc_info())
        if len(res['error']) == '0':
            print("chuyển tiền thành công")
            status = "chuyển tiền thành công"
        else:
            print("Lỗi chuyển tiền bkex " + str(res))
            status = "Lỗi chuyển tiền bkex" + str(res)
        return status

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
                    res = self.FundingAPI.coin_withdraw(nonce, asset, address, amount)
                    print("submit_token_withdrawal_bkex ", res)
                    if len(res['error']) == 0:
                        withdrawal_ID = res['result']['refid']
                        print("withdrawal_ID", withdrawal_ID)
                        print("Đã rút tiền chờ tiền về tài khoản!")
                        status = "Đã rút tiền chờ tiền về tài khoản!"
                        return True, status, withdrawal_ID
                    else:
                        print("Rút tiền thất bại! " + str(res['error']) + "fee =" + str(fee_rutien))
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

# print(f'=== 1 ETH buy {toolbkex.get_return_buy_bkex(symbol="USD", usd="ETH", amountin=1, proxy="", fake_ip=False)} USD')
# print(f'=== 1 LTC sell {toolbkex.get_return_sell_bkex(symbol="LTC", usd="USDT", amountin=1, proxy="", fake_ip=False)} USDT')

# print(toolbkex.find_quantity_price_buy_bkex("ETH", 1, "USDT", "", "", 0.1))
# print(toolbkex.find_quantity_price_sell_bkex("ETH", 1, "USDT", "", "", 0.1))

# print(toolbkex.get_depth_bkex("ETH", "USDT", "", ""))
# print(toolbkex.real_buy_in_bkex("XBT", "USD", 5, 0, "", "", 0.5))
# print(toolbkex.real_sell_in_bkex("FTM", "USD", 10, 0, "proxy", False, 5))

# print(toolbkex.get_deposit_address_bkex("XBT", "Bitcoin"))
# print(toolbkex.get_status_deposit_bkex("XBT", "Bitcoin"))
# print(toolbkex.get_status_withdrawal_bkex("FTM", "metamaskARB", 2))
# print(toolbkex.get_deposit_history_bkex("USDT", "Tether USD (TRC20)"))
# print(toolbkex.get_withdraw_history_bkex())
# print(toolbkex.transfer_bkex("USDT", "5", "Spot Wallet", "Futures Wallet"))
print(toolbkex.get_balances_bkex("USDT"))
# print(toolbkex.submit_token_withdrawal_bkex("FTM", 1, "metamaskARB"))
# print(toolbkex.submit_token_withdrawal_bkex("USDT", 2.5, "USDT_ARB"))
