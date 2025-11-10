import requests
from bs4 import BeautifulSoup

def create_link(ticker):
    return f"https://ca.finance.yahoo.com/quote/{ticker}/"

def scrape_stock(ticker):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36'}
        source = requests.get(create_link(ticker),headers=headers).text
    except:
        print("INVALID TICKER SYMBOL")
    
    soup = BeautifulSoup(source, 'lxml')

    #Get data such as price pe ratio expected return and else through soup
    def get_value(data):
        pass
    
    data = {
        "Ticker": ticker

    }

scrape_stock(create_link("MSFT"))


