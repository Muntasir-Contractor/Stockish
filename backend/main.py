from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from topmovers import get_top_movers
import joblib
import sys
from pathlib import Path
root = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root))
from application import price_prediction, valuation

app = FastAPI()
origins = [
    "http://localhost:3000",
    "http://localhost:5174",
    "http://localhost:5173"

]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

#Loading model when app starts 
MODEL = joblib.load(r"model\XGboost_model.joblib")

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

@app.get("/stockprediction/{ticker}")
async def get_prediction(ticker : str):
    stock_price_prediction = await price_prediction(ticker,MODEL)
    conclusion , factor = valuation(ticker, stock_price_prediction)
    return {"Stock Prediction": stock_price_prediction , "Stock Valuation": conclusion, "Relative Error": factor}

@app.get("/topmovers")
async def top_movers():
    stocks = await get_top_movers()
    return stocks

@app.get("/homepage")
def get_homepage_data():
    pass

#uvicorn main:app --reload
