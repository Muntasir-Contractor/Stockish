from fastapi import FastAPI

app = FastAPI()

#Get for reading
#Post for create
#Put for update
#Delete for delete

#Start of a beginning
@app.get("/")
def root():
    return {"Hello": "World"}

@app.get("/stock/{ticker}")
def get_stock_data(ticker : str):
    pass

@app.get("/homepage")
def get_homepage_data():
    pass