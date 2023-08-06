import requests
import json
import time
from . import consts as c, utils, exceptions
from hashlib import sha256
import hmac
import base64
from urllib import parse

class Client(object):

    def __init__(self, api_key, secret_key, memo):

        self.API_KEY = api_key
        self.SECRET_KEY = secret_key   
        self.MEMO = memo   

    def _public_request(self, method, request_path):
        url = c.API_URL + request_path
        #print(f"_public_request {url}")
        response = requests.get(url, timeout=5)
        return response.json()

    def _request(self, method, request_path, params):

        #print(f"request_path {request_path} params {params}")

        if method == c.GET or method == c.DELETE:
            url = c.API_URL + request_path + utils.parse_params_to_str(params)
        else:
            url = c.API_URL + request_path

        timestamp = int(time.time() * 1000)  #utils.get_timestamp()
        body = json.dumps(params)

        sign = utils.sign(utils.pre_substring(timestamp, self.MEMO, str(body)), self.SECRET_KEY)
    
        header = utils.get_header(self.API_KEY, sign, timestamp)
       
        # send request
        response = None
        #print("url:", url)
        #print("headers:", header)
        #print("body:", body)
        try:
            if method == c.GET:
                response = requests.get(url, headers=header, timeout=5)
                return response.json()
                #print(f"response get === {response.json()} - {response.status_code}")
            elif method == c.POST:
                response = requests.post(url, headers=header, data=body, timeout=5)
                return response.json()
        except:
            return "Lỗi request bitmart"

        

    def _request_without_params(self, method, request_path):
        return self._request(method, request_path, {})

    def _request_with_params(self, method, request_path, params):
        return self._request(method, request_path, params)

    def _get_timestamp(self):
        url = c.API_URL + c.SERVER_TIMESTAMP_URL
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()['ts']
        else:
            return ""
