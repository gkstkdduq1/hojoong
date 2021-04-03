import pyupbit
from tqdm import tqdm
import requests
import pandas as pd
import time
import json

with open("kakao_code.json", "r") as fp:
    tokens = json.load(fp)

url = "https://kauth.kakao.com/oauth/token"
data = {
    "grant_type": "refresh_token",
    "client_id": "6bea89b579e0495940a0b8989903b22f",
    "refresh_token": tokens["refresh_token"]
}
response = requests.post(url, data=data)
tokens = response.json()

with open("kakao_code.json", "w") as fp:
    json.dump(tokens, fp)

kakao_url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"

headers = {
    "Authorization": "Bearer " + tokens["access_token"]
}

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
print(ticker_list)

while True:
    for ticker in ticker_list:
        while True:
            url = "https://api.upbit.com/v1/candles/minutes/10"

            querystring = {"market": ticker, "count": "500"}

            response = requests.request("GET", url, params=querystring)
            data = response.json()
            df = pd.DataFrame(data)
            df = df.reindex(index=df.index[::-1]).reset_index()
            df = df[-50:]
            df['ma5'] = df['trade_price'].rolling(window=5).mean()
            df['ma20'] = df['trade_price'].rolling(window=20).mean()
            df['ma50'] = df['trade_price'].rolling(window=50).mean()
            df['sma5_diff'] = df['ma5'].diff()
            df['range'] = (df['high_price'] - df['low_price']) * 0.7
            df['target1'] = df['opening_price'] + df['range'].shift(1)
            df['target2'] = df['opening_price'] * 1.003

            df = df[-1:]

            cur_price = pyupbit.get_current_price(ticker)
            target_price1 = df['target1'].values[0]
            target_price2 = df['target2'].values[0]
            sma5_diff = df['sma5_diff'].values[0]
            ma5 = df['ma5'].values[0]
            ma20 = df['ma20'].values[0]
            ma50 = df['ma50'].values[0]

            sell_signal = sma5_diff < 1 or cur_price < ma5
            buy_signal = not sell_signal and cur_price > target_price1 and cur_price > target_price2 and cur_price > ma20 and ma5 > ma20 > ma50

            # buy here
            if buy_signal and balance == 0:
                buyprice = pyupbit.get_current_price(ticker)
                balance = 1
                print('buy', ticker, 'at', buyprice)

                data = {
                    "template_object": json.dumps({
                        "object_type": "text",
                        "text": 'buy' + ticker + ' at' + str(buyprice),
                        "link": {
                            "web_url": "www.naver.com"
                        }
                    })
                }

                requests.post(kakao_url, headers=headers, data=data)

            # sell here
            if sell_signal and balance == 1:
                sellprice = pyupbit.get_current_price(ticker)
                ror = ror * ((sellprice / buyprice) - fee)
                balance = 0
                print('sell at ', sellprice)
                print('ror is ', ror)
                data = {
                    "template_object": json.dumps({
                        "object_type": "text",
                        "text": 'sell ' + ticker + ' at' + str(sellprice)+ '\nror is ' + str(ror),
                        "link": {
                            "web_url": "www.naver.com"
                        }
                    })
                }

                requests.post(kakao_url, headers=headers, data=data)

            if balance == 1:
                ror_now = (cur_price / buyprice) - fee
                print('10 minute ', ticker, ', ror:', round(ror_now, 4), ', buy_signal', buy_signal, ', cur_price : ',
                      cur_price,
                      ', target: ', target_price1, ', balance:', balance, '          ', end='\r')
            if balance == 0:
                print('10 minute ', ticker, ', ror:', round(ror, 4), ', buy_signal', buy_signal, ', cur_price : ',
                      cur_price,
                      ', target: ', target_price1, ', balance:', balance, '          ', end='\r')

            time.sleep(0.1)
            if balance == 0 and not buy_signal:
                break
