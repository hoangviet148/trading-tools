import hmac
import base64
import time
import datetime
from . import consts as c
import hashlib
import json


def clean_dict_none(d: dict) -> dict:
    return {k:d[k] for k in d.keys() if d[k] != None}


def sign(method, endpoint, params, secret_key):
    print("get sign start ====")
    serializeFunc = map(lambda it : it[0] + '=' + str(it[1]), params.items())
    bodyParams = '&'.join(serializeFunc)
    mac = hmac.new(
        bytes(secret_key, encoding='utf8'), 
        (method + endpoint + bodyParams).encode('ascii'),
        hashlib.sha512)
    # print("get sign end ====")
    return mac.hexdigest()

def pre_substring(timestamp, memo, body):
    return f'{str(timestamp)}#{memo}#{body}'

def get_timestamp():
    return str(datetime.datetime.now().timestamp() * 1000).split('.')[0]

def pre_hash(timestamp, method, request_path, body):
    return str(timestamp) + str.upper(method) + request_path + body

def get_header(api_key, sign, timestamp):
    header = dict()
    header[c.CONTENT_TYPE] = c.APPLICATION_JSON
    header[c.ACCESS_KEY] = api_key
    header[c.ACCESS_SIGN] = sign
    header[c.DIGEST] = "HMAC-SHA512"
    return header

def parse_params_to_str(params):
    params = clean_dict_none(params)
    url = '?'
    for key, value in params.items():
        url = url + str(key) + '=' + str(value) + '&'
    return url[0:-1]