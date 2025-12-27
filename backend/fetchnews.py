from newsapi import NewsApiClient
import os
from dotenv import load_dotenv

# How can i fetch news from CNBC????

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