# key: wQ6wqCi42MZD7Y95G2t3tvJBW+hCEjl78EF2qxpM8rt0bVInqyHfsKul
# private: OWmsaZQDDlWJNj/+YWLpTZM1mjxfsGQ65H3dzhudR7n15+iNxiIHkjkHqVGzECBK7p5O7d5AQt8XXAjT6AWpzQ==

import sys
import datetime
import json
import requests
import time
import cloudscraper
from concurrent.futures import ThreadPoolExecutor
from lib2to3.pgen2 import token
from unittest import result
import os

import kraken.Account_api as Account
import kraken.Funding_api as Funding
import kraken.Market_api as Market
import kraken.Public_api as Public
import kraken.Trade_api as Trade
import kraken.subAccount_api as SubAccount
import kraken.status_api as Status

import logging
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from decouple import config

scraper = cloudscraper.create_scraper()
path_file = os.path.dirname(os.path.abspath(__file__))

ROOT_URL = 'https://www.kraken.com/'

flag = '0'

class KRAKEN_FUNCTION:
    def __init__(self, keypass=None) :
        print("Init!")
        if keypass != None:

            # NHẬP KEY, SECRET của API
            self.api_key = 'wQ6wqCi42MZD7Y95G2t3tvJBW+hCEjl78EF2qxpM8rt0bVInqyHfsKul'  
            self.api_secret = 'OWmsaZQDDlWJNj/+YWLpTZM1mjxfsGQ65H3dzhudR7n15+iNxiIHkjkHqVGzECBK7p5O7d5AQt8XXAjT6AWpzQ=='
            self.api_passphrase = null

            self.FundingAPI= Funding.FundingAPI(self.api_key, self.api_secret, self.api_passphrase,False, flag)
            self.TradeAPI= Trade.TradeAPI(self.api_key, self.api_secret, self.api_passphrase, False, flag)
            self.AccountAPI= Account.AccountAPI(self.api_key, self.api_secret, self.api_passphrase,False, flag)
            self.MarketAPI= Market.MarketAPI(self.api_key, self.api_secret, self.api_passphrase, False, flag)

toolkraken = KRAKEN_FUNCTION(keypass= '')