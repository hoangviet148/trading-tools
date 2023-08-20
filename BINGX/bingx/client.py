import requests
import json
import time
from . import consts as c, utils, exceptions
from hashlib import sha256
import hmac
import base64
from urllib import parse
from . import consts as c

class Client(object):

    def __init__(self, api_key, secret_key):

        self.API_KEY = api_key
        self.SECRET_KEY = secret_key   
        self.MEMO = "api1"     

    def _public_request(self, method, request_path):
        url = c.API_URL + request_path
        print(f"_public_request {url}")
        response = requests.get(url)
        return response.json()

    def _request(self, method, request_path, params):

        print(f"request_path {request_path} params {type(params)}")
        paramsStr = utils.praseParam(params)
        # sign = utils.sign(self.SECRET_KEY, paramsStr)

        url = "%s%s?%s&signature=%s" % (c.API_URL, request_path, paramsStr, utils.get_sign(self.SECRET_KEY, paramsStr))
        body = json.dumps(params)
        header = utils.get_header(self.API_KEY)
       
        # send request
        response = None
        print("url:", url)
        print("headers:", header)
        print("body:", body)

        try:
            response = requests.request(method, url, headers=header, data={})
            print(f"response post === {response.json()} - {response.status_code}")
        except Exception as e:
            print(f"Exception {e}")
            exit

        # exception handle
        # print(response.headers)

        if not str(response.status_code).startswith('2'):
            raise exceptions.APIException(response)

        return response.json()

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
