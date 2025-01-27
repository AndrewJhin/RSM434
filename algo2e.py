import requests
import time
import numpy as np

# Initialize API session
s = requests.Session()
s.headers.update({'X-API-key': 'P0U2IVMW'})  # Replace with your actual API key

# Parameters
LOT_SIZE = 2500
MAX_POSITION = 25000
TIME_DELAY = 3
MIN_SPREAD = 0.025

SECURITIES = ['CNR', 'RY', 'AC']
order_tracking = {}  # To track orders and their creation ticks

# Utility Functions
def get_tick():
    """Fetch the current tick and status of the case."""
    resp = s.get('http://localhost:9999/v1/case')
    if resp.ok:
        case = resp.json()
        return case['tick'], case['status']
    else:
        print("Failed to fetch tick data.")
        return None, None

def fetch_bid_ask(ticker):
    """Fetch the best bid and ask prices for a given security."""
    resp = s.get(f'http://localhost:9999/v1/securities/book?ticker={ticker}')
    if resp.ok:
        book = resp.json()
        best_bid = book['bids'][0]['price'] if book['bids'] else None
        best_ask = book['asks'][0]['price'] if book['asks'] else None
        return best_bid, best_ask
    return None, None

def get_open_orders():
    """Fetch all open orders."""
    resp = s.get('http://localhost:9999/v1/orders')
    if resp.ok:
        return resp.json()
    return []

def place_order(ticker, action, price, quantity):
    """Place a limit order."""
    resp = s.post('http://localhost:9999/v1/orders', params={
        'ticker': ticker,
        'type': 'LIMIT',
        'quantity': quantity,
        'price': price,
        'action': action
    })
    if resp.ok:
        return resp
    else:
        print(f"Failed to place {action} order for {ticker} at {price}.")
        return None

def cancel_and_resubmit_orders(current_tick,time_delay):
    """Cancel orders older than 20 ticks and resubmit unfulfilled portions."""
    global order_tracking
    open_orders = get_open_orders()

    for order in open_orders:
        order_id = order['order_id']
        order_tick = order_tracking.get(order_id, None)
        ticker = order['ticker']
        action = order['action']
        price = order['price']
        unfilled_quantity = order['quantity'] - order['quantity_filled']

        if order_tick and current_tick - order_tick > time_delay:
            print(f"Canceling and resubmitting order {order_id} (age: {current_tick - order_tick} ticks)")
            s.delete(f'http://localhost:9999/v1/orders/{order_id}')
            order_tracking.pop(order_id, None)

            if unfilled_quantity > 0:
                # Fetch updated bid/ask prices for resubmitting
                best_bid, best_ask = fetch_bid_ask(ticker)
                new_price = best_bid if action == 'BUY' else best_ask

                if new_price:
                    resp = place_order(ticker, action, new_price, unfilled_quantity)
                    if resp and resp.ok:
                        new_order_id = resp.json()['order_id']
                        order_tracking[new_order_id] = current_tick

def manage_inventory():
    """Monitor and manage inventory levels."""
    resp = s.get('http://localhost:9999/v1/securities')
    if resp.ok:
        data = resp.json()
        total_position = sum(abs(item['position']) for item in data)
        return total_position
    return 0

def reduce_positions():
    """Reduce inventory to stay within limits."""
    resp = s.get('http://localhost:9999/v1/securities')
    if resp.ok:
        data = resp.json()
        for security in data:
            ticker = security['ticker']
            position = security['position']

            if position > 0:
                # Sell excess long positions
                print(f"Reducing long position for {ticker}: {position} shares")
                best_bid, _ = fetch_bid_ask(ticker)
                if best_bid:
                    sell_quantity = min(position, LOT_SIZE)
                    place_order(ticker, 'SELL', best_bid, sell_quantity)
            elif position < 0:
                # Buy to cover short positions
                print(f"Reducing short position for {ticker}: {position} shares")
                _, best_ask = fetch_bid_ask(ticker)
                if best_ask:
                    buy_quantity = min(abs(position), LOT_SIZE)
                    place_order(ticker, 'BUY', best_ask, buy_quantity)

# Main Market-Making Logic
def market_making(lot_size,time_delay,min_spread):
    """Main market-making loop with canceling and resubmitting logic."""
    while True:
        current_tick, status = get_tick()
        if status != 'ACTIVE':
            print("Case has ended. Stopping trading...")
            profit = s.get(f'http://localhost:9999/v1/trader')
            if profit.ok:
                profit = profit.json()
                print(profit['nlv'])

        # Place new orders
        for ticker in SECURITIES:
            best_bid, best_ask = fetch_bid_ask(ticker)
            if best_bid and best_ask:
                spread = best_ask - best_bid
                if spread > min_spread:  # Fixed minimum spread
                    print(f"Placing orders for {ticker} with spread: {spread:.4f}")

                    # Place BUY order
                    buy_resp = place_order(ticker, 'BUY', best_bid, lot_size)
                    if buy_resp and buy_resp.ok:
                        order_id = buy_resp.json()['order_id']
                        order_tracking[order_id] = current_tick

                    # Place SELL order
                    sell_resp = place_order(ticker, 'SELL', best_ask, lot_size)
                    if sell_resp and sell_resp.ok:
                        order_id = sell_resp.json()['order_id']
                        order_tracking[order_id] = current_tick

        # Cancel and resubmit old orders
        cancel_and_resubmit_orders(current_tick,time_delay)

        # Manage inventory limits
        total_position = manage_inventory()
        if total_position > MAX_POSITION:
            print("Inventory limit exceeded. Reducing positions...")
            reduce_positions()

        time.sleep(1)  # Adjust frequency to avoid overloading the API

if __name__ == "__main__":
    market_making(LOT_SIZE,TIME_DELAY,MIN_SPREAD)



# import requests
# import time
# import numpy as np

# # Initialize API session
# s = requests.Session()
# s.headers.update({'X-API-key': 'P0U2IVMW'})  # Replace with your actual API key

# # Parameters
# LOT_SIZE = 1000
# MAX_POSITION = 25000 - LOT_SIZE
# SECURITIES = ['CNR', 'RY', 'AC']
# order_tracking = {}  # To track orders and their creation ticks

# # Utility Functions
# def get_tick():
#     """Fetch the current tick and status of the case."""
#     resp = s.get('http://localhost:9999/v1/case')
#     if resp.ok:
#         case = resp.json()
#         return case['tick'], case['status']
#     else:
#         print("Failed to fetch tick data.")
#         return None, None

# def fetch_bid_ask(ticker):
#     """Fetch the best bid and ask prices for a given security."""
#     resp = s.get(f'http://localhost:9999/v1/securities/book?ticker={ticker}')
#     if resp.ok:
#         book = resp.json()
#         best_bid = book['bids'][0]['price'] if book['bids'] else None
#         best_ask = book['asks'][0]['price'] if book['asks'] else None
#         return best_bid, best_ask
#     return None, None

# def get_open_orders():
#     """Fetch all open orders."""
#     resp = s.get('http://localhost:9999/v1/orders')
#     if resp.ok:
#         return resp.json()
#     return []

# def place_order(ticker, action, price, quantity=LOT_SIZE):
#     """Place a limit order."""
#     resp = s.post('http://localhost:9999/v1/orders', params={
#         'ticker': ticker,
#         'type': 'LIMIT',
#         'quantity': quantity,
#         'price': price,
#         'action': action
#     })
#     if resp.ok:
#         return resp
#     else:
#         print(f"Failed to place {action} order for {ticker} at {price}.")
#         return None

# def manage_inventory():
#     """Monitor and manage inventory levels."""
#     resp = s.get('http://localhost:9999/v1/securities')
#     if resp.ok:
#         data = resp.json()
#         total_position = sum(abs(item['position']) for item in data)
#         return total_position
#     return 0

# def reduce_positions():
#     """Reduce inventory to stay within limits."""
#     resp = s.get('http://localhost:9999/v1/securities')
#     if resp.ok:
#         data = resp.json()
#         for security in data:
#             ticker = security['ticker']
#             position = security['position']
            
#             if position > 0:
#                 # Sell excess long positions
#                 print(f"Reducing long position for {ticker}: {position} shares")
#                 best_bid, _ = fetch_bid_ask(ticker)
#                 if best_bid:
#                     sell_quantity = min(position, LOT_SIZE)
#                     place_order(ticker, 'SELL', best_bid, sell_quantity)
#             elif position < 0:
#                 # Buy to cover short positions
#                 print(f"Reducing short position for {ticker}: {position} shares")
#                 _, best_ask = fetch_bid_ask(ticker)
#                 if best_ask:
#                     buy_quantity = min(abs(position), LOT_SIZE)
#                     place_order(ticker, 'BUY', best_ask, buy_quantity)

# def cancel_old_orders(current_tick):
#     """Cancel orders older than 20 ticks."""
#     global order_tracking
#     open_orders = get_open_orders()
#     for order in open_orders:
#         order_id = order['order_id']
#         order_tick = order_tracking.get(order_id, None)
        
#         if order_tick and current_tick - order_tick > 20:
#             print(f"Canceling order {order_id} (age: {current_tick - order_tick} ticks)")
#             s.delete(f'http://localhost:9999/v1/orders/{order_id}')
#             order_tracking.pop(order_id, None)

# # Main Market-Making Logic
# def market_making():
#     """Main market-making loop with fixed spread and order cancellation logic."""
#     while True:
#         current_tick, status = get_tick()
#         if status != 'ACTIVE':
#             print("Case has ended. Stopping trading...")
#             profit = s.get(f'http://localhost:9999/v1/trader')
#             if profit.ok:
#                 profit = profit.json()
#                 print(profit['nlv'])

#             #break

#         # Place new orders
#         for ticker in SECURITIES:
#             best_bid, best_ask = fetch_bid_ask(ticker)
#             if best_bid and best_ask:
#                 spread = best_ask - best_bid
#                 if spread > 0.1:  # Fixed minimum spread
#                     print(f"Placing orders for {ticker} with spread: {spread:.4f}")
                    
#                     # Place BUY order
#                     buy_resp = place_order(ticker, 'BUY', best_bid, LOT_SIZE)
#                     if buy_resp and buy_resp.ok:
#                         order_id = buy_resp.json()['order_id']
#                         order_tracking[order_id] = current_tick
                    
#                     # Place SELL order
#                     sell_resp = place_order(ticker, 'SELL', best_ask, LOT_SIZE)
#                     if sell_resp and sell_resp.ok:
#                         order_id = sell_resp.json()['order_id']
#                         order_tracking[order_id] = current_tick
        
#         # Cancel old orders
#         cancel_old_orders(current_tick)
#         # Manage inventory limits
#         total_position = manage_inventory()
#         if total_position > MAX_POSITION:
#             print("Inventory limit exceeded. Reducing positions...")
#             reduce_positions()
        
#         time.sleep(1)  # Adjust frequency to avoid overloading the API

# def get_time_sales(ticker):
#     payload = {'ticker': ticker}
#     resp = s.get ('http://localhost:9999/v1/securities/tas', params = payload)
#     if resp.ok:
#         book = resp.json()
#         time_sales_book = [item["quantity"] for item in book]
#         return time_sales_book

# def calculate_dynamic_spread(ticker):
#     """Calculate a dynamic spread based on market conditions."""
#     recent_trades = get_time_sales(ticker)
#     if not recent_trades:
#         return 0.05  # Default spread when no data is available

#     # Compute average and standard deviation of trade volumes
#     average_trade_volume = np.mean(recent_trades)
#     trade_volatility = np.std(recent_trades)

#     # Adjust spread using both average and volatility
#     dynamic_spread = average_trade_volume / 5000 + trade_volatility / 1000

#     # Limit spread within a reasonable range
#     return max(0.02, min(0.075, dynamic_spread))

# def dynamic_market_making():
#     """Market-making strategy with dynamically adjusted spreads."""
#     while True:
#         current_tick, status = get_tick()
#         if status != 'ACTIVE':
#             print("Case has ended. Stopping trading...")
#             #break

#         for ticker in SECURITIES:
#             best_bid, best_ask = fetch_bid_ask(ticker)
#             if best_bid and best_ask:
#                 spread = calculate_dynamic_spread(ticker)
#                 mid_price = (best_bid + best_ask) / 2
#                 buy_price = round(mid_price - spread / 2, 2)
#                 sell_price = round(mid_price + spread / 2, 2)

#                 print(f"{ticker}: Calculated spread = {spread:.4f}, "
#                       f"Buy Price = {buy_price}, Sell Price = {sell_price}")

#                 # Place dynamic buy order
#                 buy_resp = place_order(ticker, 'BUY', buy_price, LOT_SIZE)
#                 if buy_resp and buy_resp.ok:
#                     order_id = buy_resp.json()['order_id']
#                     order_tracking[order_id] = current_tick

#                 # Place dynamic sell order
#                 sell_resp = place_order(ticker, 'SELL', sell_price, LOT_SIZE)
#                 if sell_resp and sell_resp.ok:
#                     order_id = sell_resp.json()['order_id']
#                     order_tracking[order_id] = current_tick

#         # Cancel old orders
#         cancel_old_orders(current_tick)

#         # Manage inventory limits
#         total_position = manage_inventory()
#         if total_position > MAX_POSITION:
#             print("Inventory limit exceeded. Reducing positions...")
#             reduce_positions()

#         time.sleep(1)

# if __name__ == "__main__":
#     # Run the dynamic market-making strategy
#     #dynamic_market_making()

#     # # Run the strategy
#     market_making()