import pyupbit

import requests
import pandas as pd
import time
from tqdm import tqdm

access_key = "Uc7gjRjwxKWtqi3CzE8eBa0GBxKEuvxstqy4VBux"
secret_key = "BuXKRKaxcPdhL8Htpl1cGsVbqGh0zd10DHVLLxWB"

upbit = pyupbit.Upbit(access_key, secret_key)

balance = 0
fee = 0.001
ror = 1

url = "https://api.upbit.com/v1/ticker"

tickers = pyupbit.get_tickers(fiat="KRW")
trade_price_list = []
change_list = []

for ticker in tqdm(tickers):
    querystring = {"markets": ticker}
    response = requests.request("GET", url, params=querystring)
    # print(ticker)
    # print(response.json()[0]['acc_trade_price_24h'])
    time.sleep(0.1)
    trade_price_list.append(response.json()[0]['acc_trade_price_24h'])
    change_list.append(response.json()[0]['change'])

trade_price_df = pd.DataFrame(list(zip(trade_price_list, change_list)), index=tickers,
                              columns=['trade_price', 'change'])
trade_price_df.sort_values(by=['trade_price'], ascending=False, inplace=True)
ticker_list = trade_price_df.iloc[:10].index.tolist()
print(ticker_list)xc

ticker_list = [ 'KRW-MED']
while True:
    for ticker in ticker_list:
        while True:


            url = "https://api.upbit.com/v1/candles/minutes/10"

            querystring = {"market": ticker, "count": "500"}

            response = requests.request("GET", url, params=querystring)
            data = response.json()
            df = pd.DataFrame(data)
            df = df.reindex(index=df.index[::-1]).reset_index()
            df = df[-20:]
            ma20 = df['trade_price'].mean()

            df = df[-5:]
            ma10 = df['trade_price'].mean()
            df['range'] = (df['high_price'] - df['low_price']) * 0.5
            df['target'] = df['opening_price'] + df['range'].shift(1)
            df = df[-1:]
            cur_price = pyupbit.get_current_price(ticker)
            bull_flag = cur_price > ma10 and cur_price > ma20
            target_price = df['target'].values[0]
            signal = bull_flag and cur_price > target_price


            # buy here
            if signal and balance == 0:
                buyprice = pyupbit.get_current_price(ticker)
                balance = 1
                print('buy', ticker, 'at', buyprice)

            # sell here
            if not bull_flag and balance == 1:
                sellprice = pyupbit.get_current_price(ticker)
                ror = ror * ((sellprice / buyprice) - fee)
                balance = 0
                print('sell at ', sellprice)
                print('ror is ', ror)

            if balance == 1:
                ror_now = (cur_price / buyprice) - fee
                print(', Upbit 1 minute ', ticker, ', ror:', round(ror_now, 4), 'signal', signal, ', cur_price : ',
                      cur_price,
                      ', target: ', target_price, ', bull: ', bull_flag, ', balance:', balance, '              ',
                      end='\r')
            if balance == 0:
                print(', Upbit 1 minute ', ticker, ', ror:', round(ror, 4), 'signal', signal, ', cur_price : ',
                      cur_price,
                      ', target: ', target_price, ', bull: ', bull_flag, ', balance:', balance, '              ',
                      end='\r')
            time.sleep(0.1)
            if balance == 0 and not signal:
                break



