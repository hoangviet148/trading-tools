import requests
import json
import time
from hashlib import sha256
import hmac
import base64
from urllib import parse

api_key = '0e6c4a52ca1fdc19bcbd05602800ca962e9ac56dbf6e0e550b0b194a429596d5'
api_secret = '98a649b9fd88a32683e53c20a35593773a47d763ebd31daa6a35bad1c2603dcd'
request_path = "/v2/u/account/balance"
url = "https://api.bkex.com" + request_path

def get_sign(url):
    params_arr = url.split("?")
    source = ""
    if len(params_arr) > 1:
        param = params_arr[1]
        unsorted_arr = param.split("&")
        source = "&".join(sorted(unsorted_arr))
        print(source)
    sign = hmac.new(bytes(api_secret, encoding='utf-8'), bytes(source, encoding='utf-8'), sha256).hexdigest()
    print("sign: " + sign)
    return sign

data = {
    "currencys": "ETH"
}
url = url + "?" + parse.urlencode(data)
print(url)
signature = get_sign(url)

header = {
    'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8', 
    'X_ACCESS_KEY': api_key, 
    'X_SIGNATURE': signature
}



response = requests.get(url, headers=header, data=data)
# response = requests.post(url, headers=header, data=data)
print(f"response === {response.json()} - {response.status_code}")

