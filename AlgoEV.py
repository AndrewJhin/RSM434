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

# Constants for each category
CONSTANTS = {
    "TP": {"div_payout": 0.80, "discount_rate": 0.05, "growth_divisor": 1.43, "pe_ratio": 12, "terminal_growth": 0.02},
    "AS": {"div_payout": 0.50, "discount_rate": 0.075, "growth_divisor": 1.55, "pe_ratio": 16, "terminal_growth": 0.02},
    "BA": {"growth_divisor": 1.50, "pe_ratio": 20}  # BA has a different formula, so no div_payout or discount_rate
}

OWNERSHIP_ERROR = {"TP":0.2,"AS":0.25,"BA":0.30} # Decreases by 5% each quarter
EPS_ERROR = {"TP":[0.02, 0.04, 0.06, 0.08],"AS":[0.04, 0.08, 0.12, 0.16],"BA":[0.06, 0.12, 0.18, 0.24]}

QUARTERS = {(0,59):(0,0),(60,119):(0,1),(120,179):(1,2),(180,239):(2,3),(240,300):(3,4)}

VALUES = {"TP":[None,None,None],"AS":[None,None,None],"BA":[None,None,None]}

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

def get_quarter(tick):
    for (start, end), value in QUARTERS.items():
        if start <= tick <= end:
            return value
    return None  # Return None if tick is out of range

def calculate_errors(tick):
    errors = get_quarter(tick)
    owne = errors[0]
    epse = errors[1]
    return {key: [0] * owne + value if owne == 0 else [0] * owne + value[:-owne] for key, value in EPS_ERROR.items()}, {key: value - epse * 0.05 for key, value in OWNERSHIP_ERROR.items()}
    

def get_news(own,eps,prev_size,tick):
    resp = s.get ('http://localhost:9999/v1/news', params = {'limit': 50}) # default limit is 20
    if resp.ok:
        news_query = resp.json()
        if len(news_query) > prev_size:
            #print(len(news_query) - prev_size)
            for index in range(len(news_query) - prev_size -1, -1, -1):
                #print(news_query[index]["headline"])
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

                    mid, min, max = get_valuation(ticker,own,eps,tick)
                    VALUES[ticker] = [mid, min, max]
                    print(VALUES)
                    # print("Updated EPS Table")
                    # print(eps)

                elif "Earnings release" in news_query[index]["headline"]:
                    parse = news_query[index]["body"].split("<br>")
                    for eps_news in parse:
                        news = eps_news.split()
                        eps[news[0]][int(news[1].replace("Q","").replace(":",""))-1] = float(news[-1].replace("$",""))
                    for ticker in TICKERS:
                        mid, min, max = get_valuation(ticker,own,eps,tick)
                        VALUES[ticker] = [mid, min, max]
                    print(VALUES)
                    # print("Updated EPS Table")
                    # print(eps)

                elif "institution" in news_query[index]["headline"]:
                    ticker = re.search(r'[A-Z]{2}',news_query[index]["body"])
                    value = re.search(r'\d{1,2}\.\d{1,2}\%',news_query[index]["body"])
                    own[ticker.group(0)] = float(value.group(0).replace("%",""))
                    for ticker in TICKERS:
                        mid, min, max = get_valuation(ticker,own,eps,tick)
                        VALUES[ticker] = [mid, min, max]
                    print(VALUES)
                    # print("Updated Ownership Table")
                    # print(own)
                    
            return own, eps, len(news_query)
        else:
            return own, eps, prev_size

def get_valuation(category, OWNERSHIP, EPS_ESTIMATES, tick):
    if category not in CONSTANTS:
        raise ValueError(f"Invalid category: {category}")

    constants = CONSTANTS[category]
    eps = sum(EPS_ESTIMATES[category])
    ownership = OWNERSHIP[category]

    eps_e, ownership_e = calculate_errors(tick)
    ownership_e = ownership_e[category]
    eps_e = eps_e[category]

    def calculate_value(eps_value, ownership_value):
        """ Calculate valuation based on EPS and ownership values. """
        g = (eps_value / constants["growth_divisor"]) - 1

        if category == "BA":
            # BA uses a different valuation model (Institutional vs. Retail PE)
            pe_inst = constants["pe_ratio"] * (1 + g) * eps_value
            pe_retail = eps_value * constants["pe_ratio"]
            if pe_inst < pe_retail:
                ownership_value *= (1 + ownership_e)
            else:
                ownership_value *= (1 - ownership_e)
            return (ownership_value / 100) * pe_inst + (1 - (ownership_value / 100)) * pe_retail

        else:
            # TP and AS use DDM + PE Model
            div = eps_value * constants["div_payout"]
            DDM = ((div * (1 + g)) / (constants["discount_rate"] - g)) * \
                  (1 - ((1 + g) / (1 + constants["discount_rate"])) ** 5) + \
                  ((div * ((1 + g) ** 5) * (1 + constants["terminal_growth"])) /
                   (constants["discount_rate"] - constants["terminal_growth"])) / ((1 + constants["discount_rate"]) ** 5)

            pe = eps_value * constants["pe_ratio"]
            if DDM < pe:
                ownership_value *= (1 + ownership_e)
            else:
                ownership_value *= (1 - ownership_e)

            return (ownership_value / 100) * DDM + (1 - (ownership_value / 100)) * pe

    # Compute values for midpoint, min, and max scenarios
    mid_val = calculate_value(eps, ownership)
    min_val = calculate_value(sum(np.add(EPS_ESTIMATES[category], -1 * np.array(eps_e))), ownership)
    max_val = calculate_value(sum(np.add(EPS_ESTIMATES[category], eps_e)), ownership)

    return round(mid_val, 2), round(min_val, 2), round(max_val, 2)

if __name__ == "__main__":
    tick, status = get_tick()
    default_size = 0
    while status == "ACTIVE":
        OWNERSHIP, EPS, default_size = get_news(OWNERSHIP, EPS,default_size,tick)
        """
        PUT A MAIN FUNCTION HERE USING THE VALUES FROM NEWS
        
        FINAL SETTLEMENT NOT IMPLEMENTED YET

        CURRENTLY UPDATING GLOBAL VARIABLES AND PRINTING EVERY UPDATE
        """
        sleep(0.5)
        tick, status = get_tick()
        
        

