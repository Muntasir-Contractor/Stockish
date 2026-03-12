import pandas as pd
import joblib
from train_forwardreturn_model import X_test,test_df, y_test

model = joblib.load(r"model/XGBoost_fr_model.joblib")

test_df = test_df.copy()
test_df['Predicted_Decile'] = model.predict(X_test)

print("Finished predicting")

portfolio = test_df[test_df['Predicted_Decile'] == 9]
portfolio_return = portfolio['Forward_1yr_Return'].mean()
average_market_return = test_df['Forward_1yr_Return'].mean()
portfolio_median = portfolio['Forward_1yr_Return'].median()
min = portfolio['Forward_1yr_Return'].min()
maxx = portfolio['Forward_1yr_Return'].max()

for index,row in portfolio.iterrows():
    print(f"{row["Ticker"]} Bought, Predicted: {row["Predicted_Decile"]}, Actual Return: {row["Forward_1yr_Return"]*100:.2f}% Sector: {row["Sector_Basic"]}")

print(f"Average Market Return (Benchmark):  {average_market_return * 100:.2f}%")
print(f"Model's 'Strong Buy' Return:        {portfolio_return * 100:.2f}%  <-- (Did we beat the market?)")
print(f"Median Return: {portfolio_median*100:.2f}")
print(f"Max Return: {maxx*100:.2f}")
print(f"Min Return: {min*100:.2f}")


print("-" * 50)
print(f"Number of Stocks Bought:  {len(portfolio)}")

