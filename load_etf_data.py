#!/usr/bin/env python3
from stockanalysis import helpers
from stockanalysis import getstockdata as gd

import argparse
import logging
import os
import time

import pandas as pd
import numpy as np



helpers.initiate_logging()
load_etf_data_logs = logging.getLogger('load_etf_data')


def getargs():
    # parse command-line arguments using argparse()
    parser = argparse.ArgumentParser(description='Loads data for ETFs in the etflist')
    parser.add_argument('-v', '--verbose', help='Verbose mode [Default=Off]', action='store_true')
    parser.add_argument('-f', '--fetchincompletedata', help='fetch incomplete data; when off fetches data iff the '
                                                            'ETF is not on disk [Default=Off]', action='store_true')

    args = parser.parse_args()

    return args


def etflist(verbose=True):
    """Get ETF list"""

    # load configurations from settings file
    settings = helpers.load_settings_stocks()
    inputdir = settings['input_dir']

    etflistfile = inputdir + 'etflist.csv'
    if os.path.exists(etflistfile):
        if verbose:
            load_etf_data_logs.info("Loading ticker list from file: " + etflistfile)
        dfetf = pd.read_csv(etflistfile)
    else:
        if verbose:
            load_etf_data_logs.error("Local ETFlist file not found " + etflistfile)
            load_etf_data_logs.info("Loading ticker list from Yahoo:")
        dfetf = getetfyahoo(verbose)

    tickerlist = dfetf['Symbol']

    return tickerlist


def getetfyahoo(verbose=True):
    """Get ETF list from Yahoo"""

    url1 = 'https://finance.yahoo.com/screener/unsaved/99f6dea0-c683-424a-aab2-8df8f048a60b?offset='
    url2 = '&count=200'

    dflist = []
    for i in range(5):
        url = url1 + str(i * 200) + url2
        if verbose:
            load_etf_data_logs.info("Getting URL: " + url1 + url2)
        dftemp = pd.read_html(url)
        dflist.append(dftemp[0])
        helpers.sleepy(2)

    dfetf = pd.concat(dflist)
    dfetf = dfetf.reset_index()
    dfetf = dfetf.drop(columns=['index'])
    dfetf.to_csv('etflist.csv', index=False)
    return dfetf


def getetfdata(tickerlist, fetchincompletedata=False, verbose=True):
    """Get ETF data from Yahoo"""

    # load configurations from settings file
    settings = helpers.load_settings_stocks()
    outputdir = settings['stockdata']

    sleepcount = 0
    randcounterlimit = 50

    for tickr in tickerlist:
        stock = gd.GetStockData(ticker=tickr, path=outputdir, fetchincompletedata=fetchincompletedata)

        if len(stock.df_yahoo) > 0:
            # TODO: there is some bug here stock.df_yahoo is empty even when yfinance fetches data
            # if data is loaded from Yahoo then sleep randomly to give impression of human activity
            # if data is NOT loaded from Yahoo then skip sleeping
            # Every 50-80 URLS sleep for 2-20 mins
            sleepcount = sleepcount + 1
            if sleepcount > randcounterlimit:
                sleepcount = 0
                randcounterlimit = np.random.randint(50, 80)
                sleeptime = np.random.randint(2, 5) * 60
                if verbose:
                    load_etf_data_logs.info("Sleeping ... " + str(sleeptime / 60) + " mins")
                helpers.sleepy(sleeptime)
            else:
                sleeptime = np.random.randint(3, 7)
                if verbose:
                    load_etf_data_logs.info("Sleeping ... " + str(sleeptime) + " seconds")
                helpers.sleepy(sleeptime)
        print("-" * 20)


def main():

    args = getargs()
    tickerlist = etflist(verbose=args.verbose)
    getetfdata(tickerlist, fetchincompletedata=args.fetchincompletedata, verbose=args.verbose)


if __name__ == '__main__':
    main()
