import requests
import json
import time
from . import consts as c, utils, exceptions
import hashlib
import hmac
import base64
import urllib.parse

class Client(object):

    def __init__(self, api_key, api_secret_key):

        self.API_KEY = api_key
        self.API_SECRET_KEY = api_secret_key

    def _public_request(self, method, request_path):
        url = c.API_URL + request_path
        print(f"_public_request {url}")
        response = requests.get(url)
        return response.json()

    def _request(self, method, request_path, params):

        print(f"request_path {request_path} params {params}")

        if method == c.GET:
            request_path = request_path + utils.parse_params_to_str(params)
        # url
        url = c.API_URL + request_path
        timestamp = utils.get_timestamp()

        # sign & header
        body = json.dumps(params) if method == c.POST else ""

        # Generate signature
        postdata = urllib.parse.urlencode(params)
        encoded = (str(params['nonce']) + postdata).encode()
        message = request_path.encode() + hashlib.sha256(encoded).digest()

        mac = hmac.new(base64.b64decode(self.API_SECRET_KEY), message, hashlib.sha512)
        sigdigest = base64.b64encode(mac.digest())
        signature = sigdigest.decode()
    
        header = utils.get_header(self.API_KEY, signature)
       

        # send request
        response = None

        print("url:", url)
        print("headers:", header)
        print("body:", params)

        if method == c.GET:
            response = requests.get(url, headers=header)
            print(f"response === {response.json()} - {response.status_code}")
        elif method == c.POST:
            try:
                response = requests.post(url, headers=header, data=params)
                print(f"response post === {response.json()} - {response.status_code}")
            except Exception as e:
                print(f"Exception {e}")
                exit

        # exception handle
        # print(response.headers)

        if not str(response.status_code).startswith('2'):
            raise exceptions.krakenAPIException(response)

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
