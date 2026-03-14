import pandas as pd
import xgboost
import joblib
from sklearn.metrics import accuracy_score, classification_report
import matplotlib.pyplot as plt

# ADD THESE FEATURES TO IMPROVE: EV_to_EBITDA , Accrual_Ratio , Interest_Coverage_Ratio, Shares_Outstanding_YoY_Growth
# Data required: Shares Outstanding, Interest Expense, Total Debt

def save_model(model,path=r'model/XGBoost_newfr_model.joblib'):
    joblib.dump(model, path)
    return

df = pd.read_csv('dataset/model_data_new_new.csv')

df['Date'] = pd.to_datetime(df['Date'])
df = df.sort_values('Date')

split_idx = int(len(df) * 0.8)
# Everything BEFORE the 80% mark is Training
train_df = df.iloc[:split_idx]
# Everything AFTER the 80% mark is Testing
test_df = df.iloc[split_idx:]

print(f"Training rows (80%): {len(train_df)}")
print(f"Testing rows (20%): {len(test_df)}")
print(f"Data split at date: {train_df['Date'].max().date()}")
print(f"Latest date in test: {test_df['Date'].max().date()}")


features_to_drop = ['Ticker', 'Date', 'y_target','Forward_1yr_Return', 'YearMonth'] + [col for col in train_df.columns if 'Sector_' in col]

X_train = train_df.drop(columns=features_to_drop)
y_train = train_df['y_target']

X_test = test_df.drop(columns=features_to_drop)
y_test = test_df['y_target']



def train_test_model():
    model = xgboost.XGBClassifier(
        objective='multi:softmax',
        num_class=10,
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        random_state=42,
        n_jobs=-1)
    model.fit(X_train,y_train)
    print("Training Complete")
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test,y_pred)
    print(f"Raw Accuracy: {accuracy*100:.2f}%")
    print(classification_report(y_test,y_pred))
    importances = model.feature_importances_

# Bind them to the column names from your X_train dataset
    feature_names = X_train.columns
    importance_df = pd.DataFrame({
        'Feature': feature_names,
        'Importance': importances
    })

    # Sort them from most important to least important
    importance_df = importance_df.sort_values(by='Importance', ascending=True)

    # Plot the results
    plt.figure(figsize=(10, 6))
    plt.barh(importance_df['Feature'], importance_df['Importance'], color='skyblue')
    plt.title('XGBoost Feature Importances (What drives the 1-Year Return?)')
    plt.xlabel('Relative Importance')
    plt.tight_layout()
    save_model(model)
    print("model saved")
    plt.show()

#14.47
# New 13.92
# Newest n=200 lr = 0.1 15.39% 9.0 precision: 20% recall: 17%
# Newest n=200, lr=0.05 15.96%, max depth 6raw accuracy 9.0 precision: 21% recall: 17%
if __name__ == "__main__":
    train_test_model()