#!/usr/bin/env python3
import os
import time

import retirementportfolio as rt
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from stockanalysis import helpers
from stockanalysis import getstockdata as gd
import datetime as dt


def r(n):
    return np.round(n, 2)


def fundperf(allocs):

    startdate, enddate = dt.datetime.today() - dt.timedelta(days=3 * 365), dt.datetime.today()

    # create empty dataframe to keep adding the price evolution of each ticker as a column
    ticker = allocs['funds'].iloc[0]
    stockobj = gd.GetStockData(ticker)
    df = stockobj.getdata(startdate, enddate)
    df = df.rename(columns={'Close': ticker})
    df = df[[ticker, 'Volume']]
    # df['Date'] = dfcontrib['Date']

    for ticker in allocs['funds'][1:]:
        stockobj = gd.GetStockData(ticker)
        dftemp = stockobj.getdata(startdate, enddate)
        df[ticker] = dftemp['Close']
        # dftemp = dftemp.rename({'Close': ticker})
        # df.merge(dftemp, left_index=True, right_index=True)
        # The 'value' column contains the real information

    df = df.drop(columns='Volume')
    df = df.apply(lambda x: r(x))
    return df


def main():
    fundnames = 'data/datainput/mutual-funds-available-in-mykplan.csv'
    fundperfcsv = 'data/dataoutput/' + 'fund_performance.csv'

    allocs = pd.read_csv(fundnames)

    if os.path.exists(fundperfcsv):
        df = pd.read_csv(fundperfcsv)
        df = df.set_index('Date')
    else:
        df = fundperf(fundnames=allocs, years=3)
        df.to_csv(fundperfcsv)

    # df.columns = list(map(lambda x: x.split(" Fund - ")[0], allocs['fund_name']))
    dfnorm = np.round((df.iloc[-1]/df.iloc[0]-1)*100, 2)

    allocs['perf'] = list(dfnorm)
    print(allocs.sort_values('perf'))

    dfnorm.plot.barh(figsize=(20, 5))
    plt.show()


if __name__ == "__main__":
    main()
