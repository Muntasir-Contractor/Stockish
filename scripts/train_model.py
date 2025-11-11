import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error , r2_score
from script import main
import joblib


def load_data(df):
    df = pd.json_normalize(df[0])
    df = df.dropna(axis=1)
    #Dropping Ticker and Current stock price
    X = df.drop(coloums=["Ticker","Current Price"],axis=1)
    # y is only the stock price
    y = df.iloc[:,1]
    return X , y

def split_data(X,y,test_size=0.2,random_state=42):
    # Splitting the data given by 80% training and 20% testing unless otherwise inputted
    return train_test_split(X,y,test_size=test_size,random_state=random_state)

#train model using the 80% training data
def train_model(X_train,y_train):
    model = LinearRegression()
    model.fit(X_train,y_train)
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
    df = main(True)
    X, y = load_data(df)
    x_train , x_test , y_train , y_test = split_data(X,y,0.2)
    model = train_model(x_train,y_train)
    evaluate_model(model,x_test,y_test)
    save_model(model=model)

    