import requests
from time import sleep
import numpy as np
import time

s = requests.Session()
s.headers.update({'X-API-key': 'EZZULRX1'}) # Make sure you use YOUR API Key

# global variables
MAX_LONG_EXPOSURE_NET = 25000
MAX_SHORT_EXPOSURE_NET = -25000
MAX_EXPOSURE_GROSS = 500000
ORDER_LIMIT = 5000

def get_tick():   
    resp = s.get('http://localhost:9999/v1/case')
    if resp.ok:
        case = resp.json()
        return case['tick'], case['status']


def get_bid_ask(ticker):
    payload = {'ticker': ticker}
    resp = s.get ('http://localhost:9999/v1/securities/book', params = payload)
    if resp.ok:
        book = resp.json()
        bid_side_book = book['bids']
        ask_side_book = book['asks']
        
        bid_prices_book = [item["price"] for item in bid_side_book]
        ask_prices_book = [item['price'] for item in ask_side_book]
        
        best_bid_price = bid_prices_book[0]
        best_ask_price = ask_prices_book[0]
  
        return best_bid_price, best_ask_price

def get_time_sales(ticker):
    payload = {'ticker': ticker}
    resp = s.get ('http://localhost:9999/v1/securities/tas', params = payload)
    if resp.ok:
        book = resp.json()
        time_sales_book = [item["quantity"] for item in book]
        return time_sales_book

def get_position():
    resp = s.get ('http://localhost:9999/v1/securities')
    if resp.ok:
        book = resp.json()
        gross_position = abs(book[1]['position']) + abs(book[2]['position']) + 2 * abs(book[3]['position'])
        net_position = book[1]['position'] + book[2]['position'] + 2 * book[3]['position']
        return gross_position, net_position


# New function
def get_vol_asset(asset_index):
    resp = s.get ('http://localhost:9999/v1/securities')
    if resp.ok:
        book = resp.json()
        return book[asset_index]['position']


def get_open_orders(ticker):
    payload = {'ticker': ticker}
    resp = s.get ('http://localhost:9999/v1/orders', params = payload)
    if resp.ok:
        orders = resp.json()
        buy_orders = [item for item in orders if item["action"] == "BUY"]
        sell_orders = [item for item in orders if item["action"] == "SELL"]
        return buy_orders, sell_orders

def get_order_status(order_id):
    resp = s.get ('http://localhost:9999/v1/orders' + '/' + str(order_id))
    if resp.ok:
        order = resp.json()
        return order['status']
    

# New function
def create_etf(vol_rgld, vol_rfin, id_creation):
    resp = s.post(f'http://localhost:9999/v1/leases/{id_creation}', params={'from1': 'RGLD', 'quantity1': vol_rgld, 'from2': 'RFIN', 'quantity2': vol_rfin})
    #if resp.ok:
        #print(f"ETF Created: {resp.json()}")

# New function
def redeem_etf(vol_indx, vol_cad, id_redemption):
    resp = s.post(f'http://localhost:9999/v1/leases/{id_redemption}', params={'from1': 'INDX', 'quantity1': vol_indx, 'from2': 'CAD', 'quantity2': vol_cad})
    #if resp.ok:
        #print(f"ETF Redeemed: {resp.json()}")


def get_lease():
    resp = s.post('http://localhost:9999/v1/leases', params = {'ticker': 'ETF-Creation'})
    resp = s.post('http://localhost:9999/v1/leases', params = {'ticker': 'ETF-Redemption'})
    resp = s.get('http://localhost:9999/v1/leases')
    leases = resp.json()
    id_creation = 0
    id_redemption = 0

    for lease in leases:
        if lease['ticker'] == 'ETF-Creation':
            id_creation = lease['id']
        if lease['ticker'] == 'ETF-Redemption':
            id_redemption = lease['id']
    return id_creation, id_redemption

def get_data():
    tick, status = get_tick()
    ticker_list = ['RGLD','RFIN','INDX']
    data = {"Tick":[],"Ticker":[],"Bid":[],"Ask":[],"Spread":[],"Price Change (-5)":[],"Price Change (-10)":[]}

    market_prices = np.array([0.,0.,0.,0.,0.,0.])
    market_prices = market_prices.reshape(3,2)
    market_prices_5 = np.array([0.,0.,0.,0.,0.,0.])
    market_prices_5 = market_prices.reshape(3,2)
    market_prices_10 = np.array([0.,0.,0.,0.,0.,0.])
    market_prices_10 = market_prices.reshape(3,2)
    while status == 'ACTIVE':
        for i in range(3):
            
            ticker_symbol = ticker_list[i]
            market_prices[i,0], market_prices[i,1] = get_bid_ask(ticker_symbol)      
        data["Tick"].append(tick)
        data["Ticker"].append("RGLD")
        data["Bid"].append(market_prices[0,0])
        data["Ask"].append(market_prices[0,1])
        data["Spread"].append(market_prices[0, 0] + market_prices[1, 0] - market_prices[2, 1])
        data["Tick"].append(tick)
        data["Ticker"].append("RFIN")
        data["Bid"].append(market_prices[1,0])
        data["Ask"].append(market_prices[1,1])
        data["Spread"].append(market_prices[0, 0] + market_prices[1, 0] - market_prices[2, 1])
        data["Ticker"].append("INDX")
        data["Bid"].append(market_prices[2,0])
        data["Ask"].append(market_prices[2,1])
        data["Spread"].append(market_prices[0, 0] + market_prices[1, 0] - market_prices[2, 1])

        sleep(1)

        # resp = s.get ('http://localhost:9999/v1/securities')
        # if resp.ok:
        #     book = resp.json()
        #     for index in range(len(book)):
        #         if book[index]["ticker"] in ticker_list:
        #             ticker = book[index]["ticker"]
        #             price = (book[index]["bid"] - book[index]["ask"])/2
                    


if __name__ == "__main__":
    get_data()