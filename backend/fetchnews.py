
import yfinance as yf

# How can i fetch news from CNBC????

def get_ticker_news(ticker):
    """
    Get news for specific stocks via Yahoo Finance
    """
    stock = yf.Ticker(ticker)
    news = stock.news

    res_prompt = ""
    
    for idx,article in enumerate(news[:10]):
        ######
        # article_date_published = article["content"]["pubDate"]
        # only consider the news if it is within 7 days
        #####
        res_prompt += f"\nHeadline {idx+1}. {article["content"]["title"]}"
    
    return res_prompt

"""
load_dotenv()
finnhub_api_key = os.getenv("FINNHUB_KEY")
def get_news(api_key=finnhub_api_key,category='general'):
    finnhub_client = finnhub.Client(finnhub_api_key)
    news = finnhub_client(category,min_id=0)
    res_prompt = ""
    for idx, article in enumerate(news[:10]):
        res_prompt += f"{idx+1}. {article['headline']}"
    
    return res_prompt

"""

"""
load_dotenv()
API_KEY = os.getenv("NEWS_API_KEY")

newsapi = NewsApiClient(API_KEY)

top_headlines = newsapi.get_top_headlines(
    country="us",
    category="business",
    page_size=10
)

articles = newsapi.get_everything(
    q="Nvidia",
    language="en",
    sort_by="publishedAt",
    page_size=10

)
headlines = top_headlines["articles"]
list_of_headlines = []
for headline in headlines:
    list_of_headlines.append(headline["title"])

for headline in list_of_headlines:
    print(headline)
    print("-"*25)

#print(top_headlines["articles"][0]["title"])
#print(top_headlines)
#print(articles["totalResults"])
#print(articles)

#...
"""