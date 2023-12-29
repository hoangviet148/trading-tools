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
import subprocess

def clean_dict_none(d: dict) -> dict:
    return {k:d[k] for k in d.keys() if d[k] != None}


def sign(method, path, query_data, secret_key, api_key):
    body_data = ""
    concatenated_data = ""

    query_string = "{" + ",".join([f"\"{key}\":\"{value}\"" for key, value in query_data.items()]) + "}"
    query_string = query_string.replace('"', '\\"')
    # query_string = '&'.join([f"{key}={quote(str(query_data[key]))}" for key in (query_data.keys())])
    print("query_string: ", query_string)

    # timestamp = str(int(time.time() * 1000))
    # headers = {
    #     'validate-recvwindow': '5000',
    #     'validate-timestamp': timestamp
    # }
    # header_string = '&'.join([f"{key}={quote(str(headers[key]))}" for key in (headers.keys())])
    original_data = f"{query_string}"
    print("original_data: ", original_data)

    secret_key = "18e8a4b513c86d843b2b77e12b03deba69f3c189d31fdba9ccab990175fa4b62"

    command = f'echo -n "{original_data}" | openssl dgst -sha256 -hmac "{secret_key}"'
    print("command: ", command)

    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, text=True)

    print(result.stdout.strip().split(" "))

    return result.stdout.strip().split(" ")[1]



def pre_substring(timestamp, memo, body):
    return f'{str(timestamp)}#{memo}#{body}'

def get_timestamp():
    return str(datetime.datetime.now().timestamp() * 1000).split('.')[0]

def pre_hash(timestamp, method, request_path, body):
    return str(timestamp) + str.upper(method) + request_path + body

def get_header(api_key, sign, timestamp):
    header = dict()
    header["X-CH-APIKEY"] = api_key
    # header["X-CH-SIGN"] = sign
    # header["X-CH-TS"] = timestamp
    # header["Content-Type"] = "application/json"
    return header

def parse_params_to_str(params):
    params = clean_dict_none(params)
    url = '?'
    for key, value in params.items():
        url = url + str(key) + '=' + str(value) + '&'
    return url[0:-1]