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

import kraken.Account_api as Account
import kraken.Funding_api as Funding
import kraken.Market_api as Market
import kraken.Public_api as Public
import kraken.Trade_api as Trade
import kraken.subAccount_api as SubAccount
import kraken.status_api as Status

import logging
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
# from decouple import config

scraper = cloudscraper.create_scraper()
path_file = os.path.dirname(os.path.abspath(__file__))

flag = '0'

class KRAKEN_FUNCTION:
    def __init__(self, keypass=None):
        print("Init")
        if keypass != None:

            # NHẬP KEY, SECRET của API
            self.api_key = 'ckLFiOjFcq/UQ4z1nnscsQ8Ejdq4bf7TtGJX7UXc4E123/sX8uGbQKc7'
            self.api_secret = '/YVJ/6SqsczOy2pW8VstkNmyEv0jDajbia8Y5Mxmgzl9X/zcp50KD4W5wftOmMn44QjLb0Q0v2HMP2pbdeXCIw=='

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

    def get_balances_kraken(self, asset):  # Check số dư của 1 token trên sàn
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
    def get_depth_kraken(self, symbol, usd, proxy, fake_ip):
        token = (symbol + usd).upper()
        url = "https://api.kraken.com/0/public/Depth?pair=" + token + "&count=500"
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
    def get_return_buy_kraken(self, symbol, usd, amountin, proxy, fake_ip):
        result = self.get_depth_kraken(symbol, usd, proxy, fake_ip)
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
    def get_return_sell_kraken(self, symbol, usd, amountin, proxy, fake_ip):
        result = self.get_depth_kraken(symbol, usd, proxy, fake_ip)
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
    def find_quantity_price_buy_kraken(self, symbol, amountin, token_usd, proxy, fake_ip, truotgiasan):
        result = self.get_depth_kraken(symbol, token_usd, proxy, fake_ip)
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
            print("SOS KRAKEN -buy " + str(symbol) +
                  str(price_find)+" " + str(price_start))
            return 0, 0
        print("price OK KRAKEN price_start" +
              str(price_start) + "price_find " + (price_find))

        if float(sum_value_ask) < float(amountin):
            # 0.1 là phí giao dịch của KRAKEN
            return price_find, total_volume*(100-0.26)/100

    # lệnh buy cần tính chuẩn với khối lượng 1000 usdt mua
    # Hàm mua theo limit
    def real_buy_in_kraken(self, token_name, token_usd, amounin, amoutoutmin, proxy, fake_ip, truotgiasan):
        symbol = token_name + token_usd
        price, quantity = self.find_quantity_price_buy_kraken(
            symbol=token_name, amountin=amounin, token_usd=token_usd, proxy=proxy, fake_ip=fake_ip, truotgiasan=truotgiasan)
        print("price", price)
        print("quantity", quantity)
        if quantity == 0:
            print("Do truot gia cua san qua cao")
            return "Do truot gia cua san qua cao"
        if quantity < amoutoutmin:
            print("real_buy_in_kraken quantity" + str(quantity) +
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
    def real_sell_in_kraken(self, token_name, token_usd, amounin, amoutoutmin, proxy, fake_ip, truotgiasan):
        symbol = token_name + token_usd

        price, quantity = self.find_quantity_price_sell_kraken(
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
            print("real_sell_in_kraken quantity" + str(quantity) +
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
    def find_quantity_price_sell_kraken(self, symbol, amountin, token_usd, proxy, fake_ip, truotgiasan):
        result = self.get_depth_kraken(symbol, token_usd, proxy, fake_ip)
        # print(f"get_depth_kraken {result}")
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
        print("price OK kraken" + str(price_start) +
              "price_find " + (price_find))

        if float(total_volume) < float(amountin):
            return price_find, sum_value_bids * (100-0.26)/100

    # Lấy địa chỉ nạp tiền lên kraken
    def get_deposit_address_kraken(self, symbol, chain):
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
    def get_status_deposit_kraken(self, symbol, chain):
        symbol = symbol.upper()
        try:
            res = self.FundingAPI.get_currency()
            for data in res['result']:
                if symbol in data:
                    if res['result'][data]['status'] != 'enabled':
                        print("Tạm dừng nạp tiền rồi ", symbol, chain)
                        return 0, 0, 0
                    else:
                        add = self.get_deposit_address_kraken(
                            symbol, chain)
                        print("Đã lấy được địa chỉ nạp tiền!!!", symbol, chain)
                        return add
        except Exception as e:
            print(f"lỗi request {e}")

    # Lấy trạng thái khả dụng hay bị dừng rút tiền
    def get_status_withdrawal_kraken(self, symbol, key, amount):
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
    def get_deposit_history_kraken(self, asset, method):
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

    def get_withdraw_history_kraken(self):  # Lấy lịch sử rút tiền
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
    def transfer_kraken(self, asset, amount, From, to):
        nonce = int(time.time() * 1000)
        try:
            res = self.FundingAPI.funds_transfer(
                nonce, asset, amount, From, to)
            # break
        except:
            print("Lỗi transfer main to trading_kraken ", str(sys.exc_info()))
            return "Lỗi transfer main to trading_kraken " + str(sys.exc_info())
        if len(res['error']) == '0':
            print("chuyển tiền thành công")
            status = "chuyển tiền thành công"
        else:
            print("Lỗi chuyển tiền kraken " + str(res))
            status = "Lỗi chuyển tiền kraken" + str(res)
        return status

    # Hàm rút tiền từ kraken về  ví metamask
    def submit_token_withdrawal_kraken(self, asset, amount, address, chain):
        balance = self.get_balances_kraken(asset)
        fee = self.get_status_withdrawal_kraken(asset, chain, amount)
        print(f"fee {fee} {type(fee)}")
        list_fee_ruttien = [float(fee)]
        if float(balance) > 0 and float(balance) >= float(amount):
            for fee_rutien in list_fee_ruttien:
                try:
                    print("size ", amount)
                    nonce = int(time.time() * 1000)
                    res = self.FundingAPI.coin_withdraw(nonce, asset, address, amount)
                    print("submit_token_withdrawal_kraken ", res)
                    if res['code'] == '0':

                        withdrawal_ID = res['data'][0]['wdId']
                        print("withdrawal_ID", withdrawal_ID)
                        print("Đã rút tiền chờ tiền về tài khoản!")
                        status = "Đã rút tiền chờ tiền về tài khoản!"
                        return True, status, withdrawal_ID
                    else:
                        print("Rút tiền thất bại! " +
                              str(res['msg']) + "fee =" + str(fee_rutien))
                        status = res['msg']
                        continue
                except:
                    err = str(sys.exc_info())
                    print("Lỗi submit_token_withdrawal_kraken ", err)
                    continue
            return False, status, 0
        else:
            print("Không đủ tiền để rút rồi người đẹp!")
            status = "Không đủ tiền rút rồi!!!"
            return False, status, 0


toolkraken = KRAKEN_FUNCTION(keypass='')

# print(f'=== 1 ETH buy {toolkraken.get_return_buy_kraken(symbol="USD", usd="ETH", amountin=1, proxy="", fake_ip=False)} USD')
# print(f'=== 1 LTC sell {toolkraken.get_return_sell_kraken(symbol="LTC", usd="USDT", amountin=1, proxy="", fake_ip=False)} USDT')

# print(toolkraken.find_quantity_price_buy_kraken("ETH", 1, "USDT", "", "", 0.1))
# print(toolkraken.find_quantity_price_sell_kraken("ETH", 1, "USDT", "", "", 0.1))

# print(toolkraken.get_depth_kraken("ETH", "USDT", "", ""))
# print(toolkraken.real_buy_in_kraken("XBT", "USD", 5, 0, "", "", 0.5))
# print(toolkraken.real_sell_in_kraken("FTM", "USD", 10, 0, "proxy", False, 5))

# print(toolkraken.get_deposit_address_kraken("XBT", "Bitcoin"))
# print(toolkraken.get_status_deposit_kraken("XBT", "Bitcoin"))
# print(toolkraken.get_status_withdrawal_kraken("USDT", "usdt-wd", 2))
# print(toolkraken.get_deposit_history_kraken("USDT", "Tether USD (TRC20)"))
# print(toolkraken.get_withdraw_history_kraken())
# print(toolkraken.transfer_kraken("USDT", "5", "Spot Wallet", "Futures Wallet"))
# print(toolkraken.get_balances_kraken("USDT"))
print(toolkraken.submit_token_withdrawal_kraken("FTM", 5, "metamaskARB", "Bitcoin")) # not done
