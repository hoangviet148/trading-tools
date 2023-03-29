import requests
import json
import time
import hashlib
import hmac
import base64
import urllib.parse

api_key = 'ckLFiOjFcq/UQ4z1nnscsQ8Ejdq4bf7TtGJX7UXc4E123/sX8uGbQKc7'
api_secret = '/YVJ/6SqsczOy2pW8VstkNmyEv0jDajbia8Y5Mxmgzl9X/zcp50KD4W5wftOmMn44QjLb0Q0v2HMP2pbdeXCIw=='
url = "https://api.kraken.com/0/private/AddOrder"
request_path = "/0/private/AddOrder"
nonce = int(time.time() * 1000)

data = {
    "nonce": nonce, 
    "ordertype": "limit", 
    "pair": "XBTUSD",
    "price": 37500, 
    "type": "buy",
    "volume": 1.25
}

# Generate signature
postdata = urllib.parse.urlencode(data)
encoded = (str(nonce) + postdata).encode()
message = request_path.encode() + hashlib.sha256(encoded).digest()

mac = hmac.new(base64.b64decode(api_secret), message, hashlib.sha512)
sigdigest = base64.b64encode(mac.digest())
signature = sigdigest.decode()

header = {
    'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8', 
    'API-Key': api_key, 
    'API-Sign': signature
}

response = requests.post(url, headers=header, data=data)
print(f"response === {response.json()} - {response.status_code}")