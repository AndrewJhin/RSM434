import requests
import time

# Initialize API session
s = requests.Session()
s.headers.update({'X-API-key': '149E22H1'})

# Parameters
MAX_POSITION = 25000
LOT_SIZE = 500
SECURITIES = ['CNR', 'ALG', 'AC']

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

def market_making():
    """Main market-making loop."""
    while True:
        for ticker in SECURITIES:
            best_bid, best_ask = fetch_bid_ask(ticker)
            if best_bid and best_ask:
                spread = best_ask - best_bid
                if spread > 0.02:  # Minimum profitable spread
                    place_order(ticker, 'BUY', best_bid, LOT_SIZE)
                    place_order(ticker, 'SELL', best_ask, LOT_SIZE)
        
        total_position = manage_inventory()
        if total_position > MAX_POSITION:
            print("Inventory limit exceeded. Adjusting positions...")
            # Implement position reduction logic here
        
        time.sleep(1)  # Adjust frequency to avoid overloading the API

# Run the strategy
market_making()
