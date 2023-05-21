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
import time
import os
import requests
# import pandas as pd
import base64
import sys
import datetime
import urllib
import json
import requests
import time
import hashlib
import urllib3
import logging
import os
import kraken.Account_api as Account
import kraken.Funding_api as Funding
import kraken.Market_api as Market
import kraken.Public_api as Public
import kraken.Trade_api as Trade
import kraken.subAccount_api as SubAccount
import kraken.status_api as Status
import function_of_bina_SP
import logging
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
# from decouple import config
from decouple import config
from base64 import urlsafe_b64encode as b64e, urlsafe_b64decode as b64d
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from getpass import getpass
import secrets
scraper = cloudscraper.create_scraper()
path_file = os.path.dirname(os.path.abspath(__file__))

flag = '0'
backend = default_backend()
iterations = 100_000
class KRAKEN_FUNCTION:
    def __init__(self, keypass=None):
        #print("Init")
        if keypass != None:

            # NHẬP KEY, SECRET của API

            self.keypass = keypass
            list_infor_team= config('INFOR_TEAM')

            list_infor_team= list_infor_team.encode()
            list_infor_team = self.password_decrypt(list_infor_team, self.keypass).decode()

            self.list_infor_team= json.loads(list_infor_team)

            #print(list_infor_team)
            myteam = config('MY_TEAM')
            all_infor_of_team = self.list_infor_team['TEAM_'+ str(myteam)]
            #print("all_infor_of_team", all_infor_of_team)
            #self.opt_code = self.list_infor_team['TEAM_'+ str(myteam)]['pyotp_mexc']
    
            self.api_key = all_infor_of_team['APIKEY_kraken']  #
            self.api_secret  =  all_infor_of_team['SECRET_kraken'] #
 
            self.toolbina = function_of_bina_SP.FUNCTION_BINA()

            self.FundingAPI = Funding.FundingAPI(self.api_key, self.api_secret)
            self.TradeAPI = Trade.TradeAPI(self.api_key, self.api_secret)
            self.AccountAPI = Account.AccountAPI(self.api_key, self.api_secret)
            self.MarketAPI = Market.MarketAPI(self.api_key, self.api_secret)
            #print("Init Done")
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
        number = int(float(number)*(10**int(decimal_places))) / \
            (10**int(decimal_places))
        return number

    def get_balances_kraken(self, asset, proxy="", fake_ip= False):  # Check số dư của 1 token trên sàn
        if asset=="USD":
            token="ZUSD"
        else:
            token=asset.upper()

        try:
            nonce = str(int(time.time() * 1000))
            res = self.FundingAPI.get_balances(nonce, proxy, fake_ip )
            #print("res", res)
            try:
                balance = res['result'][token]
                #print("balance_kraken ", balance)
                time.sleep(2)
                return self.convert_number_to_smaller(float(balance))
            except:
                return 0            
        except:
            time.sleep(2)
            print("lỗi request balance_Kraken")
            return "x.x"
            

    def get_token(self):
        res=self.FundingAPI.get_currency()
        print("res", res)
    # Lấy danh sách các lệnh đang được đặt trên sàn
    def get_depth_kraken(self, symbol, usd, proxy, fake_ip):
        token = (symbol + usd).upper()
        url = "https://api.kraken.com/0/public/Depth?pair=" + token + "&count=500"
        token=(symbol+usd).upper()
        print("token", token)
        url =f'https://api.kraken.com/0/public/Depth?pair={token}&count=500'

        if fake_ip == True:
            #proxy= proxy
            #url= "https://api.myip.com/"
            proxies = {
                'http' : str(proxy),
                'https' : str(proxy) 
                }
            res = requests.get(url, proxies=proxies, timeout=5)  
        else:
            res = requests.get(url, timeout=5)
        result=res.json()
        #print("result", result['result'])
        return result['result']

    # Kiểm tra nếu dùng 1 số usd thì mua được bao nhiêu đồng coin
    def get_return_buy_kraken(self, symbol, usd, amountin, proxy, fake_ip):
        token=(symbol+usd).upper()
        print("token", token)
        result = self.get_depth_kraken(symbol, usd, proxy, fake_ip)
        #print("result1213",result )
        #print(result['data']['data']['asks'])
        #list_bids = result['bids']
        try:
            if "ETH" in symbol:
                list_asks = result["XETHZUSD"]['asks']  
            elif "BTC" in symbol:
                list_asks = result["XXBTZUSD"]['asks']              
            else:    
                list_asks = result[token]['asks']  
            #print("list_asks ", list_asks)
        except:
            print("Lỗi request"+str(sys.exc_info()))
            return 0
        #print(list_bids)
        #print("list_asks", list_asks)
        sum_value_ask = 0
        total_volume = 0 
        for ask in list_asks:
            #print(ask)
            sum_value_ask = sum_value_ask + float(ask[0])*float(ask[1])
            total_volume =  total_volume + float(ask[1])
            #print("sum_value_ask", sum_value_ask)
            #print("total_volume", total_volume)
            #print("------------")
            if float(sum_value_ask) >= float(amountin):
                ##print(ask)
                tien_con_thieu =  amountin- (sum_value_ask - float(ask[0])*float(ask[1]) )
                #print("tien_con_thieu ", tien_con_thieu)
                total_return = total_volume - float(ask[1]) + tien_con_thieu/float(ask[0])
                #print("total_return", total_return)
                return float(total_return)*(100-0.26)/100
        if  float(sum_value_ask)< float(amountin):
            #print("0 ",(total_volume)*(100-0.07)/100)
            #print("1",(sum_value_ask)*(100-0.2)/100)
            return (total_volume)*(100-0.26)/100
        #print("total_volume ", total_volume)

    # Kiểm tra nếu dùng 1 số coin thì bán ra được bao nhiêu đồng usd
    def get_return_sell_kraken(self, symbol, usd, amountin, proxy, fake_ip):
        token=(symbol+usd).upper()
        print("token", token)
        result = self.get_depth_kraken(symbol, usd, proxy, fake_ip)
        #print(result)
        ##print(result['bids'])
        try:
            if "ETH" in symbol:
                list_bids = result["XETHZUSD"]['bids']  
            elif "BTC" in symbol:
                list_bids = result["XXBTZUSD"]['bids']             
            else:    
                list_bids = result[token]['bids']
        except:
            print("Lỗi request"+str(sys.exc_info()))
            return 0
        #print("list_bids", list_bids)
        ##print(list_asks)
        sum_value_bids = 0
        total_volume = 0 
        for bid in list_bids:
            sum_value_bids = sum_value_bids + float(bid[0])*float(bid[1])
            total_volume =  total_volume + float(bid[1])
            #print("sum_value_bids", sum_value_bids)
            #print("total_volume", total_volume)
            #print("------------")
            if float(total_volume) >= float(amountin):
                ##print(bid)
                tien_con_thieu =  amountin- (total_volume - float(bid[1]) )
                #print("tien_con_thieu", tien_con_thieu)
                total_return = sum_value_bids - float(bid[0])*float(bid[1]) + tien_con_thieu*float(bid[0])
                #print("total_return", total_return)
                return float(total_return)*(100-0.26)/100
        if float(total_volume) < float(amountin):
            return float(sum_value_bids)*(100-0.26)/100 

    # Tìm giá khớp lệnh cuối cùng, và lượng token có thể nhận được khi mua
    def find_quantity_price_buy_kraken(self, symbol, amountin, token_usd, proxy, fake_ip, truotgiasan):
        token=(symbol+token_usd).upper()
        print("token", token)
        result = self.get_depth_kraken(symbol, token_usd, proxy, fake_ip)
        # print(result)
        try:
            if "ETH" in symbol:
                list_asks = result["XETHZUSD"]['asks']  
            elif "BTC" in symbol:
                list_asks = result["XXBTZUSD"]['asks']              
            else:    
                list_asks = result[token]['asks'] 
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
                tien_con_thieu = float(amountin) - (float(sum_value_ask) - float(ask[0])*float(ask[1]))
                print("tien_con_thieu", tien_con_thieu)
                total_return = float(total_volume) - float(ask[1]) + tien_con_thieu/float(ask[0])
                print("total_return", total_return)
                return price_find, total_return*(100-0.26)/100
        if float(price_find) > price_start*(1+float(truotgiasan)/100):
            print("SOS KRAKEN -buy " + str(symbol) + str(price_find)+" " + str(price_start))
            return 0, 0
        print("price OK KRAKEN price_start" + str(price_start) + "price_find " + (price_find))

        if float(sum_value_ask) < float(amountin):
            # 0.1 là phí giao dịch của KRAKEN
            return price_find, total_volume*(100-0.26)/100


    # Tìm giá khơp lệnh cuối cùng và số tiền nhận được khi bán token
    def find_quantity_price_sell_kraken(self, symbol, amountin, token_usd, proxy, fake_ip, truotgiasan):
        token=(symbol+token_usd).upper()
        print("token", token)
        result = self.get_depth_kraken(symbol, token_usd, proxy, fake_ip)
        # print(f"get_depth_kraken {result}")
        try:
            if "ETH" in symbol:
                list_bids = result["XETHZUSD"]['bids']  
            elif "BTC" in symbol:
                list_bids = result["XXBTZUSD"]['bids']             
            else:    
                list_bids = result[token]['bids']
        except:
            return 0
        sum_value_bids = 0
        total_volume = 0
        price_start = float(list_bids[0][0])

        for bid in list_bids:
            sum_value_bids = sum_value_bids + float(bid[0])*float(bid[1])  # tiền
            total_volume = total_volume + float(bid[1])  # khối lượng
            print("sum_value_bids", sum_value_bids)
            print("total_volume", total_volume)
            print("------------")
            price_find = bid[0]

            if float(total_volume) >= float(amountin):
                tien_con_thieu = amountin - (total_volume - float(bid[1]))
                print("tien_con_thieu", tien_con_thieu)
                total_return = sum_value_bids - float(bid[0])*float(bid[1]) + tien_con_thieu*float(bid[0])
                print("total_return", total_return)
                return price_find, total_return*(100-0.26)/100
            # print("price", price_find )
        if float(price_find) < price_start/(1+float(truotgiasan)/100):
            print("SOS " + str(price_find)+" " + str(price_start))
            return 10000000, 0
        print("price OK kraken" + str(price_start) + "price_find " + (price_find))

        if float(total_volume) < float(amountin):
            return price_find, sum_value_bids * (100-0.26)/100


    def get_return_buy_kraken_with_USDTETH(self, symbol, usd, amountin, proxy, fake_ip):
        result_sell_ETH = self.toolbina.get_return_sell_binance_order("ETHUSDT",amountin, proxy, fake_ip)
        #print("result_sell_ETH ", result_sell_ETH)
        result_buy_token = self.get_return_buy_kraken(symbol, 'USD', result_sell_ETH, proxy, fake_ip)
        #print("result_buy_token ", result_buy_token)
        return result_buy_token


    def get_return_sell_kraken_with_USDTETH(self, symbol, usd, amountin, proxy, fake_ip):
        result_sell_token = self.get_return_sell_kraken(symbol,'USD', amountin, proxy, fake_ip)
        print("result_sell_token ", result_sell_token)
        result = self.toolbina.get_return_buy_binance_order("ETHUSDT",result_sell_token, proxy, fake_ip)
        print("result ", result)
        return result

    def get_best_return_buy_kraken_withETH(self, symbol, amountin, proxy, fake_ip):
        executor = ThreadPoolExecutor(max_workers=2)
        #list_hop = ['ETH', 'USDTETH']
        list_hop = ['USDETH']
        res = []
        #f1 = executor.submit(self.get_return_buy_Okx, symbol, "ETH", amountin, proxy, fake_ip)  # Mua trực tiếp bằng ETH
        f2 = executor.submit(self.get_return_buy_kraken_with_USDTETH, symbol, "USD", amountin, proxy, fake_ip)  # USDT ->ETH ->token
        #f3 = executor.submit(self.get_return_buy_Okx_with_BTCETH, symbol, "BTC", amountin, proxy, fake_ip)  # USDT ->ETH ->token
        #res.append(f1.result())
        res.append(f2.result()) 
        #res.append(f3.result()) 
        print("res get_best_return_buy_kraken_withETH ", res)
        max_result_buy =  max(res)
        max_index_buy = res.index(max_result_buy)
        return max_result_buy, list_hop[max_index_buy]
    
    def get_best_return_sell_kraken_withETH(self, symbol, amountin, proxy, fake_ip):
        executor = ThreadPoolExecutor(max_workers=2)
        #list_hop = ['ETH', 'USDTETH']
        list_hop = ['USDETH']
        res = []
        #f1 = executor.submit(self.get_return_sell_Okx, symbol, "ETH", amountin, proxy, fake_ip)  # Mua trực tiếp bằng ETH
        f2 = executor.submit(self.get_return_sell_kraken_with_USDTETH, symbol, "USD", amountin, proxy, fake_ip)  # USDT ->ETH ->token
        #f3 = executor.submit(self.get_return_sell_Okx_with_BTCETH, symbol, "BTC", amountin, proxy, fake_ip)  # USDT ->ETH ->token
        #res.append(f1.result())
        res.append(f2.result()) 
        #res.append(f3.result()) 
        print("res get_best_return_sell_kraken_withETH ", res)
        max_result_sell =  max(res)
        max_index_sell = res.index(max_result_sell)
        return max_result_sell, list_hop[max_index_sell]

    def get_best_return_buy_Kraken(self, symbol, amountin, proxy, fake_ip):
        try:
            result = self.get_return_buy_kraken(symbol, "USD", amountin, proxy, fake_ip)
        except:
            #res.append(0)
            print("lỗi request" + str(sys.exc_info()))

        max_result_buy = float(result) #max(res)
        return max_result_buy


    def get_best_return_sell_Kraken(self,symbol, amountin, proxy, fake_ip):
        try:
            result = self.get_return_sell_kraken(symbol, "USD", amountin, proxy, fake_ip)
            #print("kq_buy", result)
            #res.append(float(result))
        except:
            #res.append(0)
            print("lỗi request" + str(sys.exc_info()))    
        max_result_sell = float(result) #max(res)
        return max_result_sell




    def get_stepsize(self, token):
        symbol=token.upper()+ "USD"
        print("symbol",symbol)
        resp = requests.get(f'https://api.kraken.com/0/public/AssetPairs?pair={symbol}') 
        res=resp.json()
        print("res", res)
        stepsize=res['result'][symbol]['tick_size']
        print("stepsie", stepsize)
        return stepsize

    

    # lệnh buy cần tính chuẩn với khối lượng 1000 usdt mua
    # Hàm mua theo limit
    def real_buy_in_kraken(self, token_name, token_usd, amounin, amoutoutmin, proxy, fake_ip, truotgiasan):
        symbol = (token_name + token_usd).upper()
        print("symbol", symbol)
        price, quantity = self.find_quantity_price_buy_kraken(
            symbol=token_name, amountin=amounin, token_usd=token_usd, proxy=proxy, fake_ip=fake_ip, truotgiasan=truotgiasan)
        print("price", price)
        print("quantity", quantity)
        if quantity == 0:
            print("Do truot gia cua san qua cao")
            return "ERR trượt giá sàn quá cao"
        if quantity < amoutoutmin:
            print("real_buy_in_kraken quantity" + str(quantity) +
                  " < amoutoutmin" + str(amoutoutmin))
            return "ERR Lỗi Bé hơn amoutoutmin rồi!!!"
        if "e" in str(price):
            price = f'{price:.20f}'
        else:
            price = price

        stepsize=self.get_stepsize(token_name) 
        print("stepsize", stepsize)   
        if float(stepsize) >= 1 or float(stepsize) == 0:
            #quantity =  int(quantity*(int(mu)))/(int(mu))
            quantity = int(quantity)
            print("quantity_1", quantity)
        else:
            if float(stepsize) <= 0.00001:
                mu =  int(1/ float(stepsize)) + 1  # Do lúc này chia ra chỉ được 99999.99999999999
            else:
                mu =  int(1/ float(stepsize))
            print("mu", mu)
            #quantity =  int(quantity/float(get_stepprice))*(float(get_stepprice))
            quantity =  int(quantity*(int(mu)))/(int(mu))
            print("quantity_2", quantity)

        Klin = quantity
        print("Klin ", Klin)
        print("price ", price)
        nonce = int(time.time() * 1000)
        try:
            result = self.TradeAPI.place_order(nonce=nonce, ordertype='limit', pair=symbol, price=price, type_='buy', volume=Klin)
            print("result", result)
        except:
            print("Lỗi request kraken", sys.exc_info())
            return "Lỗi request kraken" +  str(sys.exc_info())

        if len(result['error']) == 0:
            order_id = result['result']['txid'][0]
            print("Đã đặt lệnh thành công")
            print("order_id", order_id)
        else:
            print("Lỗi mua rồi.....", result)
            return 'MUA LỖI ' + str(result) 
        result = "ERR _ Đã đặt lệnh- check trạng thái lỗi ==> hủy tay đi"
        for i in range(4):
            nonce = int(time.time() * 1000)
            try:
                order_details = self.TradeAPI.get_orders(nonce, order_id)
                print("get_order_details ", order_details)
                deal_price = int(float(order_details['result'][order_id]['price'])*10**5)/(10**5) # Giá trung bình
                print("deal_price", deal_price)
                deal_amount = int(float(order_details['result'][order_id]['vol'])*10**5)/(10**5) # Số token nhận được
                print("deal_amount", deal_amount)
                deal_money = int((float(deal_amount)*float(deal_price))*10**3)/(10**3)
                print("deal_money", deal_money)
                status = order_details['result'][order_id]['status']
                print("status", status)                
            except:
                time.sleep(1)
                continue

            if 'open' in status or 'partial' in status:
                if i > 2:
                    print("Lệnh đang buy kraken còn mở")
                    try:
                        nonce = int(time.time() * 1000)
                        result = self.TradeAPI.cancel_order(nonce, order_id)
                        print("result_cancel_buy", result)
                        if result['result']['count'] == '1':
                            print("ĐÃ HỦY LỆNH THÀNH CÔNG!!!")
                            if deal_price == '0':
                                result = "KHÔNG MUA ĐƯỢC__ĐÃ HỦY LỆNH THÀNH CÔNG!!!Nhận "+ str(deal_amount) + "Hết =" + str(deal_money)
                            else:
                                print("1 Phần ĐÃ HỦY LỆNH. Nhận "+ str(deal_amount)  + "Hết =" + str(deal_money))
                                result = "1 Phần ĐÃ HỦY LỆNH. Nhận "+ str(deal_amount)  + "Hết =" + str(deal_money)
                        else:
                            print("HỦY LỆNH THẤT BẠI!!! Vào Hủy tay Nhận "+ str(deal_amount) + "Hết =" + str(deal_money))
                            result= "HỦY LỆNH THẤT BẠI!!! Vào Hủy tay Nhận "+ str(deal_amount) + "Hết =" + str(deal_money)
                    except:
                        print("LỖI REQUEST HỦY LỆNH! Vào Hủy tay Nhận "+ str(deal_amount) + "Hết =" + str(deal_money))
                        result= "LỖI REQUEST HỦY LỆNH! Vào Hủy tay Nhận "+ str(deal_amount) + "Hết =" + str(deal_money)
                    break
            else:
                print("MUA thành công. Nhận "+ str(deal_amount) + "Hết =" + str(deal_money))
                result1 = "MUA thành công. Nhận "+ str(deal_amount) + "Hết =" + str(deal_money) 
                break
            time.sleep(1)
        return result

    # Hàm bán token theo limit
    def real_sell_in_kraken(self, token_name, token_usd, amounin, amoutoutmin, proxy, fake_ip, truotgiasan):
        symbol = (token_name + token_usd).upper()
        print("symbol", symbol)

        price, quantity = self.find_quantity_price_sell_kraken(symbol=token_name, amountin=amounin, token_usd=token_usd, proxy=proxy, fake_ip=fake_ip, truotgiasan=truotgiasan)
        if "e" in str(price):
            price = f'{price:.20f}'
        else:
            price = price
        print("price", price)
        print("quantity", quantity)
        if quantity == 0:
            print("Do truot gia cua san qua cao")
            return "ERR trượt giá sàn quá cao"
        if quantity < amoutoutmin:
            print("real_sell_in_kraken quantity" + str(quantity) +" < amoutoutmin" + str(amoutoutmin))
            return "ERR Lỗi Bé hơn amoutoutmin rồi!!!"

        stepsize=self.get_stepsize(token_name) 
        print("stepsize", stepsize)   
        if float(stepsize) >= 1 or float(stepsize) == 0:
            #quantity =  int(quantity*(int(mu)))/(int(mu))
            quantity = int(amounin)
            print("quantity_1", amounin)
        else:
            if float(stepsize) <= 0.00001:
                mu =  int(1/ float(stepsize)) + 1  # Do lúc này chia ra chỉ được 99999.99999999999
            else:
                mu =  int(1/ float(stepsize))
            print("mu", mu)
            #quantity =  int(quantity/float(get_stepprice))*(float(get_stepprice))
            quantity =  int(amounin*(int(mu)))/(int(mu))
            print("quantity_2", quantity)

        Klin = quantity
        print("khối lượng vào", Klin)
        try:
            nonce = int(time.time() * 1000)
            result = self.TradeAPI.place_order(nonce=nonce, ordertype='limit', pair=symbol, price=price, type_='sell', volume=Klin)
            print("result", result)
        except:
            print("Lỗi request kraken ", sys.exc_info())
            return "Lỗi request bán kraken" +  str(sys.exc_info())


        if len(result['error']) == 0:
            order_id = result['result']['txid'][0]
            print("Đã đặt lệnh thành công")
            print("order_id", order_id)
        else:
            print("Lỗi bán rồi.....", result)
            return 'Bán LỖI ' + str(result) 
        result = "ERR _ Đã đặt lệnh- check trạng thái lỗi ==> hủy tay đi"
        for i in range(4):
            nonce = int(time.time() * 1000)
            try:
                order_details = self.TradeAPI.get_orders(nonce, order_id)
                print("get_order_details ", order_details)
                deal_price = int(float(order_details['result'][order_id]['price'])*10**5)/(10**5) # Giá trung bình
                print("deal_price", deal_price)
                deal_amount = int(float(order_details['result'][order_id]['vol'])*10**5)/(10**5) # Số token nhận được
                print("deal_amount", deal_amount)
                deal_money = int((float(deal_amount)*float(deal_price))*10**3)/(10**3)
                print("deal_amount", deal_amount)
                status = order_details['result'][order_id]['status']
                print("status", status)
            except:
                time.sleep(1)
                continue
            if 'open' in status or 'partial' in status:
                if i > 2:
                    print("Lệnh sell đang còn mở")
                    try:
                        nonce = int(time.time() * 1000)
                        result = self.TradeAPI.cancel_order(nonce, order_id)
                        print("result_cancel_sell", result)
                        if result['result']['count'] == '1':
                            print("ĐÃ HỦY LỆNH THÀNH CÔNG!!!")
                            if deal_price == '0':
                                print("KHÔNG BÁN ĐƯỢC__ĐÃ HỦY LỆNH THÀNH CÔNG!!!Bán "+ str(deal_amount) + "Nhận được =" + str(deal_money))
                                result= "KHÔNG BÁN ĐƯỢC__ĐÃ HỦY LỆNH THÀNH CÔNG!!!Bán "+ str(deal_amount) + "Nhận được =" + str(deal_money)
                            else:
                                print("1 Phần ĐÃ HỦY LỆNH. Bán "+ str(deal_amount) + "Nhận được =" + str(deal_money))
                                result = "1 Phần ĐÃ HỦY LỆNH. Bán "+ str(deal_amount) + "Nhận được =" + str(deal_money)
                        else:
                            print("HỦY LỆNH THẤT BẠI!!! Vào Hủy tay Bán "+ str(deal_amount) + "Nhận được =" + str(deal_money))
                            result= "HỦY LỆNH THẤT BẠI!!! Vào Hủy tay Bán "+ str(deal_amount) + "Nhận được =" + str(deal_money)
                    except:
                        print("LỖI REQUEST HỦY LỆNH! Vào Hủy tay Bán "+ str(deal_amount) + "Nhận được =" + str(deal_money))
                        result= "LỖI REQUEST HỦY LỆNH! Vào Hủy tay Bán "+ str(deal_amount) + "Nhận được =" + str(deal_money)
                    break
            else:
                print("Bán thành công. Bán "+ str(deal_amount) + "Nhận được =" + str(deal_money))
                result = "Bán thành công. Bán "+ str(deal_amount) + "Nhận được =" + str(deal_money) 
                break
            time.sleep(1)
        return result

    # Lấy địa chỉ nạp tiền lên kraken
    def get_deposit_address_kraken(self, symbol, chain, proxy="",fake_ip=False):
        symbol = symbol.upper()
        list_chain= self.get_chain_token(symbol, proxy , fake_ip)
        print("list_chain", list_chain)

        if chain=="Polygon":
            chainID="Polygon"
        elif chain=="OPT":
            chainID= "Optimism"
        elif chain=="BSC":
            chainID="BEP"
        elif chain=="TRON":
            if "USD" not in symbol.upper():
                chainID="Tron"   
            else: 
                chainID="TRC20"            
        elif chain=="AVAX":
            chainID= "Avalanche C-Chain"  
        elif chain=="ETH":
            chainID="ERC20" 
        elif chain=="FTM":
            chainID="Fantom"        
        elif chain=="SOL":
            if "USD" not in symbol.upper():
                chainID="Solana"
            else:
                chainID="SPL"
        elif chain=="KLAY":
            chainID="Klaytn"   
        elif chain=="ARB":
            chainID="Arbitrum"                                     
        else:
            chainID=chain
        print("chainID", chainID)

        for chai in list_chain:
            if chainID in chai:
                chain_dung= chai
                print("chain_dung", chain_dung)
                break
            
        try:
            nonce1 = int(time.time() * 1000)
            res = self.FundingAPI.get_deposit_address(nonce=nonce1, asset=symbol, method=chain_dung, proxy= proxy , fake_ip=fake_ip )
            print(f"res: {res['result'][0]['address']}")
            if len(res['error']) == 0:
                add=res['result'][0]['address']
                print("add", add)
                status=res['result'][0]['expiretm']
                print("status", status)
                if status=='0':
                    print("Địa chỉ nạp bình thường")
                    sta="Địa chỉ nạp bình thường" + str(symbol) + str(chain)
                else:
                    print("Địa chỉ nạp hết hạn")
                    sta="Địa chỉ nạp hết hạn" + str(symbol) + str(chain)                        
                return add, sta
        except:
            err = str(sys.exc_info())
            print("Lỗi request deposit Kraken" +str(err))
            sta="Lỗi request deposit Kraken" + str(symbol) + str(chain) 
            return 0, sta


    def get_chain_token(self, aset, proxy="",fake_ip=False ):
        nonce = str(int(time.time() * 1000))
        res=self.FundingAPI.get_deposit_method_token(nonce=nonce, token=aset, proxy=proxy , fake_ip=fake_ip  )
        print("res", res)
        data=res['result']
        list_chain=[]
        for add in data:
            print(add)
            chain=add["method"]
            if chain not in list_chain:
                print("chain", chain)
                list_chain.append(chain)
                print("................")
        return list_chain

    # Lấy trạng thái khả dụng hay bị dừng nạp tiền của 1 token
    def get_status_deposit_withdraw_kraken(self, symbol, chain):
        symbol = symbol.upper()
        print("symbol",symbol )
        try:
            res = self.FundingAPI.get_currency()
            for data in res['result']:
                if symbol in data:
                    status=res['result'][data]['status']
                    print("status", status)
                    if status == 'deposit_only':
                        print("Tạm dừng rút tiền rồi.Token " + str(symbol) + "Mạng: " +str(chain))
                        sta="Tạm dừng rút tiền rồi.Token " + str(symbol) + "Mạng: " +str(chain)
                        return sta
                    elif status == 'withdrawal_only':
                        print("Tạm dừng nạp tiền rồi.Token " + str(symbol) + "Mạng: " +str(chain))
                        sta="Tạm dừng nạp tiền rồi.Token " + str(symbol) + "Mạng: " +str(chain)
                        return sta 
                    elif status == 'funding_temporarily_disabled':
                        print("Tạm dừng nạp, rút tiền rồi.Token " + str(symbol) + "Mạng: " +str(chain))
                        sta="Tạm dừng nạp, rút tiền rồi.Token " + str(symbol) + "Mạng: " +str(chain)
                        return sta                                           
                    else:
                        print("Nạp rút bình thường.Token " + str(symbol) + "Mạng: " +str(chain))
                        sta="Nạp rút bình thường.Token " + str(symbol) + "Mạng: " +str(chain)
                        return sta
        except:
            print("lỗi request kraken", sys.exc_info())
            sta="lỗi request kraken.Token " + str(symbol) + "Mạng: " +str(chain)
            return sta

    # Lấy trạng thái khả dụng hay bị dừng rút tiền

    def get_status_withdraw_cooki_kraken(self, token, chain):
        if chain=="Polygon":
            chainID="Polygon"
        elif chain=="OPT":
            chainID= "Optimism"
        elif chain=="BSC":
            chainID="BEP"
        elif chain=="TRON":
            if "USD" not in token.upper():
                chainID="Tron"   
            else: 
                chainID="TRC20"            
        elif chain=="AVAX":
            chainID= "Avalanche C-Chain"  
        elif chain=="ETH":
            chainID="Ethereum" 
        elif chain=="FTM":
            chainID="Fantom"        
        elif chain=="SOL":
            if "USD" not in token.upper():
                chainID="Solana"
            else:
                chainID="SPL"
        elif chain=="KLAY":
            chainID="Klaytn"   
        elif chain=="ARB":
            chainID="Arbitrum One"                                     
        else:
            chainID=chain
        print("chainID", chainID)

        f = open(path_file+"\\cookie_kraken.txt", "r")
        cookie = f.read()
        #print('cookie ',cookie)
        f.close()
        headers = {
            'authority': 'www.kraken.com',
            'accept': 'application/json',
            'accept-language': 'en-US,en;q=0.9,vi;q=0.8,zh-CN;q=0.7,zh;q=0.6',
            'cookie':cookie,
            'origin': 'https://pro.kraken.com',
            'referer': 'https://pro.kraken.com/',
            'sec-ch-ua': '^\\^Chromium^\\^;v=^\\^112^\\^, ^\\^Google',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '^\\^Windows^\\^',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36',
            'x-korigin': '6081',
        }
        try:
            response = requests.get(f'https://www.kraken.com/api/internal/withdrawals/methods/{token}', headers=headers)
            
            res=response.json()['result']
            #print("response", res)
            for dat in res:
                print("dat", dat)
                network=dat['withdrawal_network_info']['network']
                print("network", network)
                if chainID.lower() in network.lower():
                    status=dat['temp_disabled_public']
                    print("status", status)
                    if status:
                        print("Dừng rút tiền" +str(token)+ str(chain))
                    
                    fee_wd=dat['fee']
                    print("fee_wd", fee_wd)
                    min_wd=dat['min_amount']
                    print("min_wd", min_wd)
                    print("....................")
                    return status, fee_wd, min_wd
                    break
        except:
            print("Lỗi request cooki kraken" +str(sys.exc_info()))
            return "Lỗi", "x", "x"


    # Lấy lịch sử nạp tiền
    def get_deposit_history_kraken(self, asset, txt):

        nonce = int(time.time() * 1000)
        res = self.FundingAPI.get_deposit_history(nonce=nonce, asset=asset)
        print("res", res)
        #status = []
        if len(res['error']) == 0:
            for res_dep in res['result']:
                if str(txt).lower() in res_dep['txid'].lower():
                    status= res_dep['status']
                    print("status", status)
                    if status =="Pending":
                        print("Nạp chuẩn" + str(asset) )
                        sta="Nạp chuẩn.Token: " + str(asset) 
                    elif status =="Failure":
                        print("Nạp không đủ KL Min" + str(asset))
                        sta="Nạp không đủ KL Min.Token: " + str(asset)
                    elif status == "Success":
                        print("Tiền đã vào tài khoản" + str(asset) )
                        sta="Tiền đã vào tài khoản.Token: " + str(asset)
                        break
                return sta
        else:
            print("Lỗi get status deposit Kraken")
            return "Lỗi get status deposit Kraken"

    def get_withdraw_history_kraken(self, wd_id):  # Lấy lịch sử rút tiền
        
        try:
            nonce = int(time.time() * 1000)
            res = self.FundingAPI.get_withdrawal_history(nonce=nonce)
            if len(res['result']) == 0:
                return ["Không có giao dịch rút tiền gần đây!"]
            for res_wd in res['result']:

                if str(wd_id).lower() in str(res_wd['refid']).lower():
                    status=res_wd['status']
                    print("status", status)
                    if res_wd['status'] == 'canceled':
                        sta="Lệnh rút tiền đã hủy!"
                    elif res_wd['status'] == 'Pending':
                        sta="Lệnh rút tiền đang sử lý!"
                    elif res_wd['status'] == 'Success':
                        sta="Rút tiền thành công chờ tiền về ví!"
        except:
            print("Lỗi request WD history Kraken " + str(sys.exc_info()))
            sta="Lỗi request WD history Kraken"
        return sta

    # Hàm rút tiền từ kraken về  ví metamask
    def submit_token_withdrawal_kraken(self, asset, amount, chain, proxy="",fake_ip=False ):
        balance = self.get_balances_kraken(asset, proxy , fake_ip)
        print("balance", balance)
        symbol=asset.upper()
        key=symbol+"_"+chain
        print("key", key)      
        #status, fee_wd, min_wd=self.get_status_withdraw_cooki_kraken(asset, chain)
        #print("fee_WD",fee_wd )
        if float(balance) > 0 and float(balance) >= float(amount):
            try:
                print("size ", amount)
                nonce = int(time.time() * 1000)
                res = self.FundingAPI.coin_withdraw(nonce, symbol, key, amount, proxy , fake_ip)
                print("Bắt đầu rút tiền ", res)
                if len(res['error']) == 0:
                    withdrawal_ID = res['result']['refid']
                    print("withdrawal_ID", withdrawal_ID)
                    print("Đã rút tiền chờ tiền về tài khoản!")
                    status = "Đã rút tiền chờ tiền về tài khoản!"
                    return True, status, withdrawal_ID
                else:
                    print("Rút tiền thất bại! " + str(res['error']))
                    status = res['error']
                    return False, status, 0
            except:
                err = str(sys.exc_info())
                print("Lỗi request withdrawal_kraken ", err)
                #continue
                status = err
                return 'False1', status, 0
        else:
            print("Không đủ tiền để rút rồi người đẹp!")
            status = "Không đủ tiền rút rồi!!!"
            return 'False2', status, 0


    def get_status_withdrawal_kraken(self, symbol, chain, amount):      
        symbol=symbol.upper()
        print("symbol",symbol) 
        key=symbol+"_"+chain
        print("key", key)          
        try:
            nonce = int(time.time() * 1000)
            res = self.FundingAPI.get_withdrawal_info(nonce=nonce, asset=symbol, key=key, amount=amount)
            print("res", res)

            if len(res['error']) == 0:
                print("Mạng rút bình thường!!!"+ str(symbol)+ "mạng :" + str(chain))
                max_WD = res['result']['limit']
                print("max_WD", max_WD)
                fee_WD = res['result']['fee']
                print("fee_WD", fee_WD)
                return fee_WD, max_WD
            else:
                print("Tạm dừng rút tiền rồi "+ str(symbol)+ "mạng :" + str(chain))
                return 'x', 'x'
        except:
            print("Lỗi request WD_kraken" + str(sys.exc_info()))
            return 'x1', 'x1'
       



#toolkraken = KRAKEN_FUNCTION(keypass='')
#print(toolkraken.get_stepsize("FTM"))
#print(toolkraken.get_status_withdrawal_kraken("USDT", "Arbitrum One Network", 1))
#print("balance", toolkraken.get_balances_kraken("USD"))
#print("white_list", toolkraken.set_add_whitelist_kraken("1INCH", "ETH", "0xF43B3668cb00FdeB68467dd966AaF87c493d1a65"))
# print(f'=== 1 ETH buy {toolkraken.get_return_buy_kraken(symbol="USD", usd="ETH", amountin=1, proxy="", fake_ip=False)} USD')
# print(f'=== 1 LTC sell {toolkraken.get_return_sell_kraken(symbol="LTC", usd="USDT", amountin=1, proxy="", fake_ip=False)} USDT')
#print("1111",toolkraken.get_chain_token("USDT") )
#print(toolkraken.find_quantity_price_buy_kraken("ETH", 1000, "USD", "", "", 0.1))
# print(toolkraken.find_quantity_price_sell_kraken("ETH", 1, "USDT", "", "", 0.1))

#print(toolkraken.get_depth_kraken("ETH", "USD", "", ""))
#print(toolkraken.real_buy_in_kraken("FTM", "USD", 5, 0, "", False, 5))

#a= toolkraken.get_balances_kraken("FTM")
#print(toolkraken.real_sell_in_kraken("FTM", "USD", a, 0, "proxy", False, 5))

#print(toolkraken.get_token())
#print(toolkraken.get_deposit_address_kraken("USDT", "SOL"))
#print(toolkraken.get_status_deposit_withdraw_kraken("USDT", "ETH"))
# print(toolkraken.get_status_withdrawal_kraken("FTM", "metamaskARB", 2))
#print(toolkraken.get_deposit_history_kraken("USDT", "TRON", "73cafdcba3fe70d9408b926c6a179b177f438dc2a13f2a077f110fc132c732db"))
# print(toolkraken.get_withdraw_history_kraken())
# print(toolkraken.transfer_kraken("USDT", "5", "Spot Wallet", "Futures Wallet"))

# print(toolkraken.submit_token_withdrawal_kraken("FTM", 1, "metamaskARB"))
#print(toolkraken.submit_token_withdrawal_kraken("USDT", 2, "Usdt_Polygon"))


#https://www.kraken.com/api/internal/withdrawals/methods/USDT?


#print(get_status_withdrawal_kraken("USDT", "ETH"))



