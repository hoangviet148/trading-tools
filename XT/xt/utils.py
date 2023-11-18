import hmac
import base64
import time
import datetime
from . import consts as c
import hashlib
import json
import urllib.parse


def clean_dict_none(d: dict) -> dict:
    return {k:d[k] for k in d.keys() if d[k] != None}


def sign(payload, secret_key, api_key):
    if not all([payload.get('accesskey'), payload.get('nonce')]):
        payload['accesskey'] = api_key
        payload['nonce']  = str(int(time.time() * 1000))
        # Need sorted
        payload = urllib.parse.urlencode(dict(sorted(payload.items(), key = lambda kv:(kv[0], kv[1]))))
    print("payload: ", payload)
    
    signature = hmac.new(secret_key.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).hexdigest().upper()
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