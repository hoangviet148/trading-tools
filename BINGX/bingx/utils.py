import hmac
import base64
import time
import datetime
from . import consts as c
import hashlib
import json
from hashlib import sha256

def clean_dict_none(d: dict) -> dict:
    return {k:d[k] for k in d.keys() if d[k] != None}


def get_sign(api_secret, payload):
    signature = hmac.new(api_secret.encode("utf-8"), payload.encode("utf-8"), digestmod=sha256).hexdigest()
    print("sign=" + signature)
    return signature

def pre_substring(timestamp, memo, body):
    return f'{str(timestamp)}#{memo}#{body}'

def get_timestamp():
    return str(datetime.datetime.now().timestamp() * 1000).split('.')[0]

def pre_hash(timestamp, method, request_path, body):
    return str(timestamp) + str.upper(method) + request_path + body

def get_header(api_key):
    header = dict()
    # header[c.CONTENT_TYPE] = c.APPLICATION_JSON
    header[c.ACCESS_KEY] = api_key
    # header[c.ACCESS_SIGN] = sign
    # header[c.DIGEST] = "HMAC-SHA512"
    return header

def praseParam(paramsMap):
    sortedKeys = sorted(paramsMap)
    paramsStr = "&".join(["%s=%s" % (x, paramsMap[x]) for x in sortedKeys])
    return paramsStr+"&timestamp="+str(int(time.time() * 1000))