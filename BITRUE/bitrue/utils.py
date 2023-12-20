import hmac
import base64
import time
import datetime
from . import consts as c
import hashlib
import json
import urllib.parse
from urllib.parse import quote
from urllib.parse import urlencode

def clean_dict_none(d: dict) -> dict:
    return {k:d[k] for k in d.keys() if d[k] != None}


def sign(method, path, query_data, secret_key, api_key):
    if path == '/v4/order' or path == '/v4/withdraw' or path == '/v4/balance/transfer':
        query_data = json.dumps(query_data)
    else:
        query_data = urlencode(query_data)
    
    body_data = ""
    print("test: ", body_data, type(body_data))
    concatenated_data = f"#{method}#{path}"
    if query_data != "":
        concatenated_data = f"#{method}#{path}#{query_data}"
    timestamp = str(int(time.time() * 1000))
    headers = {
        'validate-algorithms': 'HmacSHA256',
        'validate-appkey': api_key,
        'validate-recvwindow': '5000',
        'validate-timestamp': timestamp
    }
    header_string = '&'.join([f"{key}={quote(str(headers[key]))}" for key in sorted(headers.keys())])
    original_data = f"{header_string}{concatenated_data}"
    print("original_data: ", original_data)
    print("secret_key: ", secret_key)
    signature = hmac.new(secret_key.encode('utf-8'), original_data.encode('utf-8'), hashlib.sha256).hexdigest().upper()
    print("signature: ", signature)

    return signature

def pre_substring(timestamp, memo, body):
    return f'{str(timestamp)}#{memo}#{body}'

def get_timestamp():
    return str(datetime.datetime.now().timestamp() * 1000).split('.')[0]

def pre_hash(timestamp, method, request_path, body):
    return str(timestamp) + str.upper(method) + request_path + body

def get_header(api_key, sign, timestamp):
    header = dict()
    
    header[c.CONTENT_TYPE] = 'application/json'
    header[c.DIGEST] = "HmacSHA256"
    header[c.ACCESS_KEY] = api_key
    header[c.RECVWINDOW] = "5000"
    header[c.TIMESTAMP] = timestamp
    header[c.ACCESS_SIGN] = sign
    
    
    return header

def parse_params_to_str(params):
    params = clean_dict_none(params)
    url = '?'
    for key, value in params.items():
        url = url + str(key) + '=' + str(value) + '&'
    return url[0:-1]