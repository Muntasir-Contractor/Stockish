import pandas as pd
import xgboost
import joblib
import optuna
from sklearn.metrics import accuracy_score, classification_report
import matplotlib.pyplot as plt

def save_model(model, path=r'model/XGBoost_newestfr_model.joblib'):
    joblib.dump(model, path)
    return

df = pd.read_csv('dataset/model_data_newest_cleaned.csv')

df['Date'] = pd.to_datetime(df['Date'])
df = df.sort_values('Date')

split_idx = int(len(df) * 0.8)
train_df = df.iloc[:split_idx]
test_df  = df.iloc[split_idx:]

print(f"Training rows (80%): {len(train_df)}")
print(f"Testing rows (20%): {len(test_df)}")
print(f"Data split at date: {train_df['Date'].max().date()}")
print(f"Latest date in test: {test_df['Date'].max().date()}")

features_to_drop = ['Ticker', 'Date', 'y_target', 'Forward_1yr_Return', 'YearMonth'] + [col for col in train_df.columns if 'Sector_' in col]

X_train = train_df.drop(columns=features_to_drop)
y_train = train_df['y_target']

X_test = test_df.drop(columns=features_to_drop)
y_test = test_df['y_target']


def objective(trial):
    params = {
        'objective':     'multi:softmax',
        'num_class':     10,
        'random_state':  42,
        'n_jobs':        -1,
        'verbosity':     0,
        'n_estimators':  trial.suggest_int('n_estimators', 100, 600),
        'max_depth':     trial.suggest_int('max_depth', 3, 8),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.2, log=True),
        'subsample':     trial.suggest_float('subsample', 0.6, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
        'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
        'gamma':         trial.suggest_float('gamma', 0.0, 1.0),
    }
    model = xgboost.XGBClassifier(**params)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    return accuracy_score(y_test, y_pred)


def tune(n_trials=50):
    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)

    print(f"\nBest accuracy: {study.best_value * 100:.2f}%")
    print(f"Best params:   {study.best_params}")
    return study.best_params


def train_test_model(params=None):
    if params is None:
        params = {
            'n_estimators':  400,
            'max_depth':     4,
            'learning_rate': 0.05,
        }

    model = xgboost.XGBClassifier(
        objective='multi:softmax',
        num_class=10,
        random_state=42,
        n_jobs=-1,
        **params
    )
    model.fit(X_train, y_train)
    print("Training Complete")

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Raw Accuracy: {accuracy * 100:.2f}%")
    print(classification_report(y_test, y_pred))

    importance_df = pd.DataFrame({
        'Feature':    X_train.columns,
        'Importance': model.feature_importances_
    }).sort_values(by='Importance', ascending=True)

    plt.figure(figsize=(10, 6))
    plt.barh(importance_df['Feature'], importance_df['Importance'], color='skyblue')
    plt.title('XGBoost Feature Importances (What drives the 1-Year Return?)')
    plt.xlabel('Relative Importance')
    plt.tight_layout()
    plt.show()

    return model


#14.47
# New 13.92
# Newest n=200 lr = 0.1 15.39% 9.0 precision: 20% recall: 17%
# Newest n=200, lr=0.05 15.96%, max depth 6 raw accuracy 9.0 precision: 21% recall: 17%
if __name__ == "__main__":
    best_params = tune(n_trials=100)
    model = train_test_model(params=best_params)
    save_model(model)
    print("Model saved")
