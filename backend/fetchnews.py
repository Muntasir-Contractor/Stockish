
import yfinance as yf

# How can i fetch news from CNBC????

# FUTURE IMPLEMENTATION, fetch summary alongside title for better sentiment analysis, costs more tokens tho

def get_ticker_newss(ticker):
    stock = yf.Ticker(ticker)
    news_data = stock.news
    news = []
    for idx in range(1,(min(len(news_data), 6))):
        news.append({"Headline": news_data[idx]['content']['title'],
                     "Summary": news_data[idx]['content']['summary']})
        
    return news

def news_toString(news : list[dict]):
    string_news = ""
    for idx,news_data in enumerate(news):
        string_news += f"{idx}. Headline: '{news_data["Headline"]}' \n Summary: '{news_data['Summary']}' \n \n"
    
    return string_news
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

if __name__ == "__main__":
    news = get_ticker_newss("NVDA")
    new_news = news_toString(news)
    print(new_news)