import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error , r2_score
from script import main


def load_data(df):
    df = df.dropna(axis=1)
    X = df.drop(coloums=[1],axis=1)
    y = df.iloc[:,1]
    return X , y

def split_data(X,y,test_size=0.2,random_state=42):
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
    print(f"MSE: {round(means_square_err, 2)}")
    print(f"R^2: {r2_score}")

#Pickle the model
def save_model(model,path):
    pass


model = LinearRegression()


#X are the feautures  y is the price that is going to be predicted
