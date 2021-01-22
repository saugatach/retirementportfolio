#!/usr/bin/env python3
import argparse

import setpath
from stockanalysis import helpers
from stockanalysis import getstockdata as gd

import time
from tqdm import tqdm
import retirementportfolio as rt
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import load_etf_data


def getargs(description="Compare portfolio performance with all ETFs"):
    # parse command-line arguments using argparse()
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-v', '--verbose', help='Verbose mode [Default=Off]', action='store_true')
    parser.add_argument('-s', '--summary', help='Display summary and exit', action='store_true')
    args = parser.parse_args()
    return args

def prettyprint(tickr, currentval, ret):
    print("+" + "-" * 41 + "+")
    print("|" + "Portfolio".center(20) + "|" + tickr.center(20) + "|")
    print("-" * 43)
    print("|" + "".center(20) + "|" + "".center(20) + "|")
    print("|" + str(currentval).center(20) + "|" + str(ret).center(20) + "|")
    print("+" + "-" * 41 + "+")
    print("\n")
    print("Excess return over " + tickr + " = ", currentval - ret, "\n")


def sleepy(x=np.random.randint(1)):
    time.sleep(x+np.random.randint(2))


def main(args):
    # -------------------------- MAIN MODULE --------------------------

    verbose = args.verbose
    summary = args.summary

    # load configurations from settings file
    settings = helpers.load_settings_stocks()
    outputdir = settings['output_dir']

    portfolio = rt.Retirementportfolio(importquicken=True, verbose=verbose)
    dfcontrib = portfolio.gencontrib()

    if summary:
        print(portfolio.summary())
        exit(0)
    # currentval = portfolio.getcurrentportfoliovalue()

    tickerlist = load_etf_data.etflist()
    # tickerlist = []
    if len(tickerlist) == 0:
        tickerlist = ['SPY', 'QQQ', 'IWM', 'IBB', 'BND', 'VGT', 'UPRO', 'TQQQ', 'VNQ', 'GLD', 'AAPL', 'MSFT', 'AMZN',
                      'GITAX', 'VITAX', 'HAGAX', 'KO', 'COST', 'BABA', 'T', 'TMUS']
    # print("First 5 ETFs in the database:", tickerlist)
    # exit(0)
    # smaller list for testing purposes
    # tickerlist = ['SPY', 'QQQ', 'IWM']
    portfolioreturns = []
    for tickr in tqdm(tickerlist):
        # if verbose:
        #     print("Working on", tickr)
        ret = portfolio.getreturn(dfcontrib, tickr, fetchincompletedata=False)
        if len(ret) > 2:        # if len(ret) < 2 then error: no ticker data
            portfolioreturns.append(ret)
            # print(ret)

        # sleepy(5)

    df = pd.DataFrame(portfolioreturns, columns=['ticker', 'excessreturn', 'yoyreturn', 'totreturn'])

    # save comparison with ETFs to file
    comparereturnsfile = outputdir + 'comparereturns.csv'
    df.to_csv(comparereturnsfile, index=False)
    print("Comparisons are saved to " + comparereturnsfile)

    # filter our non-performers keeping excess return ones and compare their growth w.rt. to your portfolio growth
    df = df[(df['excessreturn'] > 0)]
    print(portfolio.summary())
    helpers.printdataframe(df)
    df.plot(kind='bar', x='ticker', y='excessreturn')
    plt.show()


if __name__ == '__main__':
    args = getargs()
    main(args)
