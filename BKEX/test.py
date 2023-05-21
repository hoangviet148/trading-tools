import requests
import json
import time
import hashlib
import hmac
import base64
import urllib.parse

api_key = 'FoPcc7arU8rybD2Q/rzLNdhskiMBSySO1E9HXjmLdJAKUxKTDAXjxD2V'
api_secret = 'kqwRBfN4djmE5iQmwbrpGOzptLK95hDatklPKVQGuOWk8UqCFuYEmxw1hGSweCNBrqaMhS93tygnToD+Hx0DMA=='
request_path = "/0/private/Balance"
url = "https://api.kraken.com" + request_path
nonce = str(int(time.time() * 1000))

data = {
    "nonce": nonce
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