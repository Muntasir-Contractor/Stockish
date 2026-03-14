import simfin as sf
import pandas as pd
import numpy as np
import warnings
import os
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), '..', 'backend', '.env')

# Load that specific .env file
load_dotenv(dotenv_path=env_path)
SIMFIN = os.getenv("SIMFIN")
warnings.filterwarnings('ignore', category=FutureWarning)

# Set your local SimFin data directory
sf.set_api_key(SIMFIN)
sf.set_data_dir('~/simfin_data/')

print("1. Loading raw datasets and calculating preliminary features...")
df_inc = sf.load_income(variant='quarterly').reset_index()

# --- NEW FEATURE: Revenue Growth YoY ---
# Sort by date so the 4-quarter lookback is accurate
df_inc = df_inc.sort_values(['Ticker', 'Report Date'])
df_inc['Revenue_Growth_YoY'] = df_inc.groupby('Ticker')['Revenue'].pct_change(periods=4)
df_inc.replace([float('inf'), float('-inf')], pd.NA, inplace=True)
# ---------------------------------------

df_bal = sf.load_balance(variant='quarterly').reset_index()
df_cf  = sf.load_cashflow(variant='quarterly').reset_index()
df_prices = sf.load_shareprices(variant='daily').reset_index()

# --- NEW FEATURE: 6-Month Momentum ---
# Sort prices chronologically
df_prices = df_prices.sort_values(['Ticker', 'Date'])
# Calculate the trailing 6-month (126 trading days) return
df_prices['Momentum_6M'] = df_prices.groupby('Ticker')['Close'].pct_change(periods=126)
# -------------------------------------

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
df_fundamentals['Free Cash Flow'] = df_fundamentals['Net Cash from Operating Activities'] + df_fundamentals['Change in Fixed Assets & Intangibles'].fillna(0)

# --- NEW FEATURE: Shares Outstanding YoY Growth (calculated on quarterly fundamentals) ---
df_fundamentals['Shares_Outstanding_YoY_Growth'] = df_fundamentals.groupby('Ticker')['Shares (Basic)'].pct_change(periods=4)
# -----------------------------------------------------------------------------------------

flow_columns = [
    'Gross Profit', 'Operating Income (Loss)', 'Free Cash Flow',
    'Net Income',                      # needed for Accrual Ratio
    'Depreciation & Amortization',     # needed for EBITDA
    'Interest Expense, Net',           # needed for Interest Coverage Ratio
]

for col in flow_columns:
    if col in df_fundamentals.columns:
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
master_df['Total_Debt'] = master_df['Short Term Debt'].fillna(0) + master_df['Long Term Debt'].fillna(0)
master_df['Invested_Capital'] = master_df['Total_Debt'] + master_df['Total Equity'].fillna(0)

# Calculate the actual Machine Learning Ratios using the TTM metrics!
master_df['Gross_Profitability'] = master_df['Gross Profit_TTM'] / master_df['Total Assets']
master_df['ROIC'] = master_df['Operating Income (Loss)_TTM'] / master_df['Invested_Capital']
master_df['FCF_Yield'] = master_df['Free Cash Flow_TTM'] / master_df['Market_Cap']

# --- NEW FEATURE: EV / EBITDA ---
master_df['Enterprise_Value'] = master_df['Market_Cap'] + master_df['Total_Debt'] - master_df['Cash, Cash Equivalents & Short Term Investments'].fillna(0)
if 'Depreciation & Amortization_TTM' in master_df.columns:
    master_df['EBITDA_TTM'] = master_df['Operating Income (Loss)_TTM'] + master_df['Depreciation & Amortization_TTM'].fillna(0)
    master_df['EV_to_EBITDA'] = master_df['Enterprise_Value'] / master_df['EBITDA_TTM']
# --------------------------------

# --- NEW FEATURE: Accrual Ratio (earnings quality) ---
# High accruals = earnings driven by accounting, not cash → negative signal
if 'Net Income_TTM' in master_df.columns:
    master_df['Accrual_Ratio'] = (master_df['Net Income_TTM'] - master_df['Free Cash Flow_TTM']) / master_df['Total Assets']
# ------------------------------------------------------

# --- NEW FEATURE: Interest Coverage Ratio ---
if 'Interest Expense, Net_TTM' in master_df.columns:
    # Interest Expense, Net in SimFin is typically negative; negate for the denominator
    master_df['Interest_Coverage'] = master_df['Operating Income (Loss)_TTM'] / (master_df['Interest Expense, Net_TTM'].abs())
# --------------------------------------------

# Clean out division-by-zero or infinite values
master_df.replace([float('inf'), float('-inf')], pd.NA, inplace=True)

# Drop rows where no forward price was found
master_df = master_df.dropna(subset=['Date'])

print("6. Calculating the Target Variable (y)...")
# Map the future 1-year price backwards
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

# Calculate the 1-year return
master_df['Forward_1yr_Return'] = (master_df['Future_Close_1yr'] / master_df['Close']) - 1

# Rank percentile cross-sectionally within each YearMonth (same year + same month)
# This ensures each stock is ranked relative to all others published in the same calendar month
master_df['YearMonth'] = master_df['Date'].dt.to_period('M')
master_df['y_target'] = master_df.groupby('YearMonth')['Forward_1yr_Return'].transform(
    lambda x: pd.qcut(x, q=10, labels=False, duplicates='drop')
)

print(f"   Forward_1yr_Return null count: {master_df['Forward_1yr_Return'].isna().sum()} / {len(master_df)}")
print(f"   y_target null count: {master_df['y_target'].isna().sum()} / {len(master_df)}")
print(f"   FCF_Yield null count: {master_df['FCF_Yield'].isna().sum()} / {len(master_df)}")

print("7. Finalizing the Dataset & One-Hot Encoding Sectors...")
# Build list of new feature columns that were successfully computed
new_feature_cols = []
for col in ['EV_to_EBITDA', 'Accrual_Ratio', 'Interest_Coverage', 'Shares_Outstanding_YoY_Growth']:
    if col in master_df.columns:
        new_feature_cols.append(col)

final_columns = [
    'Ticker', 'Date', 'YearMonth', 'Sector',
    'Gross_Profitability', 'ROIC', 'FCF_Yield',
    'Revenue_Growth_YoY', 'Momentum_6M',
    *new_feature_cols,
    'Forward_1yr_Return', 'y_target'
]

# Drop rows missing ANY of the critical features
model_ready_df = master_df[final_columns].dropna(
    subset=['Gross_Profitability', 'FCF_Yield', 'Revenue_Growth_YoY', 'Momentum_6M', 'y_target']
)

# Convert the "Sector" text column into 1s and 0s for the Decision Tree
model_ready_df = pd.get_dummies(model_ready_df, columns=['Sector'], drop_first=False)

# Convert boolean True/False from get_dummies into 1/0 integers for XGBoost compatibility
for col in model_ready_df.columns:
    if col.startswith('Sector_'):
        model_ready_df[col] = model_ready_df[col].astype(int)

print("\n--- DONE! FINAL FEATURE MATRIX ---")
print(model_ready_df.head())
print(f"Total Rows Processed: {model_ready_df.shape[0]}")
print(model_ready_df.columns)

os.makedirs('dataset', exist_ok=True)
model_ready_df.to_csv(r'dataset/model_data_new_new.csv', index=False)