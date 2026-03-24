import pandas as pd
import joblib
from train_forwardreturn_model import X_test,test_df, y_test
from sklearn.metrics import confusion_matrix



model = joblib.load(r"model/XGBoost_newestfr_model.joblib")

test_df = test_df.copy()
test_df['Predicted_Decile'] = model.predict(X_test)

print("Finished predicting")

def confusionMatrix():
    y_pred = test_df['Predicted_Decile']
    matrix = confusion_matrix(y_test, y_pred,labels=list(range(10)))
    print(matrix)


RISK_FREE_RATE = 0.04  # the rfr hovered between  3.5-4.5% throughout the 2023-2024 year

portfolio = test_df[test_df['Predicted_Decile'] == 9]
portfolio_return = portfolio['Forward_1yr_Return'].mean()
average_market_return = test_df['Forward_1yr_Return'].mean()
portfolio_median = portfolio['Forward_1yr_Return'].median()
min = portfolio['Forward_1yr_Return'].min()
maxx = portfolio['Forward_1yr_Return'].max()

portfolio_std = portfolio['Forward_1yr_Return'].std()
sharpe = (portfolio_return - RISK_FREE_RATE) / portfolio_std if portfolio_std else None

market_std = test_df['Forward_1yr_Return'].std()
market_sharpe = (average_market_return - RISK_FREE_RATE) / market_std if market_std else None


for index,row in portfolio.iterrows():
    print(f"{row["Ticker"]} Bought, Predicted: {row["Predicted_Decile"]}, Actual Return: {row["Forward_1yr_Return"]*100:.2f}% , Actual Target: {row["y_target"]}")
print(f"Average Market Return (Benchmark):  {average_market_return * 100:.2f}%")
print(f"Model's 'Strong Buy' Return:        {portfolio_return * 100:.2f}%  <-- (Did we beat the market?)")
print(f"Median Return: {portfolio_median*100:.2f}")
print(f"Max Return: {maxx*100:.2f}")
print(f"Min Return: {min*100:.2f}")
print(f"Portfolio Sharpe Ratio:             {sharpe:.4f}" if sharpe is not None else "Portfolio Sharpe Ratio: N/A")
print(f"Benchmark Sharpe Ratio:             {market_sharpe:.4f}" if market_sharpe is not None else "Benchmark Sharpe Ratio: N/A")


print("-" * 50)
print(f"Number of Stocks Bought:  {len(portfolio)}")

confusionMatrix()