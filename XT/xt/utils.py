import hmac
import base64
import time
import datetime
from . import consts as c
import hashlib
import json
import urllib.parse
from urllib.parse import quote

def clean_dict_none(d: dict) -> dict:
    return {k:d[k] for k in d.keys() if d[k] != None}


def sign(payload, secret_key, api_key):
    path = "/v4/deposit/address"
    query_data = ""
    body_data = json.dumps(payload)
    method = "GET"
    print("test: ", body_data, type(body_data))
    concatenated_data = f"#{method}#{path}#{body_data}"
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
    signature = hmac.new(secret_key.encode(), original_data.encode(), hashlib.sha256).hexdigest()

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
    header[c.ACCESS_KEY] = api_key
    header[c.ACCESS_SIGN] = sign
    header[c.DIGEST] = "HmacSHA256"
    header[c.RECVWINDOW] = "5000"
    header[c.TIMESTAMP] = timestamp
    return header

def parse_params_to_str(params):
    params = clean_dict_none(params)
    url = '?'
    for key, value in params.items():
        url = url + str(key) + '=' + str(value) + '&'
    return url[0:-1]