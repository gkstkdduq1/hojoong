from operator import index

import pyupbit
from tqdm import tqdm
import requests
import pandas as pd
import time
from kakao import Kakao

# import trading

account = 0
fee = 0.001
ror = 1
balance = 10000
RATE = 0.5
V_RATE = 1.5
VMA_WINDOW = 60
MA_WINDOW = 3

def tickSize(price):
    if price > 2000000:
        tick = 1000
    elif price > 1000000:
        tick = 500
    elif price > 100000:
        tick = 50
    elif price > 10000:
        tick = 10
    elif price > 1000:
        tick = 5
    elif price > 100:
        tick = 1
    elif price > 10:
        tick = 0.1
    else:
        tick = 0.01

    return tick


while True:

    start_time = time.time()
    with open("upbit_key.txt") as f:
        lines = f.readlines()
        access_key = lines[0].strip()
        secret_key = lines[1].strip()

    upbit = pyupbit.Upbit(access_key, secret_key)
    kakao = Kakao()

    kakao.send_message2me(f'안녕하세요.\n\n'
                          '트레이딩을 시작합니다.\n'
                          '거래대금 상위 10종목을 선택하여 \n매수/매도를 반복합니다.\n\n'
                          '목표가에 도달하면 전액 매수하고 \n매도 조건에 도달하면 전액 매도합니다.')

    url = "https://api.upbit.com/v1/ticker"
    tickers = pyupbit.get_tickers(fiat="KRW")
    trade_price_list = []
    change_list = []
    ticker_idx = []
    for ticker in tqdm(tickers):
        querystring = {"markets": ticker}
        response = requests.request("GET", url, params=querystring)
        # print(response.json()[0]['acc_trade_price_24h'])
        time.sleep(0.1)
        if response.json()[0]['trade_price'] > 0:
            trade_price_list.append(response.json()[0]['acc_trade_price'])
            change_list.append(response.json()[0]['change'])
            ticker_idx.append(ticker)

    trade_price_df = pd.DataFrame(list(zip(trade_price_list, change_list)), index=ticker_idx,
                                  columns=['trade_price', 'change'])
    trade_price_df.sort_values(by=['trade_price'], ascending=False, inplace=True)
    ticker_list = trade_price_df.iloc[:5].index.tolist()
    #ticker_list = trade_price_df.index.tolist()
    ticker_list_str = ''
    for i in ticker_list:
        ticker_list_str += '\n' + i
    ticker_list_str = "\n".join(ticker_list)

    kakao.send_message2me(f"현재 거래대금 상위 10종목은:\n{ticker_list_str}\n입니다."
                          f"\n(5000원 미만 종목 제외)")

    while True:
        for ticker in ticker_list:
            while True:
                url = "https://api.upbit.com/v1/candles/minutes/1"
                querystring = {"market": ticker, "count": "500"}
                response = requests.request("GET", url, params=querystring)
                data = response.json()
                df = pd.DataFrame(data)
                df = df.reindex(index=df.index[::-1]).reset_index()
                df = df[-60:]
                df['ma'] = df['trade_price'].rolling(window=MA_WINDOW).mean()
                df['ma5'] = df['trade_price'].rolling(window=5).mean()
                df['ma20'] = df['trade_price'].rolling(window=20).mean()
                # df['ma50'] = df['trade_price'].rolling(window=50).mean()
                df['vma'] = df['candle_acc_trade_volume'].rolling(window=VMA_WINDOW).mean()
                # df['close_diff'] = df['trade_price'].diff()
                df['sma_diff'] = df['ma'].diff()
                df['range'] = (df['high_price'].shift(1) - df['low_price'].shift(1)) * RATE
                # df['range_shift'] = df['range'].shift(1)
                # df['target'] = df['opening_price'] + df['range'].shift(1)
                # df['target2'] = df['opening_price'] * 1.003
                # df['target'] = df['opening_price']

                df = df[-1:]

                cur_price = pyupbit.get_current_price(ticker)
                target_range = df['range'].values[0] if df['range'].values[0] > tickSize(cur_price) else tickSize(
                    cur_price)
                target_price = df['opening_price'].values[0] + target_range
                # target_price1 = df['target1'].values[0]
                # target_price2 = df['target2'].values[0]
                sma_diff = df['sma_diff'].values[0]
                # close_diff = df['close_diff'].values[0]
                ma5 = df['ma5'].values[0]
                ma20 = df['ma20'].values[0]
                # ma50 = df['ma50'].values[0]
                vma = df['vma'].values[0]
                target_volume = vma * V_RATE
                volume = df['candle_acc_trade_volume'].values[0]

                sell_signal = sma_diff < 0 #and cur_price < ma10
                # buy_signal = not sell_signal and cur_price > target_price1 and cur_price > target_price2 and cur_price
                # > ma20 and ma5 > ma20 > ma50
                buy_signal = not sell_signal and cur_price > target_price and volume > target_volume and ma5 > ma20

                # buy here
                if buy_signal and account == 0:
                    # buyprice, balance = trading.trade(upbit, 'buy', ticker)
                    orderbook = pyupbit.get_orderbook(ticker)
                    bids_asks = orderbook[0]['orderbook_units']
                    bid_price = bids_asks[0]['bid_price']
                    buyprice = bid_price
                    #buyprice = pyupbit.get_current_price(ticker)

                    account = 1

                    message = f'{ticker}를 {buyprice}에 \n전량매수 했습니다.\n\n매수 체결량: \n{balance}원'
                    print(message)
                    kakao.send_message2me(message)

                # sell here
                if sell_signal and account == 1:
                    # sellprice, balance = trading.trade(upbit, 'sell', ticker)
                    orderbook = pyupbit.get_orderbook(ticker)
                    bids_asks = orderbook[0]['orderbook_units']
                    ask_price = bids_asks[0]['ask_price']
                    sellprice = ask_price
                    #sellprice = pyupbit.get_current_price(ticker)
                    this_ror = (sellprice / buyprice) - fee
                    ror = ror * this_ror
                    balance = ror * 10000
                    account = 0

                    message = f'{ticker}를 {sellprice}에 \n전량매도 했습니다.\n\n매도 체결 후 잔액:\n{balance}원\n\n' \
                              f'이번 수익률: {round((this_ror - 1) * 100, 2)}%\n' \
                              f'총 수익률: {round((ror - 1) * 100, 2)}%'
                    print(message)
                    kakao.send_message2me(message)

                if account == 1:
                    ror_now = ror * (cur_price / buyprice) - fee
                    print('1 minute ', ticker, ', ror:', round(ror_now, 4), ', buy_signal:', buy_signal,
                          ', cur_price: ',
                          cur_price,
                          ', target: ', target_price,', volume: ', (target_volume-volume),  ', account:', account, '          ', end='\r')
                if account == 0:
                    print('1 minute ', ticker, ', ror:', round(ror, 4), ', buy_signal:', buy_signal, ', cur_price: ',
                          cur_price,
                          ', target: ', target_price,', volume: ', (target_volume-volume),  ', account:', account, '          ', end='\r')

                time.sleep(0.1)
                if account == 0 and not buy_signal:
                    break
        cur_time = time.time()
        if cur_time >= start_time + 3600:
            break
