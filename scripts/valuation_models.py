import yfinance as yf
import numpy as np

def cost_of_equity(beta):
    return 0.0396 + (beta*0.0438)

def WACC(beta,mc,td,coe,cod,tr):
    v = mc + td
    Wacc = ((mc/v)*coe) + ((td/v)*cod*(1-tr))
    return Wacc

def discounted_cashflow_analysis(ticker):
    ticker = yf.Ticker(ticker)
    tickerData = ticker.info
    tickerbs = ticker.balancesheet.iloc[:, 0]
    ticker_financial = ticker.financials[:, 0]
    freeCashflow = tickerData["freeCashflow"]
    beta = tickerData["beta"]
    marketCap = tickerData["marketCap"]
    totalDebt = tickerData["totalDebt"]
    taxRate = ticker_financial["Tax Provision"] / ticker_financial["Pretax Income"]
    COD = ticker_financial["Interest Expense"] / tickerbs["Total Debt"]
    if freeCashflow == None or beta == None or marketCap == None or beta == np.inf:
        return None

    firmValue = marketCap + totalDebt
    COE = cost_of_equity(beta)
#    COD = interestExpense / totalDebt
#    taxRate = taxexpense/pretaxincome
    #WACC
    wacc = WACC(beta, marketCap, totalDebt, COE, COD, taxRate)



    return wacc

#bs = yf.Ticker("NVDA")
#balanceSheet = bs.balancesheet['2026-01-31']
#fn = bs.financials["2026-01-31"]
print(discounted_cashflow_analysis("NVDA"))