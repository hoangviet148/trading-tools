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

import xt.Account_api as Account
import xt.Funding_api as Funding
import xt.Market_api as Market
import xt.Public_api as Public
import xt.Trade_api as Trade
import xt.subAccount_api as SubAccount
import xt.status_api as Status

import logging
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
# from decouple import config

scraper = cloudscraper.create_scraper()
path_file = os.path.dirname(os.path.abspath(__file__))

flag = '0'


class xt_FUNCTION:
    def __init__(self, keypass=None):
        print("Init")
        if keypass != None:

            # NHẬP KEY, SECRET của API
            self.api_key = '1b63b469-30ed-4d17-9436-43e3d6dec6ce'
            self.api_secret = 'e9afbc48bdf5e7158c1270c9e804131f1a77d6ab'

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

    def get_balances_xt(self, currency):  # Check số dư của 1 token trên sàn
        while True:
            try:
                res = self.FundingAPI.get_balances(currency=currency, type_="ACCOUNT_TYPE_WALLET")
                print("res", res)
                balance = res['available']
                break
            except:
                time.sleep(1)
                continue

        # print("balance_trading ", balance_trading)
        return self.convert_number_to_smaller(float(balance))

    # Lấy danh sách các lệnh đang được đặt trên sàn
    def get_depth_xt(self, symbol, usd, proxy, fake_ip):
        url = f"https://sapi.xt.com/v4/public/depth"
        params = { 
            'symbol': f"{symbol}_{usd}",
            'limit': '50'              
        }
        try:
            if fake_ip == True:
                proxies = {
                    'http': str(proxy),
                    'https': str(proxy)
                }
                res = requests.get(url, params=params, proxies=proxies, timeout=5)
                
            else:
                res = requests.get(url, params=params, timeout=5)

            if res.status_code != 200:
                return 0
            else:
                # print(res.json())
                return res.json()
        except Exception as e:
            print("Exception: ", e)
            return 0

    # Kiểm tra nếu dùng 1 số usd thì mua được bao nhiêu đồng coin
    def get_return_buy_xt(self, symbol, usd, amountin, proxy, fake_ip):
        result = self.get_depth_xt(symbol, usd, proxy, fake_ip)['result']
        # print("result: ", result['result']['timestamp'])
        # print("result: ", result['timestamp'])
        try:
            list_asks = result['asks']
            # print("list_buys: ", list_asks)
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
        # print("sum_value_ask: ", sum_value_ask)
        if float(sum_value_ask) < float(amountin):
            return (total_volume)*(100-0.26)/100

    # Kiểm tra nếu dùng 1 số coin thì bán ra được bao nhiêu đồng usd
    def get_return_sell_xt(self, symbol, usd, amountin, proxy, fake_ip):
        result = self.get_depth_xt(symbol, usd, proxy, fake_ip)['result']
        try:
            list_bids = result['bids']
        except:
            return 0
        sum_value_bids = 0
        total_volume = 0
        # print("list_bids: ", list_bids)
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
    def find_quantity_price_buy_xt(self, symbol, amountin, token_usd, proxy, fake_ip, truotgiasan):
        result = self.get_depth_xt(symbol, token_usd, proxy, fake_ip)['result']
        # print(result)
        try:
            list_asks = result['asks']
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
            print("SOS xt -buy " + str(symbol) +
                  str(price_find)+" " + str(price_start))
            return 0, 0
        print("price OK xt price_start" +
              str(price_start) + "price_find " + (price_find))

        if float(sum_value_ask) < float(amountin):
            # 0.1 là phí giao dịch của xt
            return price_find, total_volume*(100-0.26)/100

    # lệnh buy cần tính chuẩn với khối lượng 1000 usdt mua
    # Hàm mua theo limit
    def real_buy_in_xt(self, token_name, token_usd, amounin, amoutoutmin, proxy, fake_ip, truotgiasan):
        symbol = token_name + "_" + token_usd
        price, quantity = self.find_quantity_price_buy_xt(symbol=token_name, amountin=amounin, token_usd=token_usd, proxy=proxy, fake_ip=fake_ip, truotgiasan=truotgiasan)
        if "e" in str(price):
            price = f'{price:.10f}'
        else:
            price = price
        print("price", price)
        print("quantity", quantity)
        if quantity == 0:
            print("Do truot gia cua san qua cao")
            return "Do truot gia cua san qua cao"
        if quantity < amoutoutmin:
            print("real_buy_in_xt quantity" + str(quantity) +
                  " < amoutoutmin" + str(amoutoutmin))
            return "Bé hơn amoutoutmin rồi!!!"
        if "e" in str(price):
            price = f'{price:.20f}'
        else:
            price = price
        Klin = int(quantity*10**3)/(10**3)
        print("Klin ", Klin)
        print("price ", price)
        result = None
        try:
            result = self.TradeAPI.place_order(baseCurrency=token_name, quoteCurrency=token_usd, price=price, side="BUY", quantity=Klin, type_="LIMIT", condition="IOC")
            print("result: ", result.status_code)
            print("=== result ===", result) 
        except:
            result = sys.exc_info()
            print("result", result)
            return 
        
        if result['status'] == "SUCCESS":
            order_id = result['id']
            print("Đã đặt lệnh thành công")
        else:
            print("Lỗi rồi.....", result)
            return result

        print("order_id", order_id)
        order_details = None
        for i in range(4):
            response = self.TradeAPI.get_orders(order_id)
            order_details = response
            print("get_order_details ", order_details)
            deal_price = order_details['price']
            print("deal_fund", deal_price)
            dealSize = order_details['quantity']
            print("dealSize", dealSize)
            status = order_details['status']
            print("status", status)
            if 'ORDER_STATUS_REJECTED' in status or 'ORDER_STATUS_CLOSED' in status:
                if i > 2:
                    print("Lệnh đang buy market còn mở")
                    result = self.TradeAPI.cancel_order(order_id)
                    print("result_cancel_buy", result)
                    if result['status'] == 'SUCCESS':
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
    def real_sell_in_xt(self, token_name, token_usd, amounin, amoutoutmin, proxy, fake_ip, truotgiasan):
        symbol = token_name + '_' + token_usd

        price, quantity = self.find_quantity_price_sell_xt(
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
            print("real_sell_in_xt quantity" + str(quantity) +
                  " < amoutoutmin" + str(amoutoutmin))
            return "Bé hơn amoutoutmin rồi!!!"

        Klin = int(amounin*10**4)/(10**4)
        print("khối lượng vào", Klin)
        try:
            result = self.TradeAPI.place_order(baseCurrency=token_name, quoteCurrency=token_usd, price=price, side="SELL", quantity=Klin, type_="LIMIT", condition="GTC")
        except:
            print("Lỗi ", sys.exc_info())

        if result['status'] == "SUCCESS":
            order_id = result['id']
            print("Đã đặt lệnh thành công")
        else:
            print("Lỗi rồi.....", result)
            return result

        print("order_id", order_id)
        order_details = None
        for i in range(4):
            response = self.TradeAPI.get_orders(order_id)
            order_details = response
            print("get_order_details ", order_details)
            deal_price = order_details['price']
            print("deal_fund", deal_price)
            dealSize = order_details['quantity']
            print("dealSize", dealSize)
            status = order_details['status']
            print("status", status)
            if 'ORDER_STATUS_REJECTED' in status or 'ORDER_STATUS_CLOSED' in status:
                if i > 2:
                    print("Lệnh sell đang còn mở")
                    result = self.TradeAPI.cancel_order(order_id)
                    print("result_cancel_buy", result)
                    if result['status'] == 'SUCCESS':
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
    def find_quantity_price_sell_xt(self, symbol, amountin, token_usd, proxy, fake_ip, truotgiasan):
        result = self.get_depth_xt(symbol, token_usd, proxy, fake_ip)['result']
        # print(f"get_depth_xt {result}")
        try:
            list_bids = result['bids']
        except:
            return 0
        sum_value_bids = 0
        total_volume = 0
        price_start = float(list_bids[0][1])

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
        print("price OK xt" + str(price_start) +
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

    # Lấy địa chỉ nạp tiền lên xt
    def get_deposit_address_xt(self, currency, chain):
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
        currencyBinding = None
        # try:
            # res = self.FundingAPI.get_list_deposit_address(currency=currency)
            
            # if len(res) == 0:
            #     return ["No address avaiable"]
            # for re in res:
            #     if re['providerName'] == chainID:
            #         currencyBinding = re['id']
        res = self.FundingAPI.get_deposit_address(chain='Bitcoin', currency="BTC")
        print("res: ", res)
        depositAddress = res['depositAccount']['address']
        print(f"=== res: {depositAddress}")
        return depositAddress
        # except:
        #     err = str(sys.exc_info())
        #     print("err", err)
        #     print("Kiểm tra lại Chain đi người đẹp!")
        #     return ["No address avaiable"]

    # Lấy trạng thái khả dụng hay bị dừng nạp tiền của 1 token
    def get_status_deposit_xt(self, currency):
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
    def get_status_withdrawal_xt(self, currency):
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
    def get_deposit_history_xt(self, currency, id):
        res = self.FundingAPI.get_deposit_withdrawal_history(id=id)
        print("res", res)
        if len(res) != 0:
            if "DEPOSIT" in res['type']:
                status = res['status']
                print("status", status)
                if status == 'TRANSACTION_STATUS_CONFIRMED':
                    print("Create " + str(currency))
                    sta = "Create.Token: " + str(currency)
                elif status == 'TRANSACTION_STATUS_PENDING':
                    print("Pending " + str(currency))
                    sta = "Pending " + str(currency)
            return sta
        else:
            print("Lỗi get status deposit xt")
            return "Lỗi get status deposit xt"

    def get_withdraw_history_xt(self, wd_id):  # Lấy lịch sử rút tiền
        res = self.FundingAPI.get_deposit_withdrawal_history(id=id)
        print("res", res)
        if len(res) != 0:
            if "WITHDRAWAL" in res['type']:
                status = res['status']
                print("status", status)
                if status == 'TRANSACTION_STATUS_CONFIRMED':
                    print("Create " + str(currency))
                    sta = "Create.Token: " + str(currency)
                elif status == 'TRANSACTION_STATUS_PENDING':
                    print("Pending " + str(currency))
                    sta = "Pending " + str(currency)
            return sta
        else:
            print("Lỗi get status deposit xt")
            return "Lỗi get status deposit xt"

    # Hàm rút tiền từ xt về  ví metamask
    def submit_token_withdrawal_xt(self, currency, chainID, amount, destinationAddress):
        balance = self.get_balances_xt(currency)
        status = ''
        currencyBinding = ''
        res = self.FundingAPI.get_list_deposit_address(currency=currency)
        if len(res) == 0:
            return ["No address avaiable"]
        for re in res:
            if re['providerName'] == chainID:
                currencyBinding = re['id']
        if float(balance) > 0 and float(balance) >= float(amount):
            try:
                print("size ", amount)
                res = self.FundingAPI.coin_withdraw(currencyBinding, amount, destinationAddress)
                print("submit_token_withdrawal_xt ", res)
                if res['withdrawalId']:
                    withdrawal_ID = res['withdrawalId']
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
                print("Lỗi submit_token_withdrawal_xt ", err)
                status = err
                return 'False1', status, 0
        else:
            print("Không đủ tiền để rút rồi người đẹp!")
            status = "Không đủ tiền rút rồi!!!"
            return False, status, 0

    def transfer_xt(self, value, currency):  # Chuyển tiền tron nội bộ sàn ( Có nhiều sàn ko cần chức năng này)
        try:
            res=  self.FundingAPI.funds_transfer(value, currency)# 18:trading, 6: funding
        except:
            print("Lỗi transfer main to trading_xt ", str(sys.exc_info()))
            return "Lỗi transfer main to trading_xt " + str(sys.exc_info())
        if res['code'] =='0':
            print("chuyển tiền thành công")
            status="chuyển tiền thành công"
        else:
            print("Lỗi chuyển tiền OKX "+ str(res))
            status="Lỗi chuyển tiền OKX"+ str(res)
        return status


toolxt = xt_FUNCTION(keypass='')

#print(toolxt.get_depth_xt("btc", "usdt", "", "")) done
# print(toolxt.get_return_buy_xt(symbol="btc", usd="usdt", amountin=, proxy="", fake_ip=False)) done

# print(toolxt.get_return_sell_xt(symbol="btc", usd="usdt", amountin=1, proxy="", fake_ip=False)) done

# print(toolxt.find_quantity_price_buy_xt("btc", 1, "usdt", "", "", 0.1)) done
# print(toolxt.find_quantity_price_sell_xt("btc", 1, "usdt", "", "", 0.1)) done

# print(toolxt.real_buy_in_xt("trx", "usdt", 0.1, 0, "", "", 0.5)) 
# print(toolxt.real_sell_in_xt("BTC", "USDT", 10, 0, "proxy", False, 5))

print(toolxt.get_deposit_address_xt("USDT", "ETH"))
# print(toolxt.get_status_deposit_xt("BTC"))
# print(toolxt.get_status_withdrawal_xt("FTM")) # no
# print(toolxt.get_deposit_history_xt("USDT", "aca0a1da-6c12-42e7-a64c-55fde1da28a8"))  # no
# print(toolxt.get_withdraw_history_xt("1"))  # no
# print(toolxt.get_balances_xt("BTC")) # no
# print(toolxt.submit_token_withdrawal_xt("USDT", "TRC20" , 5 ,"0x5a66f58a075df679e87956702c74a86dc121a79f")) # no
# print(toolxt.submit_token_withdrawal_xt("USDT", 2.5, "USDT_ARB")) # no

# toolxt.transfer_xt(1, ["USDT"])