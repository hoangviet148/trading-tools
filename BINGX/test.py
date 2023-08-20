import requests
import json
import time
from hashlib import sha256
import hmac
import base64
from urllib import parse

api_key = '6bf34c02-a263-4255-9cff-9cece36992d2'
api_secret = 'MWM0Mjk2NzYtMTEwOS00NmQ4LWE5YjctZDc5YmZhMjY0NTQx'
request_path = "/v2/u/account/balance"
url = "https://api.latoken.com" + request_path

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

