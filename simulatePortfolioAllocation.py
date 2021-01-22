#!/usr/bin/env python3
from stockanalysis import helpers
from stockanalysis import getstockdata as gd

import argparse
import logging
import retirementportfolio as rt
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


simportfoliologs = logging.getLogger("simulateportfolio")


def r(n):
    return np.round(n, 2)


def getargs():
    # parse command-line arguments using argparse()
    description = "Simulate the current portfolio allocation and compare with another ETF."
    epilog = "./simulatePortfolioAllocation.py -v -t QQQ"
    parser = argparse.ArgumentParser(description=description, epilog=epilog)
    parser.add_argument('-v', '--verbose', help='Verbose mode [Default=Off]', action='store_true')
    parser.add_argument('-f', '--fetchincompletedata', help='Fetch incomplete data [Default=Off]', action='store_true')
    parser.add_argument('-t', '--ticker', help='Compare with ETF ticker [Default=SPY]', type=str)
    args = parser.parse_args()
    return args


def getprices(ticker, dfcontrib, fetchincompletedata=True):
    """
    Returns a table of prices for a specific ticker symbol on the days of contribution to the portfolio
    in the format ['Date', 'price', 'value']
    :param ticker:
    :param dfcontrib:
    :param fetchincompletedata:
    :return:
    """

    # prepare data for loading and comparison
    # transform Date column into datetime object so we can merge the dataframes - stockdata and dfcontrib
    startdate = dfcontrib['Date'].iloc[0]
    enddate = dfcontrib['Date'].iloc[-1]

    stock = gd.GetStockData(ticker, fetchincompletedata=fetchincompletedata)
    stockdata = stock.getdata(startdate, enddate)['Close']

    stockdata = stockdata.reset_index()

    # 'Adj Close vs Close'. We want Adj Close as we want to capture the return due to dividend payouts
    # get rid of extra data like volume etc.
    stockdata = stockdata[['Date', 'Close']]
    stockdata.rename({'Close': 'price'}, axis=1, inplace=True)

    # We actually want to know what is the price of SPY on the days we contributed to the 401k portfolio.
    # Direct comparison between unequal sized dataframes are not possible. Instead if we merge (inner=intersection)
    # on the Date column then only the days of contribution will be extracted from the SPY data

    dftickr = pd.merge(stockdata, dfcontrib, on=['Date'], how="inner")
    dftickr['units'] = dfcontrib['contrib'] / dftickr['price']
    dftickr['value'] = dftickr['units'].cumsum() * dftickr['price']

    # the merge leaves behind multiple indices. clean up the dataframe.
    dftickr = dftickr[['Date', 'price', 'value']]

    return dftickr


def simportfolio(args):
    verbose = args.verbose
    # load configurations from settings file
    settings = helpers.load_settings_stocks()
    inputdir = settings['input_dir']

    # import available mutual funds and their percentage allocation in the portfolio.
    # format: [fund_name, funds, allocation]
    mfnames = inputdir + 'mutual-funds-available-in-mykplan.csv'
    if verbose:
        print('Loading ' + mfnames)
    allocs = pd.read_csv(mfnames)

    verbose = args.verbose

    fetchincompletedata = args.fetchincompletedata

    if args.ticker is None:
        stock = 'SPY'
    else:
        stock = args.ticker

    if verbose:
        simportfoliologs.info("Stock ticker to compare portfolio with [ {0} ]".format(stock))

    # load the retirementportfolio class to begin the data import
    portfolio = rt.Retirementportfolio(importquicken=True)

    # import the contributions to the portfolio. format: [Date, Contribution]
    dfcontrib = portfolio.gencontrib()

    # import the dividend payouts to the portfolio. format: [Date, name, dividend]
    dfdividends = portfolio.getdividends()
    dfdividends = dfdividends[['Date', 'dividend']]

    # create empty dataframe to keep adding the price evolution of each ticker as a column
    df = pd.DataFrame()
    df['Date'] = dfcontrib['Date']

    for ticker, f in zip(allocs['funds'], allocs['allocation']):
        dftickr = getprices(ticker, dfcontrib, fetchincompletedata)
        # The 'value' column contains the real information
        df[ticker] = dftickr['value'] * f / 100
        df = df.ffill(axis=0)

    # compare portfolio performance to a single broad market ETF performance
    dfstock = getprices(stock, dfcontrib)

    # include dividend payouts from 401k
    dfportfolio = df
    dfportfolio.set_index('Date', inplace=True)
    dfportfolio['portfoliovalue_nodiv'] = df.sum(axis=1)

    dfportfolio = pd.merge(dfportfolio, dfdividends, on=['Date'], how='outer', sort=True)
    dfportfolio['sum_div'] = dfportfolio['dividend'].cumsum().fillna(method='ffill').fillna(0)
    dfportfolio['portfoliovalue_nodiv'] = dfportfolio['portfoliovalue_nodiv'].fillna(method='ffill')
    dfportfolio['dividend'] = dfportfolio['dividend'].fillna(0)
    dfportfolio['portfoliovalue_div'] = dfportfolio['portfoliovalue_nodiv'] + dfportfolio['sum_div']
    dfportfolio = pd.merge(dfportfolio, dfstock, on=['Date'], how='outer', sort=True)
    dfportfolio.rename({'value': stock + 'value'}, axis=1, inplace=True)

    if verbose:
        print(dfportfolio)
    # TODO: find delta of performance
    # plot portfolio performance graph
    dfportfolio.set_index('Date', inplace=True)
    dfportfolio[['portfoliovalue_nodiv', 'portfoliovalue_div', stock + 'value']].plot()
    plt.show()


if __name__ == '__main__':
    helpers.initiate_logging()
    args = getargs()
    simportfolio(args)
