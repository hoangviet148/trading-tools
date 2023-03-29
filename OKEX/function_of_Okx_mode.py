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
import okex.Account_api as Account
import okex.Funding_api as Funding
import okex.Market_api as Market
import okex.Public_api as Public
import okex.Trade_api as Trade
import okex.subAccount_api as SubAccount
import okex.status_api as Status
import logging
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from decouple import config

scraper = cloudscraper.create_scraper()
path_file = os.path.dirname(os.path.abspath(__file__))


ROOT_URL = 'https://www.okx.com/'

flag = '0'

class OKX_FUNCTION:
    def __init__(self, keypass=None) :
        print("Init!")
        if keypass != None:

            # NHẬP KEY, SECRET của API
            self.api_key = '0f97363c-5a0f-451a-9472-85ec07dabeca'  
            self.api_secret = '3F66A0EF19036A4F0D136064CC4CDD2F'
            self.api_passphrase = 'gZ6^LRMK1JaA'

            self.FundingAPI= Funding.FundingAPI(self.api_key, self.api_secret, self.api_passphrase,False, flag)
            self.TradeAPI= Trade.TradeAPI(self.api_key, self.api_secret, self.api_passphrase, False, flag)
            self.AccountAPI= Account.AccountAPI(self.api_key, self.api_secret, self.api_passphrase,False, flag)
            self.MarketAPI= Market.MarketAPI(self.api_key, self.api_secret, self.api_passphrase, False, flag)


    #print("klines", klines)

    def get_stepprice_Okx(self, symbol): # Hàm này để tìm bước nhảy giá thấp nhất ví dụ giá 1.0001 thì stepprice là 0.0001
        token=symbol.upper()
        #print("token", token)
        res = self.FundingAPI.get_currency()
        result=res['data']
        for data in result:
            if  token in data['ccy']:
                step_price=data['wdTickSz']
                break
        return step_price    


    def get_decimal_token_cefi(self,number):  # Tìm xem 1 số có bao nhiêu số sau dấu phẩy
        string_number = str(number)
        if "." in string_number:
            decimal_places = len(string_number) - string_number.index('.') - 1
            #print(decimal_places)
        else:
            decimal_places=0
            #print(decimal_places)
        return decimal_places

    def convert_number_to_smaller(self, number):   # Chuyển 1 số thành dạng tối đa có 3 số sau dấu phẩy
        decimal_places = self.get_decimal_token_cefi(number)
        if decimal_places == 0:
            return number
        if decimal_places > 3:
            decimal_places = 3
        number = int(float(number)*(10**int(decimal_places)))/(10**int(decimal_places))
        return number


    def get_depth_Okx(self, symbol, usd, proxy, fake_ip):  # Lấy danh sách các lệnh đang được đặt trên sàn 
        token=(symbol+"-"+ usd).upper()
        url ="https://www.okx.com/api/v5/market/books?instId="+ token+"&sz=200"
        try:
            if fake_ip == True:
                proxies = {
                    'http' : str(proxy),
                    'https' : str(proxy) 
                    }
                res = requests.get(url, proxies=proxies, timeout=5)  
            else:
                res = requests.get(url, timeout=5)
            result=res.json()
            #print("result", result)
            #print(result['tick'])
            if result['data'] == False:
                return 0
            else:
                return result['data'][0]  
        except:
            return 0
    #print("dept", get_depth_Okx("BTC", "USDT", "aaaa", False))


    def get_return_buy_Okx(self, symbol, usd, amountin, proxy, fake_ip):  # Kiểm tra nếu dùng 1 số usd thì mua được bao nhiêu đồng coin
        result = self.get_depth_Okx(symbol, usd, proxy, fake_ip)
        try:
            list_asks = result['asks']
            #print("list_asks ", list_asks)
        except:
            return 0
        sum_value_ask = 0
        total_volume = 0 
        for ask in list_asks:
            #print(ask)
            sum_value_ask = sum_value_ask + float(ask[0])*float(ask[1])
            total_volume =  total_volume + float(ask[1])
            if float(sum_value_ask) >= float(amountin):
                ##print(ask)
                tien_con_thieu =  amountin- (sum_value_ask - float(ask[0])*float(ask[1]) )
                #print("tien_con_thieu ", tien_con_thieu)
                total_return = total_volume - float(ask[1]) + tien_con_thieu/float(ask[0])
                #print("total_return", total_return)
                return float(total_return)*(100-0.1)/100
        if  float(sum_value_ask)< float(amountin):
            return (total_volume)*(100-0.1)/100

    #print("buy", get_return_buy_Okx("ETH","USDT", 1000, "aaaa", False))

    def get_return_sell_Okx(self, symbol, usd, amountin, proxy, fake_ip): # Kiểm tra nếu dùng 1 số coin thì bán ra được bao nhiêu đồng usd
        result = self.get_depth_Okx(symbol, usd, proxy, fake_ip)
        try:
            list_bids = result['bids']
        except:
            return 0
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
                return float(total_return)*(100-0.1)/100
        if float(total_volume) < float(amountin):
            return float(sum_value_bids)*(100-0.1)/100 

    #print("sell", get_return_sell_Okx("ETH","USDT", 1, "aaaa", False))

    def get_return_buy_Okx_withETH(self, symbol, usd, amountin, proxy, fake_ip):   # Tuyến đường mua sẽ là ETH --> USDT --> Token
        result_sell_ETH = self.get_return_sell_Okx('ETH', 'USDT', amountin, proxy, fake_ip)
        #print("result_sell_ETH ", result_sell_ETH)
        result_buy_token = self.get_return_buy_Okx(symbol, 'USDT', result_sell_ETH, proxy, fake_ip)
        #print("result_buy_token ", result_buy_token)
        return result_buy_token


    def get_return_sell_Okx_withETH(self, symbol, usd, amountin, proxy, fake_ip): # Tuyến đường bán sẽ là Token --> USDT --> ETH
        result_sell_token = self.get_return_sell_Okx(symbol, 'USDT', amountin, proxy, fake_ip)
        print("result_sell_token ", result_sell_token)
        result = self.get_return_buy_Okx('ETH', 'USDT', result_sell_token, proxy, fake_ip)
        print("result ", result)
        return result


    def get_best_return_buy_Okx(self, symbol, amountin, proxy, fake_ip):  # Hàm này để so sánh xem mua bằng usdt hay usdc được lợi hơn 
        #symbol==symbol.upper()
        #list_usd = ['USDT','USDC']
        #res = []
        #for i in range(len(list_usd)):
        try:
            result = self.get_return_buy_Okx(symbol, "USDT", amountin, proxy, fake_ip)
            #print("kq_buy", result)
            #res.append(float(result))
        except:
            #res.append(0)
            print("Lỗi request!!!")
            #continue    
        max_result_buy = float(result) #max(res)

        return max_result_buy, "USDT"


    def get_best_return_buy_Okx_withETH(self, symbol, amountin, proxy, fake_ip):  # Hàm này để xem mua bằng ETH -->Token hay ETH --> USDT --> Token được lợi hơn 
        executor = ThreadPoolExecutor(max_workers=2)
        list_hop = ['ETH', 'USDTETH']
        res = []
        f1 = executor.submit(self.get_return_buy_Okx, symbol, "ETH", amountin, proxy, fake_ip)  # Mua trực tiếp bằng ETH
        f2 = executor.submit(self.get_return_buy_Okx_withETH, symbol, "USDT", amountin, proxy, fake_ip)  # USDT ->ETH ->token

        res.append(f1.result())
        res.append(f2.result())  

        max_result_buy =  max(res)
        max_index_buy = res.index(max_result_buy)

        return max_result_buy, list_hop[max_index_buy]


    def get_best_return_sell_Okx(self, symbol, amountin, proxy, fake_ip):  # Hàm này so sánh xem bán token --> USDT hay USDC được lợi hơn 
        #symbol==symbol.upper()
        #list_usd = ['USDT','USDC']
        #res = []
        #for i in range(len(list_usd)):
        try:
            result = self.get_return_sell_Okx(symbol, "USDT", amountin, proxy, fake_ip)
            #print("kq_sell", result)
            #res.append(float(result))
        except:
            #res.append(0)
            print("Lỗi request")
            #continue

        max_result_sell = float(result) 

        return max_result_sell, "USDT"


    def get_best_return_sell_Okx_withETH(self, symbol, amountin, proxy, fake_ip):  # Hàm này để xem bán token--> ETH  hay Token -->USDT --> ETH   được lợi hơn 
        executor = ThreadPoolExecutor(max_workers=2)
        list_hop = ['ETH', 'USDTETH']
        res = []
        f1 = executor.submit(self.get_return_sell_Okx, symbol, "ETH", amountin, proxy, fake_ip)  # Mua trực tiếp bằng ETH
        f2 = executor.submit(self.get_return_sell_Okx_withETH, symbol, "USDT", amountin, proxy, fake_ip)  # USDT ->ETH ->token

        res.append(f1.result())
        res.append(f2.result())  
        print("res get_best_return_sell_Okx_withETH ", res)
        max_result_sell =  max(res)
        max_index_sell = res.index(max_result_sell)

        return max_result_sell, list_hop[max_index_sell]


    def find_quantity_price_buy_Okx(self, symbol, amountin, token_usd, proxy, fake_ip, truotgiasan):  #Tìm giá khớp lệnh cuối cùng, và lượng token có thể nhận được khi mua
        result = self.get_depth_Okx(symbol, token_usd, proxy, fake_ip)
        #print(result)
        try:
            list_asks = result['asks']
        except:
            return 0
        ##print(list_bids)
        #print(list_asks)
        sum_value_ask = 0
        total_volume = 0 
        price_start= float(list_asks[0][0])
        for ask in list_asks:
            sum_value_ask = sum_value_ask + float(ask[0])*float(ask[1])
            total_volume =  total_volume + float(ask[1])
            print("sum_value_ask", sum_value_ask)
            print("total_volume", total_volume)
            print("------------")
            price_find =  float(ask[0])
            if float(sum_value_ask) >= float(amountin):
                ##print(ask)
                tien_con_thieu =  float(amountin)- (float(sum_value_ask) - float(ask[0])*float(ask[1]) )
                print("tien_con_thieu", tien_con_thieu)
                total_return = float(total_volume) - float(ask[1]) + tien_con_thieu/float(ask[0])
                print("total_return", total_return)
                return price_find, total_return*(100-0.1)/100
        if float(price_find) > price_start*(1+float(truotgiasan)/100):
            print("SOS OKX -buy "+ str(symbol) + str(price_find)+" "+ str(price_start))
            return 0, 0
        print("price OK OKX price_start"+ str(price_start) + "price_find "+ (price_find))

        if  float(sum_value_ask)< float(amountin):
            return price_find, total_volume*(100-0.1)/100  #0.1 là phí giao dịch của OKX

    

    def find_quantity_price_sell_Okx(self, symbol, amountin, token_usd, proxy, fake_ip, truotgiasan):  # Tìm giá khơp lệnh cuối cùng và số tiền nhận được khi bán token 
        result = self.get_depth_Okx(symbol,token_usd, proxy, fake_ip)
        try:
            list_bids = result['bids']
        except:
            return 0
        sum_value_bids = 0
        total_volume = 0 
        price_start= float(list_bids[0][0])    

        for bid in list_bids:
            sum_value_bids = sum_value_bids + float(bid[0])*float(bid[1]) #tiền
            total_volume = total_volume + float(bid[1])   #khối lượng
            print("sum_value_bids", sum_value_bids)
            print("total_volume", total_volume)
            print("------------")
            price_find = bid[0]
            
            if float(total_volume) >= float(amountin):
                tien_con_thieu =  amountin- (total_volume - float(bid[1]))
                print("tien_con_thieu", tien_con_thieu)
                total_return = sum_value_bids - float(bid[0])*float(bid[1]) + tien_con_thieu*float(bid[0])
                print("total_return", total_return)
                return price_find, total_return*(100-0.1)/100 
            #print("price", price_find ) 
        if float(price_find) < price_start/(1+float(truotgiasan)/100):
            print("SOS "+ str(price_find)+" "+ str(price_start))
            return 10000000, 0
        print("price OK OKX"+ str(price_start) + "price_find "+ (price_find))        

        if float(total_volume) < float(amountin):
            return price_find, sum_value_bids *(100-0.1)/100    
        

    def get_balances_Okx(self, symbol):  # Check số dư của 1 token trên sàn
        token=symbol.upper()
        while True:
            try:
                res= self.FundingAPI.get_balances(token) 
                #print("res", res)
                balance_funding=res['data'][0]['availBal']
                break
            except:
                time.sleep(1)
                continue
        while True:
            try:
                res1=self.AccountAPI.get_account(token)
                #print("res1", res1)
                balance_trading=res1['data'][0]['details']
                break
            except:
                time.sleep(1)
                continue

        if len(balance_trading) ==0:
            balance_trading=0
        else:
            balance_trading= balance_trading[0]['availBal']
        #print("balance_trading ", balance_trading)
        balance=float(balance_funding)+float(balance_trading)
        return self.convert_number_to_smaller(float(balance)), self.convert_number_to_smaller(float(balance_funding)), self.convert_number_to_smaller(float(balance_trading))


    #print(kucoin.get_balances(token_name="USD"))
    #lệnh buy cần tính chuẩn với khối lượng 1000 usdt mua
    def real_buy_in_Okx(self, token_name, token_usd, amounin, amoutoutmin, proxy, fake_ip, truotgiasan):  # Hàm mua theo limit 
        token_name=token_name.upper()
        token_usd=token_usd.upper()
        symbol = str(token_name)+ str(token_usd)
        symbol1 = str(token_name)+ "-"+ str(token_usd)
        symbol2= str(token_name)
        print("symbol", symbol)
        print("symbol1", symbol1)
        print("symbol2", symbol2)
        price , quantity= self.find_quantity_price_buy_Okx(symbol = symbol2 , amountin = amounin, token_usd= token_usd, proxy= proxy, fake_ip= fake_ip, truotgiasan=truotgiasan)
        print("price", price)
        print("quantity", quantity)
        if quantity == 0:
            print("Do truot gia cua san qua cao")
            return "Do truot gia cua san qua cao"
        if quantity<amoutoutmin:
            print("real_buy_in_OKx quantity" + str(quantity) + " < amoutoutmin" + str(amoutoutmin))
            return "Bé hơn amoutoutmin rồi!!!"
        if "e" in str(price):
            price = f'{price:.20f}' 
        else:
            price = price 
        Klin = int(quantity*10**4)/(10**4)
        print("Klin ", Klin)
        print("price ", price)
        try:
            result= self.TradeAPI.place_order(instId=symbol1, tdMode='cash',side= 'buy', ordType= 'limit', sz= Klin, px= price)
    
        except:
            print("Lỗi ", sys.exc_info())
        print("result", result)
        
        if result['data'][0]['sCode'] =='0':
            order_id = result['data'][0]['ordId']
            print("Đã đặt lệnh thành công")
        else:
            print("Lỗi rồi.....")

        print("order_id", order_id)
        for i in range(4):
            order_details = self.TradeAPI.get_orders(symbol1,order_id)
            print("get_order_details ", order_details)
            deal_price =  order_details['data'][0]['avgPx']
            print("deal_fund", deal_price)
            dealSize =  order_details['data'][0]['accFillSz']
            print("dealSize", dealSize)
            status=order_details['data'][0]['state'] 
            print("status", status)
            if 'live' in status  or 'partially_filled' in status:
                if i>2:
                    print("Lệnh đang buy market còn mở")
                    result = self.TradeAPI.cancel_order(symbol1,order_id)
                    print("result_cancel_buy",result)
                    if result['data'][0]['sCode'] == '0':
                        print("ĐÃ HỦY LỆNH THÀNH CÔNG!!!")
                        if deal_price == '0':
                            result= "KHÔNG MUA ĐƯỢC__ĐÃ HỦY LỆNH THÀNH CÔNG!!!"
                        else:
                            result = "1 Phần. Nhận "+ str(dealSize) + "Hết =" + str(float(dealSize)*float(deal_price)) + " ĐÃ HỦY LỆNH THÀNH CÔNG"
                    else:
                        result= "HỦY LỆNH THẤT BẠI!!! Vào Hủy tay đi chị đẹp"
                    break
            else:
                result = "MUA OK. Nhận "+ str(dealSize) + "Hết =" + str(float(dealSize)*float(deal_price))
                break
            time.sleep(1)
        return result

    def real_buy_market_in_Okx(self, token_name, token_usd, amounin, amoutoutmin, proxy, fake_ip, truotgiasan):  # Hàm mua theo market
        token_name=token_name.upper()
        token_usd=token_usd.upper()
        symbol = token_name+ token_usd
        symbol1 = token_name+ "-"+ token_usd
        symbol2= token_name

        price , quantity= self.find_quantity_price_buy_Okx(symbol = symbol2 , amountin = amounin, token_usd= token_usd, proxy= proxy, fake_ip= fake_ip, truotgiasan=truotgiasan)
        print("price", price)
        print("quantity", quantity)
        if quantity == 0:
            print("Do truot gia cua san qua cao")
            return "Do truot gia cua san qua cao"
        if quantity<amoutoutmin:
            print("real_buy_in_OKx quantity" + str(quantity) + " < amoutoutmin" + str(amoutoutmin))
            return "Bé hơn amoutoutmin rồi!!!"
        if "e" in str(price):
            price = f'{price:.20f}' 
        else:
            price = price      #1.336e-09

        Klin = int(quantity*10**4)/(10**4)
        print("Klin ", Klin)
        print("price ", price)
        try:
            result= self.TradeAPI.place_order(instId=symbol1, tdMode='cash',side= 'buy', ordType= 'market', sz= amounin)
    
        except:
            print("Lỗi buy market ", sys.exc_info())


        print("result buy market ", result)
        if result['data'][0]['sCode'] == '0':
            order_id = result['data'][0]['ordId']
            print("order_id sell market ", order_id)
            #amountout=result['size']/result['price']
            print("Đã đặt lệnh sell market thành công")
        else:
            print("Lỗi buy market rồi....."+ str(result))
            return "Lỗi buy market rồi....."+ str(result)

        print("order_id1 sell market ", order_id)

        for i in range(4):
            order_details = self.TradeAPI.get_orders(symbol1,order_id)
            print("get_order_details ", order_details)
        
            deal_price =  order_details['data'][0]['avgPx']
            print("deal_fund", deal_price)
            dealSize =  order_details['data'][0]['accFillSz']
            print("dealSize", dealSize)
            status=order_details['data'][0]['state'] 
            print("status", status)
            if 'live' in status  or 'partially_filled' in status:
                if i>2:
                    print("Lệnh đang buy market còn mở")
                    try:
                        result = self.TradeAPI.cancel_order(symbol1,order_id)
                        print("result_cancel_buy",result)
                        if result['data'][0]['sCode'] == '0':
                            print("ĐÃ HỦY LỆNH THÀNH CÔNG!!!")
                            if deal_price == '0':
                                result= "KHÔNG MUA ĐƯỢC__ĐÃ HỦY LỆNH THÀNH CÔNG!!!. ETH Nhận "+ str(dealSize) + "Hết =" + str(float(dealSize)*float(deal_price))
                            else:
                                result = "1 Phần. ĐÃ HỦY LỆNH. ETH Nhận "+ str(dealSize) + "Hết =" + str(float(dealSize)*float(deal_price))
                        else:
                            result= "HỦY LỆNH THẤT BẠI!!! Vào Hủy tay đi chị đẹp. ETH Nhận "+ str(dealSize) + "Hết =" + str(float(dealSize)*float(deal_price))
                    except:
                        result= "Lỗi request hủy lệnh!!! Vào Hủy tay đi chị đẹp. ETH Nhận "+ str(dealSize) + "Hết =" + str(float(dealSize)*float(deal_price))
                    break
            else:
                result = "MUA MARKET OK. ETH Nhận "+ str(dealSize) + "Hết =" + str(float(dealSize)*float(deal_price))
                break
            time.sleep(1)

        return result

    def real_buy_market_ETH(self, amounin, amoutoutmin, proxy, fake_ip, truotgiasan):  #Hàm mua ETH bằng USDT theo market
        tonggiatridakhop = 0
        tongethdamua = 0
        amountinfirst = amounin
        for i in range(4):
            result = self.real_buy_market_in_Okx("ETH", "USDT", amounin, amoutoutmin, proxy, fake_ip, truotgiasan)        
            if "MUA OK." in result:
                print("lệnh mua ETH theo market hoàn tất")
                return result
            else:

                amountin_dakhoplenh = float(result.split("Hết =")[1])
                amoutethnhanduoc = float(result.split("Hết =")[0].split("Nhận ")[1])
                tonggiatridakhop = tonggiatridakhop + amountin_dakhoplenh
                tongethdamua = tongethdamua + amoutethnhanduoc
                if tonggiatridakhop > float(amountinfirst)*0.998:
                    print("Đã khớp tương đối rồi")
                    return f"Đã Mua xong {i} lần. Nhận {tongethdamua} ETH Hết = {tonggiatridakhop}"
                amountin_chuakhoplenh = float(amounin) - amountin_dakhoplenh
                amounin = amountin_chuakhoplenh

        return f"Đã Mua xong {i} lần. Nhận {tongethdamua} ETH Hết = {tonggiatridakhop} $"



    def real_sell_in_Okx(self, token_name, token_usd, amounin, amoutoutmin, proxy, fake_ip, truotgiasan):  # Hàm bán token theo limit
        token_name=token_name.upper()
        token_usd=token_usd.upper()
        symbol = str(token_name)+ str(token_usd)
        symbol1 = str(token_name)+ str("-"+ token_usd+"")
        symbol2= str(token_name)

        price , quantity= self.find_quantity_price_sell_Okx( symbol = symbol2 , amountin = amounin, token_usd= token_usd, proxy= proxy, fake_ip= fake_ip , truotgiasan= truotgiasan)
        if "e" in str(price):
            price = f'{price:.20f}' 
        else:
            price = price  
        print("price", price)
        print("quantity", quantity)
        if quantity == 0:
            print("Do truot gia cua san qua cao")
            return "Do truot gia cua san qua cao"            
        if quantity<amoutoutmin:
            print("real_sell_in_OKx quantity" + str(quantity) + " < amoutoutmin" + str(amoutoutmin))
            return "Bé hơn amoutoutmin rồi!!!"

        Klin = int(amounin*10**4)/(10**4)
        print("khối lượng vào", Klin)
        try:
            result=  self.TradeAPI.place_order(instId=symbol1, tdMode='cash', side= 'sell', ordType= 'limit', sz= Klin, px= price)

        except:
            print("Lỗi ", sys.exc_info())
        print("result", result)

        
        if result['data'][0]['sCode'] == '0':
            order_id = result['data'][0]['ordId']
            print("order_id", order_id)
            print("Đã đặt lệnh thành công")
        else:
            print("Lỗi sell rồi.....")

        print("order_id1", order_id)
        for i in range(4):
            order_details = self.TradeAPI.get_orders(symbol1,order_id)
            print("get_order_details ", order_details)
            deal_price =  order_details['data'][0]['avgPx']
            print("deal_fund", deal_price)
            dealSize =  order_details['data'][0]['accFillSz']
            print("dealSize", dealSize)
            status=order_details['data'][0]['state'] 
            print("status", status)
            if 'live' in status  or 'partially_filled' in status:
                if i >2:
                    print("Lệnh sell đang còn mở")
                    result = self.TradeAPI.cancel_order(symbol1,order_id)
                    print("result_cancel_buy",result)
                    if result['data'][0]['sCode'] == '0':
                        print("ĐÃ HỦY LỆNH THÀNH CÔNG!!!")
                        if deal_price == '0':
                            result= "KHÔNG BÁN ĐƯỢC__ĐÃ HỦY LỆNH THÀNH CÔNG!!!"
                        else:
                            result = "Bán 1 Phần "+ str(dealSize) + "Nhận được =" + str(float(dealSize)*float(deal_price)) + " ĐÃ HỦY LỆNH THÀNH CÔNG"
                    else:
                        result= "HỦY LỆNH THẤT BẠI!!! Vào Hủy tay đi chị đẹp"
                    break
            else:
                result = f"THÀNH CÔNG. BÁN {Klin} {token_name} Nhận được {str(float(dealSize)*float(deal_price))} "
                break
            time.sleep(1)
        return result

    def real_sell_market_in_Okx(self, token_name, token_usd, amounin, amoutoutmin, proxy, fake_ip, truotgiasan):  # Hàm Bán token theo market
        token_name=token_name.upper()
        token_usd=token_usd.upper()
        symbol = token_name+ token_usd
        symbol1 = token_name+ "-"+ token_usd
        symbol2= token_name
        price , quantity= self.find_quantity_price_sell_Okx( symbol = symbol2 , amountin = amounin, token_usd= token_usd, proxy= proxy, fake_ip= fake_ip , truotgiasan= truotgiasan)

        print("quantity", quantity)
        if quantity == 0:
            print("Do truot gia cua san qua cao")
            return "Do truot gia cua san qua cao"            
        if quantity<amoutoutmin:
            print("real_sell_in_OKx quantity" + str(quantity) + " < amoutoutmin" + str(amoutoutmin))
            return "Bé hơn amoutoutmin rồi!!!"

        Klin = int(amounin*10**4)/(10**4)
        try:
            result=  self.TradeAPI.place_order(instId=symbol1, tdMode='cash', side= 'sell', ordType= 'market', sz= Klin)

        except:
            print("Lỗi real_sell_market_in_Okx", sys.exc_info()) 


        print("result sell market ", result)
        if result['data'][0]['sCode'] == '0':
            order_id = result['data'][0]['ordId']
            print("order_id sell market ", order_id)
            print("Đã đặt lệnh sell market thành công")
        else:
            print("Lỗi sell market rồi.....")

        print("order_id1 sell market ", order_id)

        for i in range(4):
            order_details = self.TradeAPI.get_orders(symbol1,order_id)
            print("get_order_details ", order_details)
            deal_price =  order_details['data'][0]['avgPx']
            print("deal_fund", deal_price)
            dealSize =  order_details['data'][0]['accFillSz']
            print("dealSize", dealSize)
            status=order_details['data'][0]['state'] 
            print("status", status)
            if 'live' in status  or 'partially_filled' in status:
                if i >2:
                    try:
                        print("Lệnh sell đang còn mở")
                        result = self.TradeAPI.cancel_order(symbol1,order_id)
                        print("result_cancel_buy",result)
                        if result['data'][0]['sCode'] == '0':
                            print("ĐÃ HỦY LỆNH THÀNH CÔNG!!!")
                            if deal_price == '0':
                                result= "KHÔNG BÁN ĐƯỢC__ĐÃ HỦY LỆNH THÀNH CÔNG!!! HẾT "+ str(dealSize) + "Nhận được =" + str(float(dealSize)*float(deal_price))
                            else:
                                result = "Bán 1 Phần ĐÃ HỦY LỆNH THÀNH CÔNG. HẾT "+ str(dealSize) + "Nhận được =" + str(float(dealSize)*float(deal_price))
                        else:
                            result= "HỦY LỆNH THẤT BẠI!!! Vào Hủy tay đi chị đẹp HẾT "+ str(dealSize) + "Nhận được =" + str(float(dealSize)*float(deal_price))
                    except:
                        result= "LỖI request hủy LỆNH! Vào Hủy tay đi chị đẹp HẾT "+ str(dealSize) + "Nhận được =" + str(float(dealSize)*float(deal_price))
                    break
            else:
                result = f"THÀNH CÔNG. BÁN {Klin} {token_name} Nhận được {str(float(dealSize)*float(deal_price))} "
                break
            time.sleep(1)
        return result



    def real_sell_market_ETH(self, amounin, amoutoutmin, proxy, fake_ip, truotgiasan):  # Hàm Bán ETH ra USDT theo market
        tonggiatridakhop = 0
        tongusdtnhanduoc = 0
        amountinfirst = amounin
        for i in range(4):
            result = self.real_sell_market_in_Okx( "ETH", "USDT", amounin, amoutoutmin, proxy, fake_ip, truotgiasan)        
            if "MUA OK." in result:
                print("lệnh bán ETH theo market hoàn tất")
                return result
            else:

                amountin_dakhoplenh = float(result.split("HẾT ")[1].split("Nhận được")[0])
                amout_usdt_nhanduoc = float(result.split("Nhận được =")[1])
                tonggiatridakhop = tonggiatridakhop + amountin_dakhoplenh
                tongusdtnhanduoc = tongusdtnhanduoc + amout_usdt_nhanduoc
                if tonggiatridakhop > float(amountinfirst)*0.998:
                    print("Đã khớp SELL tương đối rồi")
                    return f"Đã BÁN xong {i} lần. Nhận {amout_usdt_nhanduoc} USDT Hết = {tonggiatridakhop} ETH"
                amountin_chuakhoplenh = float(amounin) - amountin_dakhoplenh
                amounin = amountin_chuakhoplenh

        return f"Đã BÁN xong {i} lần. Nhận {amout_usdt_nhanduoc} USDT Hết = {tonggiatridakhop} ETH"




    def get_deposit_address_Okx(self, symbol, chain):  # Lấy địa chỉ nạp tiền lên OKX
        token=symbol.upper()
        if chain=="Polygon":
            chainID=token+"-"+ "Polygon"
        elif chain=="OPT":
            chainID= token+"-"+"Optimism"
        elif chain=="BSC":
            chainID=token+"-"+"BSC"
        elif chain=="TRON":
            chainID=token+"-"+"TRC20"               
        elif chain=="AVAX":
            chainID= token+"-"+"Avalanche C-Chain"  
        elif chain=="ETH":
            chainID=token+"-"+"ERC20" 
        elif chain=="FTM":
            chainID=token+"-"+"Fantom" 
        elif chain=="ASTAR":
            chainID=token+"-"+"Astar"         
        elif chain=="SOL":
            chainID=token+"-"+"Solana"
        elif chain=="MOON":
            chainID=token+"-"+"Moonriver"   
        elif chain=="NEAR":
            chainID=token+"-"+"NEAR"  
        elif chain=="KLAY":
            chainID=token+"-"+"Klaytn" 
        elif chain=="OSMO":
            chainID=token+"-"+"Cosmos"
        elif chain=="JUNO":
            chainID=token+"-"+"Cosmos"    
        elif chain=="ARB":
            chainID=token+"-"+"Arbitrum one"   
        elif chain=="BEAM":
            chainID=token+"-"+"Moonbeam"
        elif chain=="METIS":
            chainID=token+"-"+"Metis"
        elif chain=="APT":
            chainID=token+"-"+"Aptos"    
        elif chain=="OKT":
            chainID=token+"-"+"OKC" 
            if "ETH" in symbol:
               chainID="ETHK"+"-"+"OKC"  
            elif "BTC" in symbol:
               chainID="BTCK"+"-"+"OKC" 
            elif "DAI" in symbol:
               chainID="DAIK"+"-"+"OKC"                                             
        else:
            print("Chain không khả dụng!!!!") 

        try:
            res=  self.FundingAPI.get_deposit_address(token)
            for dat in res['data']:
                if dat['selected'] == True and chainID in dat['chain']:
                    add=dat['addr']
                    tag=dat['ctAddr']
                    return add, tag

        except:
            err = str(sys.exc_info())
            print("err", err)
            print("Kiểm tra lại Chain đi người đẹp!")
            return 0,0



    def get_status_deposit_Okx(self, symbol, chain):  #Lấy trạng thái khả dụng hay bị dừng nạp tiền của 1 token
        token=symbol.upper()
        if chain=="Polygon":
            chainID=token+"-"+ "Polygon"
        elif chain=="OPT":
            chainID= token+"-"+"Optimism"
        elif chain=="BSC":
            chainID=token+"-"+"BSC"
        elif chain=="TRON":
            chainID=token+"-"+"TRC20"               
        elif chain=="AVAX":
            chainID= token+"-"+"Avalanche C-Chain"  
        elif chain=="ETH":
            chainID=token+"-"+"ERC20" 
        elif chain=="FTM":
            chainID=token+"-"+"Fantom" 
        elif chain=="ASTAR":
            chainID=token+"-"+"Astar"         
        elif chain=="SOL":
            chainID=token+"-"+"Solana"
        elif chain=="MOON":
            chainID=token+"-"+"Moonriver"   
        elif chain=="NEAR":
            chainID=token+"-"+"NEAR"  
        elif chain=="KLAY":
            chainID=token+"-"+"Klaytn" 
        elif chain=="OSMO":
            chainID=token+"-"+"Cosmos" 
        elif chain=="JUNO":
            chainID=token+"-"+"Cosmos"   
        elif chain=="ARB":
            chainID=token+"-"+"Arbitrum one"
        elif chain=="METIS":
            chainID=token+"-"+"Metis"
        elif chain=="APT":
            chainID=token+"-"+"Aptos"                 
        elif chain=="BEAM":
            chainID=token+"-"+"Moonbeam"   
        elif chain=="OKT":
            chainID=token+"-"+"OKC" 
            if "ETH" in symbol:
               chainID="ETHK"+"-"+"OKC"  
            elif "BTC" in symbol:
               chainID="BTCK"+"-"+"OKC" 
            elif "DAI" in symbol:
               chainID="DAIK"+"-"+"OKC"                              
        else:
            print("Chain không khả dụng!!!!") 
        print("chain", chainID)
        try:
            res = self.FundingAPI.get_currency()
            for data in result:
                if  token in data['ccy'] and chainID in data['chain']:
                    if data['canDep'] == False:
                        print("Tạm dừng nạp tiền rồi ", token, chain)
                        return 0,0,0
                    else:
                        mindeposit=data['minDep']
                        add, tag= self.get_deposit_address_Okx(token, chain)
                        print("Đã lấy được địa chỉ nạp tiền!!!", token, chain) 
                        return add, tag, mindeposit
        except:
            print("lỗi request")
            return "Lỗi", "Lỗi", "Lỗi"

    def get_status_withdrawal_Okx(self, symbol, chain): # Lấy trạng thái khả dụng hay bị dừng rút tiền
        token=symbol.upper()
        if chain=="Polygon":
            chainID=token+"-"+ "Polygon"
        elif chain=="OPT":
            chainID= token+"-"+"Optimism"
        elif chain=="BSC":
            chainID=token+"-"+"BSC"
        elif chain=="TRON":
            chainID=token+"-"+"TRC20"               
        elif chain=="AVAX":
            chainID= token+"-"+"Avalanche C-Chain"  
        elif chain=="ETH":
            chainID=token+"-"+"ERC20" 
        elif chain=="FTM":
            chainID=token+"-"+"Fantom" 
        elif chain=="ASTAR":
            chainID=token+"-"+"Astar"         
        elif chain=="SOL":
            chainID=token+"-"+"Solana"
        elif chain=="MOON":
            chainID=token+"-"+"Moonriver"   
        elif chain=="NEAR":
            chainID=token+"-"+"NEAR"  
        elif chain=="KLAY":
            chainID=token+"-"+"Klaytn" 
        elif chain=="OSMO":
            chainID=token+"-"+"Cosmos"
        elif chain=="JUNO":
            chainID=token+"-"+"Cosmos"    
        elif chain=="ARB":
            chainID=token+"-"+"Arbitrum one"   
        elif chain=="BEAM":
            chainID=token+"-"+"Moonbeam" 
        elif chain=="METIS":
            chainID=token+"-"+"Metis"
        elif chain=="APT":
            chainID=token+"-"+"Aptos"   
        elif chain=="OKT":
            chainID=token+"-"+"OKC"
            if "ETH" in symbol:
               chainID="ETHK"+"-"+"OKC"  
            elif "BTC" in symbol:
               chainID="BTCK"+"-"+"OKC" 
            elif "DAI" in symbol:
               chainID="DAIK"+"-"+"OKC"                                
        else:
            print("Chain không khả dụng!!!!") 
        print("chain", chainID)    
    
        try:
            while True:
                try:
                    res = self.FundingAPI.get_currency()
                    result=res['data']
                    break
                except:
                    time.sleep(1)
            for data in result:
                if  token == data['ccy'] and chainID == data['chain']:
                    print("data", data)
                    if data['canWd'] == False:
                        print("Tạm dừng rút tiền rồi ", token, chain)
                        return False, 0,0,0,0,0
                    else:
                        print("Mạng rút bình thường!!!")
                        minfee=data['minFee']
                        maxfee=data['maxFee']
                        minsize=data['minWd']
                        maxsize=data['maxWd']
                        wdTickSz = data['wdTickSz']
                        return True, minfee, maxfee, minsize, maxsize, wdTickSz

        except:
            err = str(sys.exc_info())
            #print("err", err)
            print("Chain không khả dụng!!!"+ err)    
            return "False1", 0,0,0,0,0

    def get_deposit_history_Okx(self, txt):  # Lấy lịch sử nạp tiền
        res=  self.FundingAPI.get_deposit_history(txt)
        status="Chưa thấy tín hiệu"
        try:
            token= res['data'][0]
            if token['state'] == '2':
                print("Nạp thành công!!!"+ str(token['ccy']))
                status="Nạp thành công!" + str(token['ccy'])
            else:
                print("Nạp chuẩn! pending " + str(token['ccy']))
                status="Nạp chuẩn! pending " + str(token['ccy'])  
        except:
            pass          
        return status


    def get_withdraw_history_Okx(self, wd_id): # Lấy lịch sử rút tiền
        try:
            res_wd=  self.FundingAPI.get_withdrawal_history(wd_id)
            if res_wd['code']=='0':
                result=res_wd['data'][0]
                symbol= result['chain']
                status = "Không thấy trạng thái" + str(symbol)   
                state = str(result['state'])
                if state =='0':
                    status="waiting withdrawal" + str(symbol) 
                elif state=='1':
                    status="withdrawing" + str(symbol)                          
                elif state=='2':
                    print("withdraw success")
                    status="withdraw success" + str(symbol)  
                elif state in ['4', '5', '6', '8', '9', '12']:
                    status="waiting mannual review" + str(symbol) 
                elif state=='-1':
                    status="failed" + str(symbol) 
                elif state=='-2':
                    status="canceled" + str(symbol)   
                elif state=='-3':
                    status="canceling" + str(symbol)               

        except:
            print("Lỗi lấy data" +str(sys.exc_info()))  
            status="Lỗi "+ str(sys.exc_info())           
        return status


    def transfer_Okx(self, symbol, size, From , to):  # Chuyển tiền tron nội bộ sàn ( Có nhiều sàn ko cần chức năng này)
        try:
            token=symbol.upper()
            res=  self.FundingAPI.funds_transfer(token, size, From, to, type='0')# 18:trading, 6: funding
            #break
        except:
            print("Lỗi transfer main to trading_Okx ", str(sys.exc_info()))
            return "Lỗi transfer main to trading_Okx " + str(sys.exc_info())
        if res['code'] =='0':
            print("chuyển tiền thành công")
            status="chuyển tiền thành công"
        else:
            print("Lỗi chuyển tiền OKX "+ str(res))
            status="Lỗi chuyển tiền OKX"+ str(res)
        return status


    def submit_token_withdrawal_Okx(self, symbol, size, address, chain):  # Hàm rút tiền từ OKX về 
        token=symbol.upper()
        if chain=="Polygon":
            chainID=token+"-"+ "Polygon"
        elif chain=="OPT":
            chainID= token+"-"+"Optimism"
        elif chain=="BSC":
            chainID=token+"-"+"BSC"
        elif chain=="TRON":
            chainID=token+"-"+"TRC20"               
        elif chain=="AVAX":
            chainID= token+"-"+"Avalanche C-Chain"  
        elif chain=="ETH":
            chainID=token+"-"+"ERC20" 
        elif chain=="FTM":
            chainID=token+"-"+"Fantom" 
        elif chain=="ASTAR":
            chainID=token+"-"+"Astar"         
        elif chain=="SOL":
            chainID=token+"-"+"Solana"
        elif chain=="MOON":
            chainID=token+"-"+"Moonriver"   
        elif chain=="NEAR":
            chainID=token+"-"+"NEAR"  
        elif chain=="KLAY":
            chainID=token+"-"+"Klaytn" 
        elif chain=="OSMO":
            chainID=token+"-"+"Cosmos" 
        elif chain=="JUNO":
            chainID=token+"-"+"Cosmos"  
        elif chain=="ARB":
            chainID=token+"-"+"Arbitrum one"   
        elif chain=="BEAM":
            chainID=token+"-"+"Moonbeam"
        elif chain=="METIS":
            chainID=token+"-"+"Metis"
        elif chain=="APT":
            chainID=token+"-"+"Aptos"    
        elif chain=="OKT":
            chainID=token+"-"+"OKC" 
            if "ETH" in symbol:
               chainID="ETHK"+"-"+"OKC"  
            elif "BTC" in symbol:
               chainID="BTCK"+"-"+"OKC" 
            elif "DAI" in symbol:
               chainID="DAIK"+"-"+"OKC"                                               
        else:
            print("Chain không khả dụng!!!!") 
        print("chain", chainID)

        balance, balance_funding, balance_trading= self.get_balances_Okx(token)
        tag, minfee, maxfee, minsize, maxsize, wdTickSz= self.get_status_withdrawal_Okx(token, chain)
        list_fee_ruttien = [float(minfee)*1.1, (float(minfee)*1.1 + float(maxfee))/2 , float(maxfee)]
        if float(balance)>0 and float(balance)>=float(size):
            if float(balance_funding)<float(size):
                amout1= int(float(size)*10**3)/(10**3)
                res1=  self.transfer_Okx(token, amout1, "18", "6")
            for fee_rutien in list_fee_ruttien:
                try:
                    if int(wdTickSz) >3:
                        wdTickSz =3
                    print("wdTickSz ", wdTickSz)
                    size = int((float(size)-fee_rutien)*10**int(wdTickSz))/(10**int(wdTickSz))
                    print("size ", size)
                    res=  self.FundingAPI.coin_withdraw(token, size,  "4" , address, chainID, str(fee_rutien))
                    print("submit_token_withdrawal_Okx ", res)
                    if res['code'] =='0':
                        
                        withdrawal_ID=res['data'][0]['wdId']
                        print("withdrawal_ID", withdrawal_ID)
                        print("Đã rút tiền chờ tiền về tài khoản!")
                        status = "Đã rút tiền chờ tiền về tài khoản!"
                        return True, status, withdrawal_ID                                   
                    else:
                        print("Rút tiền thất bại! " + str(res['msg']) + "fee =" + str(fee_rutien))
                        status= res['msg']
                        continue
                except:
                    err = str(sys.exc_info())
                    print("Lỗi submit_token_withdrawal_Okx ", err)
                    continue
            return False, status, 0
        else:
            print("Không đủ tiền để rút rồi người đẹp!")
            status = "Không đủ tiền rút rồi!!!"
            return False, status, 0           


toolokx = OKX_FUNCTION(keypass= '')
print(toolokx.real_buy_market_ETH(50, 0, "", False, 5))
#print(toolokx.real_buy_market_in_Okx("ETH", "USDT", 10, 0, "", False, 5))
#print(toolokx.real_sell_market_in_Okx("ETH", "USDT", 0.0137, 0, "", False, 5))
# print("Kq 1 ETH= ", toolokx.get_return_buy_Okx(symbol= 'AVAX', usd= 'ETH', amountin = 2, proxy="", fake_ip=False))

# print("Kq 2 ETH= ", toolokx.get_return_buy_Okx_withETH(symbol="AVAX", usd="USDT", amountin= 2, proxy="", fake_ip=False))

# print("Kq 11 ETH= ", toolokx.get_return_sell_Okx(symbol= 'AVAX', usd= 'ETH', amountin = 200, proxy="", fake_ip=False))

# print("Kq 21 ETH= ", toolokx.get_return_sell_Okx_withETH(symbol="AVAX", usd="USDT", amountin= 200, proxy="", fake_ip=False))

# print("okxxx 1 ", toolokx.get_best_return_buy_Okx_withETH( symbol='OKB', amountin= 2, proxy="", fake_ip= False))
# print("okxxx 2 ", toolokx.get_best_return_sell_Okx_withETH( symbol='OKB', amountin= 69.57584785849045, proxy="", fake_ip= False))
#print(toolokx.real_buy_in_Okx("POLYDOGE", "USDT", 20, 0, "proxy", False, 5))
#print(toolokx.real_sell_in_Okx("POLYDOGE", "USDT", 1136518771, 0, "proxy", False, 5))
