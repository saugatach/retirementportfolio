#!/usr/bin/env python3
import sys

import retirementportfolio as rt
import pandas as pd
import numpy as np
from stockanalysis import getstockdata as gd
import matplotlib.pyplot as plt


def r(n):
    return np.round(n, 2)


def getprices(ticker, dfcontrib):
    """
    Returns a table of prices for a specific ticker symbol on the days of contribution to the portfolio
    in the format ['Date', 'price', 'value']
    :param ticker:
    :param dfcontrib:
    :return:
    """

    # prepare data for loading and comparison
    # transform Date column into datetime object so we can merge the dataframes - stockdata and dfcontrib
    # dfcontrib['Date'] = pd.to_datetime(list(map(lambda x: x.date(), dfcontrib['Date'])))

    startdate = dfcontrib['Date'].iloc[0]
    enddate = dfcontrib['Date'].iloc[-1]

    stock = gd.GetStockData(ticker)

    stockdata = stock.getdata(startdate, enddate)

    stockdata = stockdata.reset_index()

    # 'Adj Close vs Close'. We want Adj Close as we want to capture the return due to dividend payouts
    # get rid of extra data like volume etc.
    stockdata = stockdata[['Date', 'Adj Close']]
    stockdata.rename({'Adj Close': 'price'}, axis=1, inplace=True)

    # We actually want to know what is the price of SPY on the days we contributed to the 401k portfolio.
    # Direct comparison between unequal sized dataframes are not possible. Instead if we merge (inner=intersection)
    # on the Date column then only the days of contribution will be extracted from the SPY data

    dftickr = pd.merge(stockdata, dfcontrib, on=['Date'], how="inner")

    dftickr['units'] = dfcontrib['contrib']/dftickr['price']
    dftickr['value'] = dftickr['units'].cumsum() * dftickr['price']

    # the merge leaves behind multiple indices. clean up the dataframe.
    dftickr = dftickr[['Date', 'price', 'value']]

    return dftickr


# -------------------------- MAIN MODULE --------------------------
if len(sys.argv) > 1:
    stock = sys.argv[1]
else:
    stock = 'SPY'

# load the retirementportfolio class to begin the data import
portfolio = rt.retirementportfolio(importquicken=False)

# import the contributions to the portfolio. format: [Date, Contribution]
dfcontrib = portfolio.gencontrib()

# import the dividend payouts to the portfolio. format: [Date, name, dividend]
dfdividends = portfolio.getdividends()
dfdividends = dfdividends[['Date', 'dividend']]

# import available mutual funds and their percentage allocation in the portfolio. format: [fund_name, funds, allocation]
allocs = pd.read_csv('./data/mutual-funds-available-in-mykplan.csv')

# create empty dataframe to keep adding the price evolution of each ticker as a column
df = pd.DataFrame()
df['Date'] = dfcontrib['Date']

for ticker, f in zip(allocs['funds'], allocs['allocation']):
    dftickr = getprices(ticker, dfcontrib)
    # The 'value' column contains the real information
    df[ticker] = dftickr['value'] * f/100

# compare portfolio performance to a single broad market ETF performance
dfstock = getprices(stock, dfcontrib)

# include dividend payouts from 401k
dfportfolio = df
dfportfolio['portfoliovalue_nodiv'] = df.sum(axis=1)
dfportfolio = pd.merge(dfportfolio, dfdividends, on=['Date'], how='outer', sort=True)
dfportfolio['sum_div'] = dfportfolio['dividend'].cumsum().fillna(method='ffill').fillna(0)
dfportfolio['portfoliovalue_nodiv'] = dfportfolio['portfoliovalue_nodiv'].fillna(method='ffill')
dfportfolio['dividend'] = dfportfolio['dividend'].fillna(0)
dfportfolio['portfoliovalue_div'] = dfportfolio['portfoliovalue_nodiv'] + dfportfolio['sum_div']

dfportfolio = pd.merge(dfportfolio, dfstock, on=['Date'], how='outer', sort=True)
dfportfolio.rename({'value': stock+'value'}, axis=1, inplace=True)
dfportfolio = dfportfolio.ffill(axis=0)
print(dfportfolio)

# plot portfolio performance graph
dfportfolio.set_index('Date', inplace=True)
dfportfolio[['portfoliovalue_nodiv', 'portfoliovalue_div', stock+'value']].plot()
plt.show()

