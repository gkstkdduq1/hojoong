import pyupbit

import requests
import pandas as pd
import time

access_key = "Uc7gjRjwxKWtqi3CzE8eBa0GBxKEuvxstqy4VBux"
secret_key = "BuXKRKaxcPdhL8Htpl1cGsVbqGh0zd10DHVLLxWB"

upbit = pyupbit.Upbit(access_key, secret_key)

tickers = pyupbit.get_tickers(fiat="KRW")

ticker = 'KRW-MTL'
balance = 0
fee = 0.001
ror = 1
while True:
    url = "https://api.upbit.com/v1/candles/minutes/1"

    querystring = {"market": ticker, "count": "500"}

    response = requests.request("GET", url, params=querystring)
    data = response.json()
    df = pd.DataFrame(data)
    df = df.reindex(index=df.index[::-1]).reset_index()
    df = df[-5:]
    df['range'] = (df['high_price'] - df['low_price']) * 0.1
    df['target'] = df['opening_price'] + df['range'].shift(1)

    df = df[-1:]
    ma5 = df['trade_price'].mean()
    df['bull'] = df['opening_price'] > ma5
    bull_flag = df['bull'].values[0]
    cur_price = pyupbit.get_current_price(ticker)
    target_price = df['target'].values[0]
    if cur_price > target_price and bull_flag and balance == 0:
        buyprice = pyupbit.get_current_price(ticker)
        balance = 1

    if not df['bull'].values[0] & balance == 0:
        sellprice = pyupbit.get_current_price(ticker)
        ror = ror * (sellprice / buyprice - fee)
        banance = 0

    print('Upbit 1 minute ', ticker, ',cur_price : ', cur_price, ',target: ', target_price, ',bull: ', bull_flag,
          ',ror:', ror, end='\r')

    time.sleep(1)



