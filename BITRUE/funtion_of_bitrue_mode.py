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

import bitrue.Account_api as Account
import bitrue.Funding_api as Funding
import bitrue.Market_api as Market
import bitrue.Public_api as Public
import bitrue.Trade_api as Trade
import bitrue.subAccount_api as SubAccount
import bitrue.status_api as Status

import logging
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
# from decouple import config

scraper = cloudscraper.create_scraper()
path_file = os.path.dirname(os.path.abspath(__file__))

flag = '0'


class bitrue_FUNCTION:
    def __init__(self, keypass=None):
        print("Init")
        if keypass != None:

            # NHẬP KEY, SECRET của API
            self.api_key = '2098a806ce5de9b3e42af2e4a0a7a6cd3c9ac641cc491a21233ece9e0bfae394'
            self.api_secret = '18e8a4b513c86d843b2b77e12b03deba69f3c189d31fdba9ccab990175fa4b62'

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

    def get_balances_bitrue(self, currency):  # Check số dư của 1 token trên sàn
        while True:
            try:
                currency = currency.lower()
                res = self.FundingAPI.get_balances(currency=currency)
                print("res", res)
                balance = res['result']['availableAmount']
                break
            except:
                time.sleep(1)
                continue

        # print("balance_trading ", balance_trading)
        return self.convert_number_to_smaller(float(balance))

    # Lấy danh sách các lệnh đang được đặt trên sàn
    def get_depth_bitrue(self, symbol, usd, proxy, fake_ip):
        url = f"https://fapi.bitrue.com/fapi/v1/depth"
        symbol = symbol.upper()
        usd = usd.upper()
        params = { 
            'contractName': f"E-{symbol}-{usd}"
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
                return res.json()
        except Exception as e:
            print("Exception: ", e)
            return 0

    # Kiểm tra nếu dùng 1 số usd thì mua được bao nhiêu đồng coin
    def get_return_buy_bitrue(self, symbol, usd, amountin, proxy, fake_ip):
        result = self.get_depth_bitrue(symbol, usd, proxy, fake_ip)
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
    def get_return_sell_bitrue(self, symbol, usd, amountin, proxy, fake_ip):
        result = self.get_depth_bitrue(symbol, usd, proxy, fake_ip)
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
    def find_quantity_price_buy_bitrue(self, symbol, amountin, token_usd, proxy, fake_ip, truotgiasan):
        result = self.get_depth_bitrue(symbol, token_usd, proxy, fake_ip)
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
                # return price_find, total_return*(100-0.1)/100
                return price_find, total_return
        if float(price_find) > price_start*(1+float(truotgiasan)/100):
            print("SOS bitrue -buy " + str(symbol) +
                  str(price_find)+" " + str(price_start))
            return 0, 0
        print("price OK bitrue price_start" +
              str(price_start) + "price_find " + (price_find))

        if float(sum_value_ask) < float(amountin):
            # 0.1 là phí giao dịch của bitrue
            return price_find, total_volume*(100-0.26)/100

    # lệnh buy cần tính chuẩn với khối lượng 1000 usdt mua
    # Hàm mua theo limit
    def real_buy_in_bitrue(self, token_name, token_usd, amounin, amoutoutmin, proxy, fake_ip, truotgiasan):
        symbol = token_name + "_" + token_usd
        price, quantity = self.find_quantity_price_buy_bitrue(symbol=token_name, amountin=amounin, token_usd=token_usd, proxy=proxy, fake_ip=fake_ip, truotgiasan=truotgiasan)
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
            print("real_buy_in_bitrue quantity" + str(quantity) +
                  " < amoutoutmin" + str(amoutoutmin))
            return "Bé hơn amoutoutmin rồi!!!"
        if "e" in str(price):
            price = f'{price:.20f}'
        else:
            price = price
        print("quantity: ", quantity)
        Klin = int(quantity*10**1)/(10**1)
        result = None
        try:
            result = self.TradeAPI.place_order(baseCurrency=token_name, quoteCurrency=token_usd, price=price, side="BUY", quantity=Klin, type_="LIMIT", condition="GTC")
            print("result: ", result)
            # print("result: ", result.status_code)
            print("=== result ===", result) 
        except:
            result = sys.exc_info()
            print("result", result)
            return 
        
        if result['result']['orderId'] != None:
            order_id = result['result']['orderId']
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
            deal_price = order_details['result']['price']
            print("deal_fund", deal_price)
            dealSize = order_details['result']['executedQty']
            print("dealSize", dealSize)
            status = order_details['result']['state']
            print("status", status)
            if 'CANCELED' == status or 'REJECTED' == status:
                if i > 2:
                    print("Lệnh đang buy market còn mở")
                    result = self.TradeAPI.cancel_order(order_id)
                    print("result_cancel_buy", result)
                    if result['result']['cancelId'] != None:
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
    def real_sell_in_bitrue(self, token_name, token_usd, amounin, amoutoutmin, proxy, fake_ip, truotgiasan):
        symbol = token_name + '_' + token_usd

        price, quantity = self.find_quantity_price_sell_bitrue(
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
            print("real_sell_in_bitrue quantity" + str(quantity) +
                  " < amoutoutmin" + str(amoutoutmin))
            return "Bé hơn amoutoutmin rồi!!!"

        Klin = int(amounin*10**1)/(10**1)
        print("khối lượng vào", Klin)
        try:
            result = self.TradeAPI.place_order(baseCurrency=token_name, quoteCurrency=token_usd, price=price, side="SELL", quantity=Klin, type_="LIMIT", condition="GTC")
        except:
            print("Lỗi ", sys.exc_info())

        if result['result']['orderId'] != None:
            order_id = result['result']['orderId']
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
            deal_price = order_details['result']['price']
            print("deal_fund", deal_price)
            dealSize = order_details['result']['executedQty']
            print("dealSize", dealSize)
            status = order_details['result']['state']
            print("status", status)
            if 'CANCELED' == status or 'REJECTED' == status:
                if i > 2:
                    print("Lệnh sell đang còn mở")
                    result = self.TradeAPI.cancel_order(order_id)
                    print("result_cancel_buy", result)
                    if result['result']['cancelId'] != None:
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
    def find_quantity_price_sell_bitrue(self, symbol, amountin, token_usd, proxy, fake_ip, truotgiasan):
        result = self.get_depth_bitrue(symbol, token_usd, proxy, fake_ip)
        # print(f"get_depth_bitrue {result}")
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
                return price_find, total_return
                # return price_find, total_return*(100-0.1)/100   # nếu return như này thì sẽ bị lỗi: The order price or quantity precision is abnormal
            # print("price", price_find )
        if float(price_find) < price_start/(1+float(truotgiasan)/100):
            print("SOS " + str(price_find)+" " + str(price_start))
            return 10000000, 0
        print("price OK bitrue" + str(price_start) +
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

    # Lấy địa chỉ nạp tiền lên bitrue
    def get_deposit_address_bitrue(self, currency, chain):
        currency = currency.upper()
        if chain == "Polygon":
            chainID = "Polygon"
        elif chain == "OPT":
            chainID = "OPT"
        elif chain == "TRON":
            chainID = "TRON"
        elif chain == "AVAX":
            chainID = "AVAX"
        elif chain == "ETH":
            chainID = "Ethereum"
        elif chain == "FTM":
            chainID = "Fantom"
        elif chain == "SOL":
            chainID = "SOL-SOL"
        elif chain == "KLAY":
            chainID = "Klaytn"
        elif chain == "ARB":
            chainID = "ARB"
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
        res = self.FundingAPI.get_deposit_address(chain=chainID, currency=currency)
        print("res: ", res)
        depositAddress = res['result']['address']
        # print(f"=== res: {depositAddress}")
        return depositAddress
        # except:
        #     err = str(sys.exc_info())
        #     print("err", err)
        #     print("Kiểm tra lại Chain đi người đẹp!")
        #     return ["No address avaiable"]

    # Lấy trạng thái khả dụng hay bị dừng nạp tiền của 1 token
    def get_status_deposit_bitrue(self, currency, chain):
        currency = currency.lower()
        if chain == "Polygon":
            chainID = "Polygon"
        elif chain == "OPT":
            chainID = "OPT"
        elif chain == "TRON":
            chainID = "TRON"
        elif chain == "AVAX":
            chainID = "AVAX"
        elif chain == "ETH":
            chainID = "Ethereum"
        elif chain == "FTM":
            chainID = "Fantom"
        elif chain == "SOL":
            chainID = "SOL-SOL"
        elif chain == "KLAY":
            chainID = "Klaytn"
        elif chain == "ARB":
            chainID = "ARB"
        else:
            chainID = chain
        print("currency: ", currency)
        # try:
        res = self.FundingAPI.get_currency()
        for item in res['result']:
            if currency.lower() == item['currency'].lower():
                for chain in item['supportChains']:
                    if chain['chain'] == chainID:
                        if chain['depositEnabled'] != True:
                            result_str = f"Tạm dừng nạp tiền rồi. Token {currency}. Chain {chainID}"
                            print(result_str)
                            return None
                        else:
                            return f"Nạp tiền bình thường. Token {currency}. Chain {chainID}"
        # except Exception as e:
        #     print(f"lỗi request {e}")

    # Lấy trạng thái khả dụng hay bị dừng rút tiền
    def get_status_withdrawal_bitrue(self, currency, chain):
        currency = currency.lower()
        if chain == "Polygon":
            chainID = "Polygon"
        elif chain == "OPT":
            chainID = "OPT"
        elif chain == "TRON":
            chainID = "TRON"
        elif chain == "AVAX":
            chainID = "AVAX"
        elif chain == "ETH":
            chainID = "Ethereum"
        elif chain == "FTM":
            chainID = "Fantom"
        elif chain == "SOL":
            chainID = "SOL-SOL"
        elif chain == "KLAY":
            chainID = "Klaytn"
        elif chain == "ARB":
            chainID = "ARB"
        else:
            chainID = chain
        try:
            res = self.FundingAPI.get_currency()
            for item in res['result']:
                if currency.lower() == item['currency'].lower():
                    for chain in item['supportChains']:
                        if chain['chain'] == chainID:
                            status = chain['withdrawEnabled']
                            if status != True:
                                result_str = f"Tạm dừng rút tiền rồi. Token {currency}. Chain {chainID}"
                                print(result_str)
                                return None
                            else:
                                minWithdrawSingle = chain['withdrawMinAmount']
                                return status, minWithdrawSingle
        except Exception as e:
            print(f"lỗi request {e}")

    # Lấy lịch sử nạp tiền
    def get_deposit_history_bitrue(self, currency):
        res = self.FundingAPI.get_deposit_withdrawal_history()
        currency = currency.lower()
        print("res: ", res)
        if res['result']['items'] != None:
            for item in res['result']['items']:
                if currency == item['currency']:
                    status = item['status']
                    print(f"Deposit {item['amount']} {currency}, ID: {item['id']}, TransactionID: {item['transactionId']}, status: {status}")
        else:   
            print("Lỗi get status deposit bitrue")
            return "Lỗi get status deposit bitrue"

    def get_withdraw_history_bitrue(self, currency):  # Lấy lịch sử rút tiền
        currency = currency.lower()
        res = self.FundingAPI.get_withdrawal_history()
        print("res", res)
        if res['result']['items'] != None:
            for item in res['result']['items']:
                if currency == item['currency']:
                    status = item['status']
                    print(f"Withdraw {item['amount']} {currency}, ID: {item['id']}, TransactionID: {item['transactionId']}, status: {status}")
        else:
            print("Lỗi get status deposit bitrue")
            return "Lỗi get status deposit bitrue"

    # Hàm rút tiền từ bitrue về  ví metamask
    def submit_token_withdrawal_bitrue(self, currency, chainID, amount, destinationAddress):
        balance = self.get_balances_bitrue(currency)
        print("balance: ", balance)
        status = ''
        currencyBinding = ''
        # res = self.FundingAPI.get_list_deposit_address(currency=currency)
        # if len(res) == 0:
        #     return ["No address avaiable"]
        # for re in res:
        #     if re['providerName'] == chainID:
        #         currencyBinding = re['id']
        if float(balance) > 0 and float(balance) >= float(amount):
            try:
                print("size: ", amount)
                res = self.FundingAPI.coin_withdraw(currency, chainID, amount, destinationAddress)
                print("submit_token_withdrawal_bitrue ", res)
                if res['result']['id']:
                    withdrawal_ID = res['result']['id']
                    print("withdrawal_ID", withdrawal_ID)
                    print("Đã rút tiền chờ tiền về tài khoản!")
                    status = "Đã rút tiền chờ tiền về tài khoản!"
                    return True, status, withdrawal_ID
                else:
                    print("Rút tiền thất bại! " + str(res['mc']))
                    status = res['mc']
                    return False, status, 0
            except:
                err = str(sys.exc_info())
                print("Lỗi submit_token_withdrawal_bitrue ", err)
                status = err
                return 'False1', status, 0
        else:
            print("Không đủ tiền để rút rồi người đẹp!")
            status = "Không đủ tiền rút rồi!!!"
            return False, status, 0

    def transfer_bitrue(self, bizId, source, to, currency, symbol, amount):  # Chuyển tiền tron nội bộ sàn ( Có nhiều sàn ko cần chức năng này)
        try:
            currency = currency.lower()
            res=  self.FundingAPI.funds_transfer(bizId, source, to, currency, symbol, amount)# 18:trading, 6: funding
            print("res: ", res)
        except:
            print("Lỗi transfer main to trading_bitrue ", str(sys.exc_info()))
            return "Lỗi transfer main to trading_bitrue " + str(sys.exc_info())
        if res['mc'] == 'SUCCESS':
            print("chuyển tiền thành công")
            status="chuyển tiền thành công"
        else:
            print("Lỗi chuyển tiền OKX "+ str(res))
            status="Lỗi chuyển tiền OKX"+ str(res)
        return status


toolbitrue = bitrue_FUNCTION(keypass='')

# print(toolbitrue.get_depth_bitrue("btc", "usdt", "", "")) done

# print(toolbitrue.get_return_buy_bitrue(symbol="etc", usd="usdt", amountin=1, proxy="", fake_ip=False)) done

# print(toolbitrue.get_return_sell_bitrue(symbol="btc", usd="usdt", amountin=1, proxy="", fake_ip=False)) done

# print(toolbitrue.find_quantity_price_buy_bitrue("eth", 3, "usdt", "", "", 0.1)) done
# print(toolbitrue.find_quantity_price_sell_bitrue("btc", 1, "usdt", "", "", 0.1)) done

print(toolbitrue.real_buy_in_bitrue("ADA", "USDT", 7, 0, "", "", 0.1))
# print(toolbitrue.real_sell_in_bitrue("ada", "usdt", 5.34, 0, "", False, 5)) 

# print(toolbitrue.get_deposit_address_bitrue("USDT", "SOL")) 

# print(toolbitrue.get_status_deposit_bitrue("usdt", "ETH")) 
# print(toolbitrue.get_status_withdrawal_bitrue("usdt", "ETH")) 

# print(toolbitrue.get_deposit_history_bitrue("USDT")) 
# print(toolbitrue.get_withdraw_history_bitrue("usdt"))  
# print(toolbitrue.get_balances_bitrue("usdt"))

# print(toolbitrue.submit_token_withdrawal_bitrue("usdt", "Polygon" , 10, "0x09a1e5cE84299aA2378b861F56467708F70640AB")) 
# print(toolbitrue.submit_token_withdrawal_bitrue("USDT", 2.5, "USDT_ARB")) # no

# Nếu chuyển từ spot sang future thì phải thêm symbol, example: bitrue_usdt
# toolbitrue.transfer_bitrue("1233423423dcsdfeadeadeqasdsdfasdsewaddfddceceqcw", "SPOT", "LEVER", "usdt", "bitrue_usdt", 3) 
# toolbitrue.transfer_bitrue("1233423423dcsdfeadeadedssfasdsewaddfddceceqcw", "FINANCE", "SPOT", "usdt", "", 3) 