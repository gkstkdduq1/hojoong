import time
import pyupbit
import jwt
import uuid
import hashlib
import requests
from urllib.parse import urlencode


def trade(upbit, position, ticker):

    orderbook = pyupbit.get_orderbook(ticker)

    if position == 'buy':
        balance = float(upbit.get_balances()[0]['balance'])
        bids_asks = orderbook[0]['orderbook_units']
        bid_price = bids_asks[0]['bid_price']
        price = bid_price
        volume = balance / price
        ret = upbit.buy_limit_order(ticker, price * 0.9, volume)
    elif position == 'sell':
        balance = float(upbit.get_balances()[1]['balance'])
        bids_asks = orderbook[0]['orderbook_units']
        ask_price = bids_asks[0]['ask_price']
        price = ask_price
        volume = balance
        ret = upbit.sell_limit_order(ticker, price, volume)

    print(ret)
    uid = ret['uuid']
    state = ret['state']
    time.sleep(1)
    counter = 0

    while state == 'wait':

        server_url = 'https://api.upbit.com'

        query = {
            'uuid': uid,
        }
        query_string = urlencode(query).encode()

        m = hashlib.sha512()
        m.update(query_string)
        query_hash = m.hexdigest()

        payload = {
            'access_key': upbit.access,
            'nonce': str(uuid.uuid4()),
            'query_hash': query_hash,
            'query_hash_alg': 'SHA512',
        }

        jwt_token = jwt.encode(payload, upbit.secret)
        authorize_token = 'Bearer {}'.format(jwt_token)
        headers = {"Authorization": authorize_token}
        res = requests.get(server_url + "/v1/order", params=query, headers=headers)
        state = res.json()['state']

        if state == 'done' or state == 'cancel':
            print(state)
            break
        if counter >= 30:
            ret = upbit.cancel_order(uid)
            state = ret['state']

        counter += 1
        time.sleep(1)

    if position == 'buy':
        balance = float(upbit.get_balances()[1]['balance'])
    elif position == 'sell':
        balance = round(float(upbit.get_balances()[0]['balance']), 2)

    return price, balance
