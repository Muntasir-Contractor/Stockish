import pandas as pd


df = pd.read_csv('dataset/model_data_new.csv')

#The coloumns that need outlier clipping
ratio_cols = ['Gross_Profitability', 'ROIC', 'FCF_Yield','Revenue_Growth_YoY','Momentum_6M',] #Forward_1yr_Return

for col in ratio_cols:
    # Find the 1st percentile (bottom 1%) and 99th percentile (top 1%)
    lower_bound = df[col].quantile(0.01)
    upper_bound = df[col].quantile(0.99)
    
    # Clip the data to stay within these normal bounds
    df[col] = df[col].clip(lower=lower_bound, upper=upper_bound)

print("Outliers Successfully Clipped!")

df.to_csv('dataset/model_data_new_cleaned.csv', index=False)
print("Cleaned dataset saved as 'model_data_new_cleaned.csv'")