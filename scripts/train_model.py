import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error , r2_score
from script import main
import joblib
from xgboost import XGBRegressor
def load_data(df):
    df = df.dropna(axis=0)
    df["Current Price"].round(3)
    y = df["Current Price"]
    #Dropping Ticker and Current stock price
    X = df.drop(columns=["Ticker", "Current Price"], axis=1)
    for col in X:
        X[col].round(3)
    mask = y.notna()
    X = X[mask]
    y = y[mask]
    return X , y

def split_data(X,y,test_size=0.2,random_state=42):
    # Splitting the data given by 80% training and 20% testing unless otherwise inputted
    return train_test_split(X,y,test_size=test_size,random_state=random_state)

#train model using the 80% training data
def train_model(X_train,y_train):
    model = LinearRegression()
    model.fit(X_train,y_train)
    return model

#Switching from a linear regression model to an XGboost model
def train_xgboost_model(X_train,y_train):
    model = XGBRegressor(
        n_estimators = 300,
        learning_rate = 0.05,
        max_depth=5,
        subsample=0.8
        )
    model.fit(X_train, y_train)
    return model


#Evaluate with means squared error and r2 score
def evaluate_model(model, X_test,y_test):
    y_prediction = model.predict(X_test)
    means_square_err = mean_squared_error(y_test,y_prediction) #MSE
    r2 = r2_score(y_test,y_prediction)
    print(f"MSE: {means_square_err}")
    print(f"R^2 score : {r2}")
    return means_square_err , r2

#Pickle the model
def save_model(model,path=r'model\finalized_model.joblib'):
    joblib.dump(model, path)

def run():
    df = pd.read_csv(r"scripts\dataset\Ticker_data.csv")
    print("Complete reading")
    X, y = load_data(df)
    print("Complete loading data")
    x_train , x_test , y_train , y_test = split_data(X,y,0.2)
    x_test = x_test.apply(pd.to_numeric, errors='coerce')
    y_test = y_test.apply(pd.to_numeric, errors='coerce')
    mask = x_test.notna().all(axis=1) & y_test.notna()
    x_test = x_test[mask]
    y_test = y_test[mask]
    print("Complete splitting train and test data")
    model = train_xgboost_model(x_train,y_train)
    print("Model is done training")
    evaluate_model(model,x_test,y_test)
    save_model(model=model,path=r'model\XGboost_model.joblib')
    print("model saved")

if __name__ == "__main__":
    run()

    