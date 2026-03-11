import simfin as sf
import pandas as pd
import warnings
import os
from dotenv import load_dotenv
env_path = r"backend\.env"


# Load that specific .env file
load_dotenv(dotenv_path=env_path)
SIMFIN = os.getenv("SIMFIN")
warnings.filterwarnings('ignore', category=FutureWarning)

# Set your local SimFin data directory
sf.set_api_key(SIMFIN)
sf.set_data_dir('~/simfin_data/')

print("1. Loading raw datasets...")
df_inc = sf.load_income(variant='quarterly').reset_index()
df_bal = sf.load_balance(variant='quarterly').reset_index()
df_cf  = sf.load_cashflow(variant='quarterly').reset_index()
df_prices = sf.load_shareprices(variant='daily').reset_index()
df_companies = sf.load_companies().reset_index()
df_industries = sf.load_industries().reset_index()
df_companies = df_companies.merge(df_industries[['IndustryId', 'Sector']], on='IndustryId', how='left')

print("2. Merging the 3 Accounting Statements...")
# Merge Income, Balance, and Cashflow on matching report identifiers
df_fundamentals = pd.merge(df_inc, df_bal, on=['Ticker', 'SimFinId', 'Fiscal Year', 'Fiscal Period', 'Report Date', 'Publish Date'], how='inner')
df_fundamentals = pd.merge(df_fundamentals, df_cf, on=['Ticker', 'SimFinId', 'Fiscal Year', 'Fiscal Period', 'Report Date', 'Publish Date'], how='inner')

# Add Sector info
df_fundamentals = pd.merge(df_fundamentals, df_companies[['Ticker', 'Sector']], on='Ticker', how='left')

print("3. Calculating Trailing Twelve Months (TTM) for Flow Metrics...")
# Sort chronologically by Ticker to ensure the rolling math is correct
df_fundamentals = df_fundamentals.sort_values(['Ticker', 'Report Date'])

# We need the sum of the last 4 quarters for these specific metrics
# (SimFin's standard cash flow columns usually provide 'Net Cash from Operating Activities' 
# and 'Change in Fixed Assets & Intangibles' which is CapEx. We calculate FCF first).
df_fundamentals['Free Cash Flow'] = df_fundamentals['Net Cash from Operating Activities'] + df_fundamentals['Change in Fixed Assets & Intangibles'].fillna(0)

flow_columns = ['Gross Profit', 'Operating Income (Loss)', 'Free Cash Flow']

for col in flow_columns:
    # Group by ticker, take a rolling window of 4 rows (4 quarters), and sum them
    df_fundamentals[f'{col}_TTM'] = df_fundamentals.groupby('Ticker')[col].transform(
        lambda x: x.rolling(window=4, min_periods=4).sum()
    )

# Drop rows that don't have a full year of history yet
df_fundamentals.dropna(subset=['Free Cash Flow_TTM'], inplace=True)

print("4. Merging Fundamentals with Daily Prices (Point-in-Time)...")
# Sort data by dates (MANDATORY for merge_asof to work)
df_fundamentals = df_fundamentals.sort_values('Publish Date')
df_prices = df_prices.sort_values('Date')

# Align the 'Publish Date' with the closest forward trading 'Date'
master_df = pd.merge_asof(
    df_fundamentals, 
    df_prices, 
    left_on='Publish Date', 
    right_on='Date', 
    by='Ticker', 
    direction='forward'
)

print(f"   master_df shape after price merge: {master_df.shape}")
print(f"   master_df Date null count: {master_df['Date'].isna().sum()}")
print("5. Engineering the Final Features (X)...")
# Calculate Market Cap and Invested Capital (Snapshot metrics)
master_df['Market_Cap'] = master_df['Close'] * master_df['Shares (Basic)']
master_df['Invested_Capital'] = master_df['Short Term Debt'].fillna(0) + master_df['Long Term Debt'].fillna(0) + master_df['Total Equity'].fillna(0)

# Calculate the actual Machine Learning Ratios using the TTM metrics!
master_df['Gross_Profitability'] = master_df['Gross Profit_TTM'] / master_df['Total Assets']
master_df['ROIC'] = master_df['Operating Income (Loss)_TTM'] / master_df['Invested_Capital']
master_df['FCF_Yield'] = master_df['Free Cash Flow_TTM'] / master_df['Market_Cap']

# Clean out division-by-zero or infinite values
master_df.replace([float('inf'), float('-inf')], pd.NA, inplace=True)

# Drop rows where no forward price was found (Date is NaT from the merge_asof above)
master_df = master_df.dropna(subset=['Date'])

print("6. Calculating the Target Variable (y)...")
# Map the future 5-year price backwards
future_prices = df_prices.copy()
future_prices['Date'] = future_prices['Date'] - pd.DateOffset(years=1)
future_prices = future_prices.rename(columns={'Close': 'Future_Close_1yr'})[['Ticker', 'Date', 'Future_Close_1yr']]

master_df = pd.merge_asof(
    master_df.sort_values('Date'), 
    future_prices.sort_values('Date'), 
    on='Date', 
    by='Ticker', 
    direction='forward'
)

# Calculate the 5-year return and cross-sectionally rank it
master_df['Forward_1yr_Return'] = (master_df['Future_Close_1yr'] / master_df['Close']) - 1
master_df['y_target'] = master_df.groupby('Date')['Forward_1yr_Return'].transform(
    lambda x: pd.qcut(x, q=10, labels=False, duplicates='drop')
)

print(f"   Forward_1yr_Return null count: {master_df['Forward_1yr_Return'].isna().sum()} / {len(master_df)}")
print(f"   y_target null count: {master_df['y_target'].isna().sum()} / {len(master_df)}")
print(f"   FCF_Yield null count: {master_df['FCF_Yield'].isna().sum()} / {len(master_df)}")
print(f"   Gross_Profitability null count: {master_df['Gross_Profitability'].isna().sum()} / {len(master_df)}")
print("7. Finalizing the Dataset & One-Hot Encoding Sectors...")
# Keep only the essential columns
final_columns = [
    'Ticker', 'Date', 'Sector', 
    'Gross_Profitability', 'ROIC', 'FCF_Yield', 
    'y_target' # Notice we dropped the raw return, the model only needs the decile target
]
model_ready_df = master_df[final_columns].dropna(subset=['Gross_Profitability', 'FCF_Yield', 'y_target'])

# Convert the "Sector" text column into 1s and 0s for the Decision Tree
model_ready_df = pd.get_dummies(model_ready_df, columns=['Sector'], drop_first=False)

# Convert boolean True/False from get_dummies into 1/0 integers for XGBoost compatibility
for col in model_ready_df.columns:
    if col.startswith('Sector_'):
        model_ready_df[col] = model_ready_df[col].astype(int)

print("\n--- DONE! FINAL FEATURE MATRIX ---")
print(model_ready_df.head())
print(model_ready_df.shape[0])
os.makedirs('dataset', exist_ok=True)
model_ready_df.to_csv(r'dataset/model_data.csv', index=False)