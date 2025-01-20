import requests
import time
import collections
import numpy as np

# Initialize API session
s = requests.Session()
s.headers.update({'X-API-key': '149E22H1'})

# Parameters
LOT_SIZE = 1000
MAX_POSITION = 25000 - LOT_SIZE
SECURITIES = ['CNR', 'RY', 'AC']

# Parameters for dynamic spread adjustment
VOLATILITY_WINDOW = 10  # Number of ticks to calculate volatility
HIGH_VOLATILITY_THRESHOLD = 0.05  # Spread threshold for high volatility
LOW_VOLATILITY_THRESHOLD = 0.02  # Spread threshold for low volatility

# Store recent spreads for volatility calculation
recent_spreads = collections.deque(maxlen=VOLATILITY_WINDOW)

def calculate_volatility():
    """Calculate market volatility based on recent spreads."""
    if len(recent_spreads) < VOLATILITY_WINDOW:
        return 0  # Insufficient data to calculate volatility
    return np.std(recent_spreads)

def get_dynamic_spread(volatility):
    """Determine the dynamic spread threshold based on volatility."""
    if volatility > HIGH_VOLATILITY_THRESHOLD:
        return 0.05  # Higher spread for volatile markets
    else:
        return 0.02  # Lower spread for stable markets

def fetch_bid_ask(ticker):
    """Fetch best bid and ask prices for a given security."""
    resp = s.get(f'http://localhost:9999/v1/securities/book?ticker={ticker}')
    if resp.ok:
        data = resp.json()
        return data['bids'][0]['price'], data['asks'][0]['price']
    return None, None

def place_order(ticker, action, price, quantity=LOT_SIZE):
    """Place a limit order."""
    return s.post('http://localhost:9999/v1/orders', params={
        'ticker': ticker,
        'type': 'LIMIT',
        'quantity': quantity,
        'price': price,
        'action': action
    })

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

def market_making():
    """Main market-making loop with position reduction logic."""
    while True:
        for ticker in SECURITIES:
            best_bid, best_ask = fetch_bid_ask(ticker)
            if best_bid and best_ask:
                spread = best_ask - best_bid
                if spread > 0.03:  # Minimum profitable spread
                    place_order(ticker, 'BUY', best_bid, LOT_SIZE)
                    place_order(ticker, 'SELL', best_ask, LOT_SIZE)
        
        total_position = manage_inventory()
        if total_position > MAX_POSITION:
            print("Inventory limit exceeded. Reducing positions...")
            reduce_positions()
        
        time.sleep(1)  # Adjust frequency to avoid overloading the API

def market_making_with_dynamic_spread():
    """Main market-making loop with dynamic spread adjustment."""
    while True:
        for ticker in SECURITIES:
            best_bid, best_ask = fetch_bid_ask(ticker)
            if best_bid and best_ask:
                spread = best_ask - best_bid
                recent_spreads.append(spread)  # Track recent spreads
                
                # Calculate market volatility and determine the spread threshold
                volatility = calculate_volatility()
                min_spread = get_dynamic_spread(volatility)
                
                if spread > min_spread:
                    print(f"Placing orders for {ticker} with spread: {spread:.4f}")
                    place_order(ticker, 'BUY', best_bid, LOT_SIZE)
                    place_order(ticker, 'SELL', best_ask, LOT_SIZE)
        
        total_position = manage_inventory()
        if total_position > MAX_POSITION:
            print("Inventory limit exceeded. Reducing positions...")
            reduce_positions()
        
        time.sleep(1)  # Adjust frequency to avoid overloading the API

# Run the strategy
#market_making()
market_making_with_dynamic_spread()
