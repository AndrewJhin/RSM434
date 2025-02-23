import requests
from time import sleep
import numpy as np
import re

# Initialize API session
s = requests.Session()
s.headers.update({'X-API-key': 'P0U2IVMW'})  # Use your actual API Key

# Constants
TICKERS = ["TP", "AS", "BA"]
MAX_NET_POSITION = 50000
MAX_GROSS_POSITION = 100000
ORDER_SIZE = 10000  # Max allowed order size

EPS = {"TP":[0.4,0.33,0.33,0.37],"AS":[0.35,0.45,0.5,0.25],"BA":[0.15,0.5,0.6,0.25]}
#EPS_VALUES = {"TP":[0,0,0,0],"AS":[0,0,0,0],"BA":[0,0,0,0]}
OWNERSHIP = {"TP":0,"AS":0,"BA":0}



def get_tick():
    resp = s.get('http://localhost:9999/v1/case')
    if resp.ok:
        case = resp.json()
        return case['tick'], case['status']
    
# Fetch Market Data
def get_bid_ask(ticker):
    resp = s.get("http://localhost:9999/v1/securities/book", params={"ticker": ticker})
    if resp.ok:
        book = resp.json()
        best_bid = book["bids"][0]["price"] if book["bids"] else None
        best_ask = book["asks"][0]["price"] if book["asks"] else None
        return best_bid, best_ask
    return None, None

# Fetch Position Data
def get_position(ticker):
    resp = s.get("http://localhost:9999/v1/securities")
    if resp.ok:
        for stock in resp.json():
            if stock["ticker"] == ticker:
                return stock["position"]
    return 0


def get_news(own,eps,prev_size):
    resp = s.get ('http://localhost:9999/v1/news', params = {'limit': 50}) # default limit is 20
    if resp.ok:
        news_query = resp.json()
        if len(news_query) > prev_size:
            #print(len(news_query) - prev_size)
            for index in range(len(news_query) - prev_size -1, -1, -1):
                print(news_query[index]["headline"])
                if "Earnings Estimates" in news_query[index]["headline"]:
                    eps_values = [float(match.group().split("$")[1]) for match in re.finditer(r'Q\d:\s\$\d\.\d{2}', news_query[index]["body"])]

                    # Extract quarter index and ticker
                    quarter_match = re.search(r'#(\d+)', news_query[index]["headline"])
                    ticker = news_query[index]["headline"].split()[0]

                    if quarter_match and ticker in eps:
                        quarter_index = int(quarter_match.group(1)) - 1  # Convert to zero-based index
                        # Ensure we don't go out of bounds
                        for i, new_value in enumerate(eps_values):
                            if quarter_index + i < len(eps[ticker]):
                                eps[ticker][quarter_index + i] = new_value
                    print("Updated EPS Table")
                    print(eps)

                elif "Earnings release" in news_query[index]["headline"]:
                    parse = news_query[index]["body"].split("<br>")
                    for eps_news in parse:
                        news = eps_news.split()
                        eps[news[0]][int(news[1].replace("Q","").replace(":",""))-1] = float(news[-1].replace("$",""))
                    print("Updated EPS Table")
                    print(eps)

                elif "institution" in news_query[index]["headline"]:
                    ticker = re.search(r'[A-Z]{2}',news_query[index]["body"])
                    value = re.search(r'\d{1,2}\.\d{1,2}\%',news_query[index]["body"])
                    own[ticker.group(0)] = float(value.group(0).replace("%",""))
                    print("Updated Ownership Table")
                    print(own)
                    
            return own, eps, len(news_query)
        else:
            return own, eps, prev_size


if __name__ == "__main__":
    tick, status = get_tick()
    default_size = 0
    while status == "ACTIVE":
        OWNERSHIP, EPS, default_size = get_news(OWNERSHIP, EPS,default_size)
        """
        PUT A MAIN FUNCTION HERE USING THE VALUES FROM NEWS
        
        FINAL SETTLEMENT NOT IMPLEMENTED YET

        CURRENTLY UPDATING GLOBAL VARIABLES AND PRINTING EVERY UPDATE
        """
        sleep(0.5)
        tick, status = get_tick()
        
        

