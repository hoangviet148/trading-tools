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
import secrets
from base64 import urlsafe_b64encode as b64e, urlsafe_b64decode as b64d
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from getpass import getpass
from decouple import config
# import pandas as pd

import bitmart.Account_api as Account
import bitmart.Funding_api as Funding
import bitmart.Market_api as Market
#import bitmart.Public_api as Public
import bitmart.Trade_api as Trade
#import bitmart.subAccount_api as SubAccount
#import bitmart.status_api as Status
# import function_of_bina_SP
import random
import logging
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
# from decouple import config

scraper = cloudscraper.create_scraper()
path_file = os.path.dirname(os.path.abspath(__file__))

flag = '0'
backend = default_backend()
iterations = 100_000

class BITMART_FUNCTION:
    def __init__(self, keypass=None):
        #print("Init")
        if keypass != None:
            self.keypass = keypass
            list_infor_team= config('INFOR_TEAM')

            list_infor_team= list_infor_team.encode()
            list_infor_team = self.password_decrypt(list_infor_team, self.keypass).decode()

            self.list_infor_team= json.loads(list_infor_team)

            #print(list_infor_team)
            myteam = config('MY_TEAM')
            all_infor_of_team = self.list_infor_team['TEAM_'+ str(myteam)]
            #print("all_infor_of_team", all_infor_of_team)

            self.api_key = '5326ea6315dcf6901df0ab6cc40bd156473baefe'
            self.api_secret = '1f1424dfbdcc9bc36aa4b2a9cad9c6dcb9cc43f7e22302b223a4bf79ec028a03'
            self.memo = all_infor_of_team['label_api_bitmart']

            self.FundingAPI = Funding.FundingAPI(self.api_key, self.api_secret, self.memo)
            self.TradeAPI = Trade.TradeAPI(self.api_key, self.api_secret, self.memo)
            self.AccountAPI = Account.AccountAPI(self.api_key, self.api_secret, self.memo)
            self.MarketAPI = Market.MarketAPI(self.api_key, self.api_secret, self.memo)
            # self.toolbina = function_of_bina_SP.FUNCTION_BINA()#print("Init Done")
            self.list_all_token_bitmart =  self.all_token_in_bitmart()

    def _derive_key(self, password: bytes, salt: bytes, iterations: int = iterations) -> bytes:
        """Derive a secret key from a given password and salt"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(), length=32, salt=salt,
            iterations=iterations, backend=backend)
        return b64e(kdf.derive(password))

    def password_encrypt(self, message: bytes, password: str, iterations: int = iterations) -> bytes:
        salt = secrets.token_bytes(16)
        key = self._derive_key(password.encode(), salt, iterations)
        return b64e(
            b'%b%b%b' % (
                salt,
                iterations.to_bytes(4, 'big'),
                b64d(Fernet(key).encrypt(message)),
            )
        )

    def password_decrypt(self, token: bytes, password: str) -> bytes:
        decoded = b64d(token)
        salt, iter, token = decoded[:16], decoded[16:20], b64e(decoded[20:])
        iterations = int.from_bytes(iter, 'big')
        key = self._derive_key(password.encode(), salt, iterations)
        return Fernet(key).decrypt(token)


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
        number = int(float(number)*(10**int(decimal_places)))/(10**int(decimal_places))
        return number


    def get_stepprice_size(self, symbol):
        url='https://api-cloud.bitmart.com/spot/v1/symbols/details'

        token=symbol.upper()
        print("token", token)
        res=requests.get(url)
        result=res.json()['data']['symbols']
        #print("result", result)
        for data in result:
            #print(data)
            #print(".....................")
            if  token in data['base_currency']:
                print("data", data)
                step_price=data['price_max_precision']
                print("step_price", step_price)
                step_size=data['quote_increment']
                print("step_size", step_size)
                return step_price, step_size   


    def get_balances_bitmart(self, currency):  # Check số dư của 1 token trên sàn

        try:
            res = self.FundingAPI.get_balances(currency=currency)
            #print("res", res)
            if res['data']['wallet'] == []:
                balance = 0
                return 0
            else:
                balance = res['data']['wallet'][0]['available']
                ##print("balance_bitmart", balance)
                return self.convert_number_to_smaller(float(balance))
        except:
            print("Lỗi request bitmart " + str(sys.exc_info()))
            return "x.x"


    # Lấy danh sách các lệnh đang được đặt trên sàn
    def get_depth_bitmart_api(self, symbol, usd, proxy, fake_ip):
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
                res = scraper.get(url, params=params, proxies=proxies, timeout=5).json()
            else:
                res = scraper.get(url, params=params, timeout=5).json()

            #print("get_depth_bitmart api = ", res)
            if res['code'] != 1000:
                return 0
            else:
                return res['data']
        except: 
            print("Lỗi request: " + str(sys.exc_info()))
            return 0

    def get_depth_bitmart_web(self, symbol, usd, proxy="", fake_ip=False):
        try:
            token = (symbol + "-" + usd).upper()
            headers= {
                "authority":"www.bitmart.com",
                "method":"GET",
                "path": f"/gw-api/quotation/market_depth_all?tradeMappingName={token}&maxSize=50",
                "scheme":"https",
                "accept":"application/json, text/plain, */*",
                "accept-encoding":"gzip, deflate, br",
                "accept-language":"en-US,en;q=0.9,vi;q=0.8",
                "cache-control":"no-cache",
                "nomessagelist":"3",
                "pragma":"no-cache",
                "referer":"https://www.bitmart.com/trade/en-US?layout=pro",
                "sec-ch-ua":'"`"Not.A/Brand`";v=`"8`", `"Chromium`";v=`"114`", `"Google Chrome`";v=`"114`""',
                "sec-ch-ua-mobile":"?0",
                "sec-ch-ua-platform":'"`"Windows`""',
                "sec-fetch-dest":"empty",
                "sec-fetch-mode":"cors",
                "sec-fetch-site":"same-origin",
                "sw8":"1-MDQxMTJlNjMtZjFkZS00Y2VjLWFhMGQtYzI0ZGYxMzE5NDNm-YTczNjcxODMtMWFlNC00MmQ1LWE2YTItZWU4MTMyNzJlZDI3-0-Yml0bWFydC1mcm9udGVuZC1jbGllbnQ=-djEuMC4w-L3RyYWRlL2VuLVVT-d3d3LmJpdG1hcnQuY29t",
                "x-bm-client":"WEB",
                "x-bm-device":"7d2dfcc59c944abfcca019e125549e86",
                "x-bm-host":"www.bitmart.com",
                "x-bm-local":"en_US",
                "x-bm-sensors-distinct-id":"188f36ac78513a-07853b7ccdec7a-26031d51-2073600-188f36ac7862a70",
                "x-bm-timezone":"Asia/Saigon",
                "x-bm-timezone-offset":"-420",
                "x-bm-ua":"",
                "x-bm-version":"1.0.0",
                "ContentType": "application/x-www-form-urlencoded;charset=UTF-8",
                "Cookie":"_gcl_au=1.1.1742586168.1687711041; __adroll_fpc=be1a23cc46266a218dede74ac6a49c93-1687711041877; _ym_uid=1687711042288352729; _ym_d=1687711042; cf_clearance=U9COIIdb9XCH1FPA_pe9hB4jt02mQXY0hNCf5Il00qQ-1688444317-0-160; _ga_0V649X1YZB=GS1.1.1688444343.2.1.1688444959.60.0.0; zendeskUserData={%22cid%22:null%2C%22userId%22:null%2C%22mainId%22:null%2C%22userType%22:null%2C%22userTypeId%22:null%2C%22userTypeName%22:null%2C%22remark%22:null%2C%22salt%22:null%2C%22loginName%22:%22dtn.coin@gmail.com%22%2C%22maskingLoginName%22:%22dtn****@gmail.com%22%2C%22bindGoogle%22:%22F%22%2C%22bindPhone%22:%22F%22%2C%22bindMail%22:%22T%22%2C%22bindEmail%22:%22T%22%2C%22userStatus%22:null%2C%22userStatusEnabled%22:null%2C%22tradeStatusEnabled%22:null%2C%22depositFiatEnabled%22:null%2C%22withdrawFiatEnabled%22:null%2C%22depositVirtualEnabled%22:null%2C%22withdrawVirtualEnabled%22:null%2C%22contractTransferEnabled%22:null%2C%22fiatTransferEnabled%22:null%2C%22otcTransferEnabled%22:null%2C%22otcTradeEnabled%22:null%2C%22contractTradeEnabled%22:null%2C%22subscribeEarnEnabled%22:null%2C%22redemptionEarnEnabled%22:null%2C%22fundTransferEnabled%22:null%2C%22leverRiskEnabled%22:null%2C%22internalWithdrawEnabled%22:null%2C%22switchJson%22:null%2C%22phone%22:%22%22%2C%22areaCode%22:%22%22%2C%22mail%22:%22dtn.coin@gmail.com%22%2C%22email%22:%22dtn.coin@gmail.com%22%2C%22gaSecret%22:null%2C%22gaUrl%22:null%2C%22inviteCode%22:null%2C%22registerTime%22:null%2C%22registerIp%22:null}; _ga=GA1.1.1987269626.1687711042; sensorsdata2015jssdkcross=%7B%22distinct_id%22%3A%2210900650%22%2C%22first_id%22%3A%22188f36ac78513a-07853b7ccdec7a-26031d51-2073600-188f36ac7862a70%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E7%9B%B4%E6%8E%A5%E6%B5%81%E9%87%8F%22%2C%22%24latest_search_keyword%22%3A%22%E6%9C%AA%E5%8F%96%E5%88%B0%E5%80%BC_%E7%9B%B4%E6%8E%A5%E6%89%93%E5%BC%80%22%2C%22%24latest_referrer%22%3A%22%22%7D%2C%22identities%22%3A%22eyIkaWRlbnRpdHlfY29va2llX2lkIjoiMTg4ZjM2YWM3ODUxM2EtMDc4NTNiN2NjZGVjN2EtMjYwMzFkNTEtMjA3MzYwMC0xODhmMzZhYzc4NjJhNzAiLCIkaWRlbnRpdHlfbG9naW5faWQiOiIxMDkwMDY1MCJ9%22%2C%22history_login_id%22%3A%7B%22name%22%3A%22%24identity_login_id%22%2C%22value%22%3A%2210900650%22%7D%2C%22%24device_id%22%3A%22188f36ac78513a-07853b7ccdec7a-26031d51-2073600-188f36ac7862a70%22%7D; _ym_isad=2; _cfuvid=6R1DADvmPOd5DNAiUKYWvjXHvJGT5dTJJ1dmKHuTXXM-1688807176441-0-604800000; isDayMode=false; __cf_bm=fTiZNKdKNh8nWSDTTEnKamSXecx4GAM17Jery5N1fPY-1688824679-0-AXy0NpcpYJoNYYgX39tQ0PDW+5q0ufTR6PR6mvKrmjVWX1+VEY/9Lm6fueFk77t2lB9Yfj6bn4U0H7Hd1hHXnno=; _ym_visorc=b; tradeType=pro; _ga_R8QWWJS24Y=GS1.1.1688824678.19.1.1688824683.55.0.0; __ar_v4=A7Q5K5D3MZE5TMGLZ7UG4J%3A20230625%3A102%7CDG4F44XG2BFTPCKNR4LF2B%3A20230625%3A102",                
            } 

            url = f"https://www.bitmart.com/gw-api/quotation/market_depth_all?tradeMappingName={token}&maxSize=50"
            if fake_ip == True:
                proxies = {
                    'http': str(proxy),
                    'https': str(proxy)
                }
                res = scraper.get(url, headers=headers, proxies=proxies, timeout=5)
            else:
                res = scraper.get(url, headers=headers ,timeout=5)
            #print(res.json()) 
            res= res.json()['data']
            #print("get_depth_bitmart web = ", res)
            return res
        except:
            print("get_depth_bitmart web = ", 0)
            return 0


    def get_depth_bitmart(self, symbol, usd, proxy="", fake_ip=False):
        resu = random.choice([1,0])
        if resu== 0:
            result= self.get_depth_bitmart_web(symbol, usd, proxy, fake_ip)
        else:
            result= self.get_depth_bitmart_api(symbol, usd, proxy, fake_ip)
        return result
    
    # Kiểm tra nếu dùng 1 số usd thì mua được bao nhiêu đồng coin
    def get_return_buy_bitmart(self, symbol, usd, amountin, proxy, fake_ip):
        result = self.get_depth_bitmart(symbol, usd, proxy, fake_ip)
        # print("result ", result)
        try:
            list_asks = result['sells']
            #print("list_buys ", list_asks)
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
                tien_con_thieu = amountin - (sum_value_ask - float(ask['price'])*float(ask['amount']))
                # print("tien_con_thieu ", tien_con_thieu)
                total_return = total_volume - float(ask['amount']) + tien_con_thieu/float(ask['price'])
                # print("total_return", total_return)
                return float(total_return)*(100-0.1)/100
        if float(sum_value_ask) < float(amountin):
            return (total_volume)*(100-0.1)/100

    # Kiểm tra nếu dùng 1 số coin thì bán ra được bao nhiêu đồng usd
    def get_return_sell_bitmart(self, symbol, usd, amountin, proxy, fake_ip):
        result = self.get_depth_bitmart(symbol, usd, proxy, fake_ip)
        try:
            list_bids = result['buys']
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
                total_return = sum_value_bids - float(bid['price'])*float(bid['amount']) + tien_con_thieu*float(bid['price'])
                # print("total_return", total_return)
                return float(total_return)*(100-0.1)/100
        if float(total_volume) < float(amountin):
            return float(sum_value_bids)*(100-0.1)/100


    def get_return_buy_bitmart_with_USDTETH(self, symbol, usd, amountin, proxy, fake_ip):
        #result_sell_ETH = self.get_return_sell_Okx('ETH', 'USDT', amountin, proxy, fake_ip)
        result_sell_ETH = self.toolbina.get_return_sell_binance_order("ETHUSDT",amountin, proxy, fake_ip)
        #print("result_sell_ETH ", result_sell_ETH)
        result_buy_token = self.get_return_buy_bitmart(symbol, 'USDT', result_sell_ETH, proxy, fake_ip)
        #print("result_buy_token ", result_buy_token)
        return result_buy_token

    def get_return_sell_bitmart_with_USDTETH(self, symbol, usd, amountin, proxy, fake_ip):
        result_sell_token = self.get_return_sell_bitmart(symbol, 'USDT', amountin, proxy, fake_ip)
        print("result_sell_token ", result_sell_token)
        #result = self.get_return_buy_Okx('ETH', 'USDT', result_sell_token, proxy, fake_ip)
        result = self.toolbina.get_return_buy_binance_order("ETHUSDT",result_sell_token, proxy, fake_ip)
        print("result ", result)
        return result


    def get_best_return_buy_bitmart_withETH(self, symbol, amountin, proxy, fake_ip):
        executor = ThreadPoolExecutor(max_workers=2)
        #list_hop = ['ETH', 'USDTETH']
        list_hop = ['USDTETH']
        res = []
        #f1 = executor.submit(self.get_return_buy_Okx, symbol, "ETH", amountin, proxy, fake_ip)  # Mua trực tiếp bằng ETH
        f2 = executor.submit(self.get_return_buy_bitmart_with_USDTETH, symbol, "USDT", amountin, proxy, fake_ip)  # USDT ->ETH ->token
        #f3 = executor.submit(self.get_return_buy_Okx_with_BTCETH, symbol, "BTC", amountin, proxy, fake_ip)  # USDT ->ETH ->token

        #res.append(f1.result())
        res.append(f2.result()) 
        #res.append(f3.result()) 

        max_result_buy =  max(res)
        max_index_buy = res.index(max_result_buy)

        return max_result_buy, list_hop[max_index_buy]



    def get_best_return_sell_bitmart_withETH(self, symbol, amountin, proxy, fake_ip):
        executor = ThreadPoolExecutor(max_workers=2)
        #list_hop = ['ETH', 'USDTETH']
        list_hop = ['USDTETH']
        res = []
        #f1 = executor.submit(self.get_return_sell_Okx, symbol, "ETH", amountin, proxy, fake_ip)  # Mua trực tiếp bằng ETH
        f2 = executor.submit(self.get_return_sell_bitmart_with_USDTETH, symbol, "USDT", amountin, proxy, fake_ip)  # USDT ->ETH ->token
        #f3 = executor.submit(self.get_return_sell_Okx_with_BTCETH, symbol, "BTC", amountin, proxy, fake_ip)  # USDT ->ETH ->token
        #res.append(f1.result())
        res.append(f2.result()) 
        #res.append(f3.result()) 
        print("res get_best_return_sell_bitmart_withETH ", res)
        max_result_sell =  max(res)
        max_index_sell = res.index(max_result_sell)

        return max_result_sell, list_hop[max_index_sell]

    # Tìm giá khớp lệnh cuối cùng, và lượng token có thể nhận được khi mua
    def find_quantity_price_buy_bitmart(self, symbol, amountin, token_usd, proxy, fake_ip, truotgiasan):
        try:
            result = self.get_depth_bitmart(symbol, token_usd, proxy, fake_ip)
            # print(result)
            list_asks = result['sells']
        except:
            return "ERR", "ERR"
        # print(list_bids)
        # print(list_asks)
        sum_value_ask = 0
        total_volume = 0
        price_start = float(list_asks[0]['price'])
        for ask in list_asks:
            sum_value_ask = sum_value_ask + float(ask['price'])*float(ask['amount'])
            total_volume = total_volume + float(ask['amount'])
            #print("sum_value_ask", sum_value_ask)
            #print("total_volume", total_volume)
            #print("------------")
            price_find = ask['price']
            if float(sum_value_ask) >= float(amountin):
                # print(ask)
                tien_con_thieu = float(
                    amountin) - (float(sum_value_ask) - float(ask['price'])*float(ask['amount']))
                #print("tien_con_thieu", tien_con_thieu)
                total_return = float(total_volume) - float(ask['amount']) + tien_con_thieu/float(ask['price'])
                #print("total_return", total_return)
                return price_find, total_return*(100-0.1)/100
        if float(price_find) > price_start*(1+float(truotgiasan)/100):
            #print("SOS bitmart -buy " + str(symbol) +str(price_find)+" " + str(price_start))
            return 0, 0
        #print("price OK bitmart price_start" +str(price_start) + "price_find " + (price_find))

        if float(sum_value_ask) < float(amountin):
            # 0.1 là phí giao dịch của bitmart
            return price_find, total_volume*(100-0.1)/100


    # Tìm giá khơp lệnh cuối cùng và số tiền nhận được khi bán token
    def find_quantity_price_sell_bitmart(self, symbol, amountin, token_usd, proxy, fake_ip, truotgiasan):
        try:
            result = self.get_depth_bitmart(symbol, token_usd, proxy, fake_ip)
            # print(f"get_depth_bitmart {result}")
        
            list_bids = result['buys']
        except:
            return "ERR", "ERR"
        #print("list_bids ", list_bids)
        sum_value_bids = 0
        total_volume = 0
        price_start = float(list_bids[0]['amount'])

        for bid in list_bids:
            sum_value_bids = sum_value_bids + float(bid['price'])*float(bid['amount'])  # tiền
            total_volume = total_volume + float(bid['amount'])  # khối lượng
            #print("sum_value_bids", sum_value_bids)
            #print("total_volume", total_volume)
            #print("------------")
            price_find = bid['price']
            #print("price_find ", price_find)

            if float(total_volume) >= float(amountin):
                tien_con_thieu = amountin - (total_volume - float(bid['amount']))
                #print("tien_con_thieu", tien_con_thieu)
                total_return = sum_value_bids - float(bid['price'])*float(bid['amount']) + tien_con_thieu*float(bid['price'])
                #print("total_return", total_return)
                return price_find, total_return*(100-0.1)/100
            # print("price", price_find )
        if float(price_find) < price_start/(1+float(truotgiasan)/100):
            #print("SOS " + str(price_find)+" " + str(price_start))
            return 10000000, 0
        #print("price OK bitmart" + str(price_start) + "price_find " + (price_find))

        if float(total_volume) < float(amountin):
            return price_find, sum_value_bids * (100-0.1)/100

    # lệnh buy cần tính chuẩn với khối lượng 1000 usdt mua
    # Hàm mua theo limit
    def real_buy_in_bitmart(self, token_name, token_usd, amounin, amoutoutmin, proxy, fake_ip, truotgiasan):
        symbol = token_name + "_" + token_usd
        print("symbol", symbol)
        price, quantity = self.find_quantity_price_buy_bitmart(symbol=token_name, amountin=amounin, token_usd=token_usd, proxy=proxy, fake_ip=fake_ip, truotgiasan=truotgiasan)
        print("price", price)
        print("quantity", quantity)
        if quantity == 0:
            print("Do trượt giá sàn quá cao")
            return "ERR Do trượt giá sàn quá cao"
        
        if quantity == "ERR":
            print("Lỗi request depth")
            return "Lỗi request depth"    

        if quantity < amoutoutmin:
            print("real_buy_in_bitmart quantity" + str(quantity) + " < amoutoutmin" + str(amoutoutmin))
            return "ERR Bé hơn amoutoutmin rồi!!!"
        
        step_price, step_size = self.get_stepprice_size(token_name.upper())
        if float(step_size) >= 1:
            #quantity =  int(quantity*(int(mu)))/(int(mu))
            Klin = int(quantity)
            print("quantity 1", Klin)
        else:
            if float(step_size) <= 0.00001:
                mu =  int(1/ float(step_size)) + 1  # Do lúc này chia ra chỉ được 99999.99999999999
            else:
                mu =  int(1/ float(step_size))
            print("real_buy_in_bitmart mu", mu)
            #quantity =  int(quantity/float(get_stepprice))*(float(get_stepprice))
            Klin =  int(quantity*(int(mu)))/(int(mu))
            print("real_buy_in_bitmart quantity 1", Klin)

        try:
            result = self.TradeAPI.place_order(side="buy", symbol=symbol, price=price, type_='limit', size=Klin)
            print("result", result)
        except:
            print("ERR Lỗi: ", sys.exc_info())
            return "ERR lỗi đặt lệnh"+ str(sys.exc_info())

        if result['code'] == 1000:
            order_id = result['data']['order_id']
            print("Đã đặt lệnh thành công")
        else:
            print("Lỗi rồi.....", result)
            return "ERR " + str(result)

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
                    try:
                        print("Lệnh đang buy limit còn mở")
                        result = self.TradeAPI.cancel_order(order_id)
                        print("result_cancel_buy", result)
                        if result['code'] == '0':
                            print("ĐÃ HỦY LỆNH THÀNH CÔNG!!!")
                            if deal_price == '0':
                                result = "KHÔNG MUA ĐƯỢC__ĐÃ HỦY LỆNH THÀNH CÔNG!!! Nhận "+ str(dealSize) + "Hết =" + str(float(dealSize)*float(deal_price))
                            else:
                                result = "1 Phần ĐÃ HỦY LỆNH. Nhận " + str(dealSize) + "Hết =" + str(float(dealSize)*float(deal_price)) 
                        else:
                            result = "HỦY LỆNH THẤT BẠI!!! Vào Hủy tay Nhận" + str(dealSize) + "Hết =" + str(float(dealSize)*float(deal_price))
                        
                    except:
                        result= "LỖI REQUEST HỦY LỆNH! Vào Hủy tay Nhận "+ str(dealSize) + "Hết =" + str(float(dealSize)*float(deal_price))
                        break
            else:
                result = "MUA thành công. Nhận " + str(dealSize) + "Hết =" +  str(float(dealSize)*float(deal_price))
                break
            time.sleep(1)
        return result

    # Hàm bán token theo limit
    def real_sell_in_bitmart(self, token_name, token_usd, amounin, amoutoutmin, proxy, fake_ip, truotgiasan):
        symbol = token_name + '_' + token_usd

        price, quantity = self.find_quantity_price_sell_bitmart(symbol=token_name, amountin=amounin, token_usd=token_usd, proxy=proxy, fake_ip=fake_ip, truotgiasan=truotgiasan)
        print("price", price)
        if quantity == 0:
            print("Do trượt giá của sàn quá cao")
            return "ERR Do trượt giá của sàn quá cao"
        if quantity == "ERR":
            print("Lỗi request depth")
            return "Lỗi request depth"            
        if quantity < amoutoutmin:
            print("real_sell_in_bitmart quantity" + str(quantity) + " < amoutoutmin" + str(amoutoutmin))
            return "ERR Bé hơn amoutoutmin rồi!!!"

        step_price, step_size = self.get_stepprice_size(token_name.upper())
        print("step_price", step_price)
        print("step_size", step_size)
        if float(step_size) >= 1:
            #quantity =  int(quantity*(int(mu)))/(int(mu))
            Klin = int(amounin)
            print("quantity 1", Klin)
        else:
            if float(step_size) <= 0.00001:
                mu =  int(1/ float(step_size)) + 1  # Do lúc này chia ra chỉ được 99999.99999999999
            else:
                mu =  int(1/ float(step_size))
            print("real_sell_in_bitmart mu", mu)
            #quantity =  int(quantity/float(get_stepprice))*(float(get_stepprice))
            Klin =  int(amounin*(int(mu)))/(int(mu))
            print("real_sell_in_bitmart quantity 1", Klin)


        print("price", price)
        print("khối lượng vào", Klin)
        try:
            result = self.TradeAPI.place_order(type_='limit', symbol=symbol, price=price, side="sell", size=Klin)
        except:
            print("Lỗi ", sys.exc_info())
            return "ERR " +str(sys.exc_info())

        if result['code'] == 1000:
            order_id = result['data']['order_id']
            print("Đã đặt lệnh thành công")
        else:
            print("Lỗi rồi.....", result)
            return "ERR "+ str(result)

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
                    try:
                        print("Lệnh sell đang còn mở")
                        result = self.TradeAPI.cancel_order(order_id)
                        print("result_cancel_buy", result)
                        if result['code'] == 1000:
                            print("ĐÃ HỦY LỆNH THÀNH CÔNG!!!")
                            if deal_price == '0':
                                result = "KHÔNG BÁN ĐƯỢC__ĐÃ HỦY LỆNH THÀNH CÔNG!!!" + str(dealSize) + "Nhận được =" + str(float(dealSize)*float(deal_price))
                            else:
                                result = "Bán 1 Phần.ĐÃ HỦY LỆNH " + str(dealSize) + "Nhận được =" + str(float(dealSize)*float(deal_price))
                        else:
                            result = "HỦY LỆNH THẤT BẠI!!! Vào Hủy tay" + str(dealSize) + "Nhận được =" + str(float(dealSize)*float(deal_price))
                    except:
                        result= "LỖI Request hủy lệnh! Vào Hủy tay"+ str(dealSize) + "Nhận được =" + str(float(dealSize)*float(deal_price))
                    break
            else:
                result = f"THÀNH CÔNG. BÁN {Klin} {token_name} Nhận được {str(float(dealSize)*float(deal_price))} "
                break
            time.sleep(1)
        return result

    '''
    def get_chain_token(self, aset, proxy="", fake_ip=False):
        nonce = str(int(time.time() * 1000))
        res = self.FundingAPI.get_deposit_method_token(nonce=nonce, token=aset, proxy=proxy, fake_ip=fake_ip)
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
    '''

    # Lấy địa chỉ nạp tiền lên bitmart
    def get_deposit_address_bitmart(self, currency, chain):
        currency = currency.upper()
        if chain=="Polygon":
            chainID=['MATIC', 'POLYGON']
        elif chain=="OPT":
            chainID=['OPTIMISM', 'OPT']
        elif chain=="BSC":
            chainID=['BEP20', 'BSC']
        elif chain=="TRON":
            chainID=['TRX', 'TRC20']              
        elif chain=="AVAX":
            chainID=['AVAX', 'AVAX-C']  
        elif chain=="ETH":
            chainID=['ERC20', 'ERC-20', 'ERC20\XA0', 'ETH20' ]
        elif chain=="FTM":
            chainID=['FTM', 'FANTOM']       
        elif chain=="SOL":
            chainID=['SOL', 'SOLANA' ]
        elif chain=="KLAY":
            chainID=['KLAYTN','KLAY']
        elif chain=="ARB":
            chainID=['ARB', 'ARBITRUM', 'ARBI']   
        elif chain=="APT":
            chainID=['APT']                                          
        else:
            chainID = [chain.upper]
        print("chainID", chainID)
        #token = currency + '-' + chainID
        #print("token", token)
        #token= 'SHINJA'
        all_token = self.list_all_token_bitmart
        for _token in all_token:
            if currency in _token['currency'] and _token['network'].upper() in chainID:
                token =  _token['currency']
                break

        try:
            res = self.FundingAPI.get_deposit_address(currency=token)
            print(f"res: {res['data']}")
            if res['code'] == 1000:
                address_bitmart= res['data']['address']
                print("address_bitmart", address_bitmart)
                add_memo=res['data']['address_memo']
                print("add_memo", add_memo)
                return address_bitmart, add_memo
            else:
                print( "Không có địa chỉ")
                return 0,0
        except:
            err = str(sys.exc_info())
            print("err", err)
            print("Kiểm tra lại Chain đi người đẹp!")
            return "Lỗi", "Lỗi"

    # Lấy trạng thái khả dụng hay bị dừng nạp tiền của 1 token
    def get_status_deposit_Bitmart(self, symbol, chain):
        token=symbol.upper()
        if chain=="Polygon":
            list_network=['MATIC', 'Polygon', 'POLYGON']
        elif chain=="OPT":
            list_network=['OPTIMISM']
        elif chain=="BSC":
            list_network=['BEP20', 'bep20']
        elif chain=="TRON":
            list_network=['TRX', 'TRC20','trc20']              
        elif chain=="AVAX":
            list_network=['AVAX', 'AVAX-C']  
        elif chain=="ETH":
            list_network=['ERC20', 'ERC-20', 'ERC20\xa0', 'ETH20' ]
        elif chain=="FTM":
            list_network=['Fantom', 'FANTOM']       
        elif chain=="SOL":
            list_network=['SOL', 'SOLANA' ]
        elif chain=="KLAY":
            list_network=['klaytn','Klaytn']
        elif chain=="ARB":
            list_network=['ARB', 'Arbitrum', 'ARBI']   
        elif chain=="APT":
            list_network=['APT']                                          
        else:
            print("Chain không khả dụng!!!!") 
        print("list_name_network", list_network)

        try:
            url="https://api-cloud.bitmart.com/account/v1/currencies"
            result=requests.get(url).json()['data']['currencies']
            #print("res", result)
            res = 'Lỗi trạng thái'
            for data in result:
                #print(data)
                #print(".....................")
                if  token in data['currency'] and data['network'] in list_network:
                    print("get_status_deposit_Bitmart", data)
                    if data['deposit_enabled'] == False:
                        print("Tạm dừng nạp tiền rồi ", token, chain)
                        return 0
                    else:
                        print("Nạp tiền bình thường !!!", token, chain) 
                        return 1
            return res
        except:
            print("lỗi request"+ str(sys.exc_info()))
            return "Lỗi"

    '''
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
    '''
    # Lấy trạng thái khả dụng hay bị dừng rút tiền
    def get_status_withdrawal_Bitmart(self, symbol, chain):
        token=symbol.upper()
        if chain=="Polygon":
            list_network=['MATIC', 'Polygon', 'POLYGON']
        elif chain=="OPT":
            list_network=['OPTIMISM']
        elif chain=="BSC":
            list_network=['BEP20', 'bep20']
        elif chain=="TRON":
            list_network=['TRX', 'TRC20','trc20']              
        elif chain=="AVAX":
            list_network=['AVAX', 'AVAX-C']  
        elif chain=="ETH":
            list_network=['ERC20', 'ERC-20', 'ERC20\xa0', 'ETH20' ]
        elif chain=="FTM":
            list_network=['Fantom', 'FANTOM']       
        elif chain=="SOL":
            list_network=['SOL', 'SOLANA' ]
        elif chain=="KLAY":
            list_network=['klaytn','Klaytn']
        elif chain=="ARB":
            list_network=['ARB', 'Arbitrum', 'ARBI']   
        elif chain=="APT":
            list_network=['APT']                                          
        else:
            print("Chain không khả dụng!!!!") 
        print("list_name_network", list_network)

        try:
            url="https://api-cloud.bitmart.com/account/v1/currencies"
            result=requests.get(url).json()['data']['currencies']
            #print("res", result)
            res = 'Lỗi'
            for data in result:
                #print(data)
                #print(".....................")
                if  token in data['currency'] and data['network'] in list_network:
                    print("get_status_withdrawal_Bitmart ", data)
                    if data['withdraw_enabled'] == False:
                        print("Tạm dừng rút tiền rồi ", token, chain)
                        return 0, 0, 0
                    else:
                        min_WD=data['withdraw_minsize']
                        min_feeWD= self.get_withdraw_fee(symbol, chain)
                        if min_feeWD == None:
                            min_feeWD = 0
                        #print("Rút tiền bình thường !!!", token, chain) 
                        return 1, min_WD, min_feeWD
            return res, 0, 0
        except:
            print("lỗi request"+str(sys.exc_info()))
            return "Lỗi", 0, 0      


    '''
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
    '''
    # Lấy lịch sử nạp tiền
    def get_deposit_history_bitmart(self, currency, id):
        sta = "Loi get_deposit_history_bitmart "
        try:
            res = self.FundingAPI.get_deposit_history(currency=currency, operation_type='deposit', N=100)
            print("res", res)
            if res['code'] == 1000:
                for res_dep in res['data']['records']:
                    if str(id).lower() in res_dep['tx_id'].lower():
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
                            print("Done " + str(currency))
                            sta = "Done " + str(currency)
                        elif status == 4:
                            print("Cancel " + str(currency))
                            sta = "Cancel " + str(currency)
                        elif status == 5:
                            print("Fail " + str(currency))
                            sta = "Fail " + str(currency)
                            break
                        return sta
                return sta
            else:
                print("Lỗi get status deposit Bitmart")
                return "Lỗi get status deposit Bitmart"
        except:
            return sta


    def get_withdraw_history_bitmart(self, wd_id):  # Lấy lịch sử rút tiền
        sta = "Loi get_withdraw_history_bitmart "
        try:
            res = self.FundingAPI.get_withdrawal_history(operation_type='withdraw', N=100)
            print("get_withdraw_history_bitmart ", res)
            if res['code'] == 1000:
                if res['data']['records'] == []:
                    return ["Không có giao dịch rút tiền gần đây!"]
            for res_wd in res['data']['records']:
                if str(wd_id).lower() in str(res_wd['withdraw_id']).lower():
                    state = res_wd['status']
                    #print("status", status)
                    if res_wd['status'] == 0:
                        sta = "Create"
                    elif res_wd['status'] == 1:
                        sta = "Submitted, waiting for withdrawal"
                    elif res_wd['status'] == 2:
                        sta = "Processing"
                    elif res_wd['status'] == 3:
                        sta = "Done"
                    elif res_wd['status'] == 4:
                        sta = "Cancel"
                    elif res_wd['status'] == 5:
                        sta = "Fail"
                    return sta
            return sta
        except:
            print("Lỗi request WD history Bitmart " + str(sys.exc_info()))
            sta = "Lỗi request WD history Bitmart"
        return sta

    # Hàm rút tiền từ bitmart về  ví metamask
    def submit_token_withdrawal_bitmart(self, symbol, chain, amount, address):
        #balance = self.get_balances_bitmart(symbol)
        #print("balance", balance)
        status = ''
        currency = symbol.upper()
        if chain=="Polygon":
            chainID=['MATIC', 'POLYGON']
        elif chain=="OPT":
            chainID=['OPTIMISM', 'OPT']
        elif chain=="BSC":
            chainID=['BEP20', 'BSC']
        elif chain=="TRON":
            chainID=['TRX', 'TRC20']              
        elif chain=="AVAX":
            chainID=['AVAX', 'AVAX-C']  
        elif chain=="ETH":
            chainID=['ERC20', 'ERC-20', 'ERC20\XA0', 'ETH20' ]
        elif chain=="FTM":
            chainID=['FTM', 'FANTOM']       
        elif chain=="SOL":
            chainID=['SOL', 'SOLANA' ]
        elif chain=="KLAY":
            chainID=['KLAYTN','KLAY']
        elif chain=="ARB":
            chainID=['ARB', 'ARBITRUM', 'ARBI']   
        elif chain=="APT":
            chainID=['APT']                                          
        else:
            chainID = [chain.upper]
        print("chainID", chainID)
        #token = currency + '-' + chainID
        #print("token", token)
        #token= 'SHINJA'
        all_token = self.list_all_token_bitmart
        for _token in all_token:
            if currency in _token['currency'] and _token['network'].upper() in chainID:
                token =  _token['currency']
                break

        try:
            print("size ", amount)
            destination="To Digital Address"
            res = self.FundingAPI.coin_withdraw(token, amount, destination, address)
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


    def get_all_token_in_bitmart(self):
        url = "https://api-cloud.bitmart.com/account/v1/currencies"
        result = requests.get(url=url, timeout=5)
        result= result.json()["data"]["currencies"]
        list_all_token = set()
        for re in result:
            #print(re)
            infor = f"{re['currency']}_{re['name']}_{re['network']}_{re['contract_address']}"
            #print(infor)
            list_all_token.add(infor)
        return list_all_token

    def all_token_in_bitmart(self):
        url = "https://api-cloud.bitmart.com/account/v1/currencies"
        result = requests.get(url=url, timeout=5)
        result= result.json()["data"]["currencies"]
        #for re in result:
            #print(re)
        return result        

    def get_withdraw_fee(self, tokename, chain):
        currency = tokename.upper()
        if chain=="Polygon":
            chainID=['MATIC', 'POLYGON']
        elif chain=="OPT":
            chainID=['OPTIMISM', 'OPT']
        elif chain=="BSC":
            chainID=['BEP20', 'BSC']
        elif chain=="TRON":
            chainID=['TRX', 'TRC20']              
        elif chain=="AVAX":
            chainID=['AVAX', 'AVAX-C']  
        elif chain=="ETH":
            chainID=['ERC20', 'ERC-20', 'ERC20\XA0', 'ETH20' ]
        elif chain=="FTM":
            chainID=['FTM', 'FANTOM']       
        elif chain=="SOL":
            chainID=['SOL', 'SOLANA' ]
        elif chain=="KLAY":
            chainID=['KLAYTN','KLAY']
        elif chain=="ARB":
            chainID=['ARB', 'ARBITRUM', 'ARBI']   
        elif chain=="APT":
            chainID=['APT']                                          
        else:
            chainID = [chain.upper]
        print("chainID", chainID)
        #token = currency + '-' + chainID
        #print("token", token)
        #token= 'SHINJA'
        all_token = self.list_all_token_bitmart
        for _token in all_token:
            if currency in _token['currency'] and _token['network'].upper() in chainID:
                token =  _token['currency']
                break
        try:
            print("token ", token)
            res = self.FundingAPI.get_withdrawal_fee(token)
            #print(res)
            fee_withdraw = res['data']['withdraw_fee']
            print("fee_withdraw ", fee_withdraw)
            return fee_withdraw
        except:
            return 0

    def get_currency(self, token_name, chain):
        currency = token_name.upper()
        if chain=="Polygon":
            chainID=['MATIC', 'POLYGON']
        elif chain=="OPT":
            chainID=['OPTIMISM', 'OPT']
        elif chain=="BSC":
            chainID=['BEP20', 'BSC']
        elif chain=="TRON":
            chainID=['TRX', 'TRC20']              
        elif chain=="AVAX":
            chainID=['AVAX', 'AVAX-C']  
        elif chain=="ETH":
            chainID=['ERC20', 'ERC-20', 'ERC20\XA0', 'ETH20' ]
        elif chain=="FTM":
            chainID=['FTM', 'FANTOM']       
        elif chain=="SOL":
            chainID=['SOL', 'SOLANA' ]
        elif chain=="KLAY":
            chainID=['KLAYTN','KLAY']
        elif chain=="ARB":
            chainID=['ARB', 'ARBITRUM', 'ARBI']   
        elif chain=="APT":
            chainID=['APT']                                          
        else:
            chainID = [chain.upper]
        #print("chainID", chainID)
        #token = currency + '-' + chainID
        #print("token", token)
        #token= 'SHINJA'
        all_token = self.list_all_token_bitmart
        token = "NOT FOUND"
        for _token in all_token:
            #{'currency': 'PAUL', 'name': 'Me Paul', 'contract_address': '0x4F1350CD63211515FAb6416d4743c7b99b1Bd1ac', 'network': 'ERC20', 'withdraw_enabled': True, 'deposit_enabled': True, 'withdraw_minsize': '14544', 'withdraw_minfee': '4'}
            if currency == _token['currency'] and _token['network'].upper() in chainID:
            #if currency in _token['currency'] :
                #print("_token ", _token)
                token =  _token['currency']
                return token
        return  token         

    def check_address_token_deposit_to_bitmart(self, tokenname, chain, address_token_sanco, infor_all_token):
        currency = self.get_currency( tokenname, chain)
        #print("currency ", currency, chain, address_token_sanco)
        if currency == "NOT FOUND":
            print("Không tìm thấy token ", tokenname, chain)
            return "NOT FOUND", tokenname, chain, "NOT FOUND"
        else:
            for token in infor_all_token:
                if currency == token['currency']:
                    #print(token)
                    contract_address = token['contract_address']
                    depositEnable= token['deposit_enabled']
                    withdrawEnable= token['withdraw_enabled'] 
                    if address_token_sanco.lower() in  ["0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE".lower(), "0x0000000000000000000000000000000000000000".lower(), 'wrap.near', "So11111111111111111111111111111111111111112".lower(), "TNUC9Qb1rRpS5CbWLmNMxXBjyFoydXjWFR".lower(), "EQCajaUU1XXSAjTD-xOV7pE49fGtg4q8kF3ELCOJtGvQFQ2C".lower(), 'uosmo', '0xe514d9deb7966c8be0ca922de8a064264ea6bcd4'.lower()]:
                        #print("Coin phí")
                        return True, 0, depositEnable, withdrawEnable


                    if address_token_sanco.lower()== contract_address.lower():
                        return True, 0, depositEnable, withdrawEnable
                    else:
                        return False , contract_address, depositEnable, withdrawEnable



#678af673-2264-43ed-b1e0-923a74e05430



toolbitmart = BITMART_FUNCTION()
#print(toolbitmart.get_depth_bitmart_web("BTC", "USDT", "http://azzz1688-rotate:123456700zzz@p.webshare.io:80", True))
#toolbitmart.get_currency("QANX", "BSC")
print(toolbitmart.all_token_in_bitmart())

#print(toolbitmart.check_address_token_deposit_to_bitmart(tokenname="PAUL", chain="ETH", address_token_sanco="0x4F1350CD63211515FAb6416d4743c7b99b1Bd1ac", infor_all_token= infor_all_token))


#print("111", toolbitmart.get_stepprice_size("BIBLE"))
#toolbitmart.real_buy_in_bitmart("BIBLE", "USDT", 10, 0, "", False, 5)

#toolbitmart.real_sell_in_bitmart("BIBLE", "USDT", 330420, 0, "", False, 5)

'''
import all_function_of_tooll_list_token

list_token = all_function_of_tooll_list_token.list_token_full

list_currency_dathem = set()
for token in list_token:
    if "BITMART" in token[1]:

        for chain in token[1]:
            if chain != "BITMART":
                chain_dex = chain
                break
        token_name =  token[0]['token_name'].split("_")[1]
        #if token_name == "GET":
        #print(token_name, chain_dex)
        #print("currency ", currency)
        currency= toolbitmart.get_currency(token_name, chain_dex)
        list_currency_dathem.add(currency)
        #print("currency ", currency)
        #print("---------------------")
list_network_sudung111 = ['MATIC', 'POLYGON', 'OPTIMISM', 'OPT', 'BEP20', 'BSC', 'TRX', 'TRC20', 'AVAX', 'AVAX-C','ERC20', 'ERC-20', 'ERC20\XA0', 'ETH20',  'FTM', 'FANTOM', 'KLAYTN','KLAY', 'ARB', 'ARBITRUM', 'ARBI', 'ZKS', "ETH",  "BSC", "BINA_ORDER", "MEXC", "OKX",  "KUCOIN", "HOUBI", "BYBIT", "BITGET","GATE", "LBANK", "BITMART", "KRAKEN", "TRON", "AVAX", "ARB", "Polygon", "FTM", "OPT", "SOL", "KLAY",  "KAVA", "OSMO", "JUNO", "NEAR",  "AURORA", "BEAM", "DFK",  "RSK", "ASTAR", "HECO", "OKT", "MOON", "CRO", "KCC",  "BNB", "APT", "BINA_FT", "RONIN", "FLUX", "KAVAEVM", "ZKS", "BTT", "PLS", "POLYEVM", "TON"]
list_network_sudung=['ETH20', 'IOTX', 'ERC20\xa0',  'APT', 'Fantom', 'SCRT',  'BSC_BNB',  'POLYGON', 'MATIC', 'CFX eSpace',  'ARB', 'CFX',  'NEAR', 'bep20', 'AVAX', 'klaytn',  'ERC20',  'GLMR', 'OK',  'CRO',  'ERC-20',  'TRC20', 'ATOM', 'AVAX-C', 'CRO_Chain', 'KAVA', 'FANTOM',  'HECO',  'Arbitrum',  'ARBI', 'ZKSYNCERA', 'BEP20', 'ASTAR',  'OSMO', 'SOLANA', 'SOL',  'OPTIMISM','Polygon', 'EVMOS']

#print(list_currency_dathem)
list_coin = toolbitmart.all_token_in_bitmart()
index= 0
list_network_bitmart = set()
for coin in list_coin:
    #list_network_bitmart.add(coin['network'])
    if coin['withdraw_enabled'] == False and coin['deposit_enabled'] == False:
        continue
    if coin['currency'] not in list_currency_dathem and coin['network'] in list_network_sudung:
        print(coin)
        index +=1
        print("-----------------------")

print("index ", index)


#print("list_currency_dathem ", len(list_currency_dathem))

#{'ETH20', 'IOTX', 'ERC20\xa0',  'APT', 'Fantom', 'SCRT',  'BSC_BNB',  'POLYGON', 'MATIC', 'CFX eSpace',  'ARB', 'CFX',  'NEAR', 'bep20', 'AVAX', 'klaytn',  'ERC20',  'GLMR', 'OK',  'CRO',  'ERC-20',  'TRC20', 'ATOM', 'AVAX-C', 'CRO_Chain', 'KAVA', 'FANTOM',  'HECO',  'Arbitrum',  'ARBI', 'ZKSYNCERA', 'BEP20', 'ASTAR',  'OSMO', 'SOLANA', 'SOL',  'OPTIMISM','Polygon', 'EVMOS'}

#print("list_network_bitmart ", list_network_bitmart)

#toolbitmart.get_withdraw_fee('USDT', "ETH")
#toolbitmart.get_deposit_history_bitmart("PTOY", "0x989c38b53bd987e4139e1ae67226ca73f0b4a38c97ca29ce552aa4731b173c09")

#toolbitmart.get_deposit_address_bitmart("SHINJA", 'ETH')
#print("111", toolbitmart.get_stepprice_size("ETH"))
#print(toolbitmart.get_chain_token("USDT", "", False))
#print("balancetr", toolbitmart.get_balances_bitmart("USDT"))
#print(toolbitmart.get_status_deposit_Bitmart("SHIBAI", "ARB"))
#print(toolbitmart.get_status_withdrawal_Bitmart("NIHAO", "ETH"))
#print(toolbitmart.get_depth_bitmart("BTC", "USDT"))
# print(f'=== {toolbitmart.get_return_buy_bitmart(symbol="BMX", usd="USDT", amountin=1, proxy="", fake_ip=False)}')
#print(toolbitmart.get_return_sell_bitmart("ETH", "USDT", 5, "", False))

# print(toolbitmart.find_quantity_price_buy_bitmart("ETH", 1, "USDT", "", "", 0.1))
# print(toolbitmart.find_quantity_price_sell_bitmart("ETH", 1, "USDT", "", "", 0.1))

#print(toolbitmart.real_buy_in_bitmart("CAKE", "USDT", 10, 0, "", "", 5))
#a= toolbitmart.get_balances_bitmart("CAKE")
#print("a", a)
#print(toolbitmart.real_sell_in_bitmart("CAKE", "USDT", float(a), 0, "proxy", False, 5))
#print("balancesau", toolbitmart.get_balances_bitmart("USDT"))
#print(toolbitmart.get_deposit_address_bitmart("USDT", "BSC"))  # no
# print(toolbitmart.get_status_deposit_bitmart("BTC")) # no
# print(toolbitmart.get_status_withdrawal_bitmart("FTM")) # no
# print(toolbitmart.get_deposit_history_bitmart("USDT", "1"))  # no
#print(toolbitmart.get_withdraw_history_bitmart("1"))  # no
# print(toolbitmart.get_balances_bitmart("ETH")) # no
#print(toolbitmart.submit_token_withdrawal_bitmart("USDT", "BSC", 20 ,"0xF43B3668cb00FdeB68467dd966AaF87c493d1a65")) # no    0x1EE6FA5A3803608fc22a1f3F76
# print(toolbitmart.submit_token_withdrawal_bitmart("USDT", 2.5, "USDT_ARB")) # no
'''