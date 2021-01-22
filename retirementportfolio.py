# this is a class file
# to analyse 401k portfolio. This file is not executable
from stockanalysis import helpers
from stockanalysis import getstockdata as gd

import datetime as dt
import logging
import os
import re
from glob import glob

import numpy as np
import pandas as pd
from ofxparse import OfxParser


rflogs = logging.getLogger('retirementportfolio')


def r(num):
    return np.round(num, 2)


def printf(str1, str2="", str3=""):
    try:
        val = float(str2)
        print("| ", str1.ljust(35), "|", (str(r(val)) + str3).ljust(20), "|")
    except:
        print("| ", str1.ljust(35), "|", str2.ljust(20), "|")


class Retirementportfolio:
    """This class helps to analyse a 401k portfolio."""

    # MAIN methods

    # importquicken()                     - imports and merges all quicken files in the directory and exports the
    #                                       merged data to a CSV file
    # gencontrib()                        - generates contribution dataframe in the format ['Date', 'Contribution']
    # compareportfolio(dfcontrib, TICKER) - compares 401k performance with that of a single ticker symbol
    # comparereturn(dfcontrib, TICKER)    - compares current portfolio return to that of a single stock portfolio
    # summary()                           - returns portfolio summary as a Series with the financials as the index

    # internal methods not callable
    # exporttransactions()                - exports transactions from quicken files into an internal dataframe
    # maxcontrib()                        - fetches maximum allowed contribution for the year

    def __init__(self, importquicken=True, forceimportquicken=False, verbose=True):

        if verbose:
            print("Loading module Retirementportfolio")

        # load configurations from settings file
        settings = helpers.load_settings_stocks()

        self.PARENT_DIRECTORY = settings['data_dir']
        self.inputdir = settings['input_dir']
        self.outputdir = settings['output_dir']
        self.stockdata = settings['stockdata']
        self.mykplandata_dir = settings['mykplandata_dir']
        self.alldatafile = settings['401kexport']
        self.fund_prices_history = settings['fund_prices_history']
        self.portfoliovalue = settings['portfoliovalue']
        self.portfolio_allocation_history = settings['portfolio_allocation_history']

        csvfile = os.path.basename(self.alldatafile)
        self.verbose = verbose

        # override [importquicken=True] if quicken files were very recently imported and forceimportquicken = False
        if dt.datetime.fromtimestamp(os.path.getmtime(self.alldatafile)).date() == dt.date.today() \
                and not forceimportquicken:
            if verbose:
                print(csvfile + " already imported today. Ignoring [importquicken=True]")
            importquicken = False

        if importquicken:
            self.rawdata = self.importquicken(self.alldatafile)
        else:
            if os.path.exists(self.alldatafile):
                self.rawdata = pd.read_csv(self.alldatafile, parse_dates=True, header=0)
            else:
                if verbose:
                    print(self.alldatafile + " not found")
                    print("Exiting.")
                exit(-2)
            # self.dfcontrib = self.gencontrib(self.rawdata)

    def importquicken(self, csvfile, exporttocsv=True):
        """
        imports and merges all quicken files in the directory and exports the merged data to a CSV file
        """

        verbose = self.verbose
        if verbose:
            print(csvfile)
        dfs = []
        # ignore case of the extension
        # this is a workaround. For robust use of ignoring case regex needs to be used
        ext = [self.mykplandata_dir + "*.qfx", self.mykplandata_dir + "*.QFX"]
        files = []
        for e in ext:
            files.extend(glob(e))

        if len(files) == 0:
            if verbose:
                print("No QFX files found in working directory:" + self.PARENT_DIRECTORY)
                print("Either download the portfolio data manually to this directory or "
                            "change the working directory by passing the argument <working_directory>\n"
                            "     portfolio = rt.retirementportfolio(working_directory='/home/me/401k/')")
                print("Exiting ...")
            exit(-2)

        for qfx_file in files:
            if verbose:
                print("Reading ... " + qfx_file)
            f = open(qfx_file, "r", encoding="utf-8")
            qfx = OfxParser.parse(f)
            df1 = self.exporttransactions(qfx)
            dfs.append(df1)

        df = pd.concat(dfs)
        df = df.drop_duplicates()
        # df = df.sort_values(by=['Date']).set_index('Date')
        df = df.sort_values(by=['Date'])

        if exporttocsv:
            # export data to CSV
            df.to_csv(csvfile, index=False)
            if verbose:
                print("Output written to: " + csvfile)

        return df

    # exports transactions from quicken files into an internal dataframe. internal calls only
    @staticmethod
    def exporttransactions(qfx):

        # get the data headers
        ll = dir(qfx.account.statement.transactions[0])
        regex = re.compile(r'^(?!__)')
        # props starting with __ like __reduce__ are methods not data. Filter them out
        props = list(filter(regex.search, ll))
        props = props[1:]

        alltransactions = []
        for t in qfx.account.statement.transactions:
            singletransaction = []
            for p in props:
                singletransaction.append(getattr(t, p))
            alltransactions.append(singletransaction)

        tempdf = pd.DataFrame(alltransactions, columns=props)

        # Dropping few columns manually. However, the original data is fully imported in tempdf.
        # We can test for new data in dropped columns by tempdf[colname].unique()

        df_transactions = tempdf[
            ['settleDate', 'security', 'income_type', 'memo', 'type', 'unit_price', 'units', 'total']]
        df_transactions = df_transactions.rename(columns={'settleDate': 'Date'})

        securities = qfx.security_list

        listofsecurities = []
        for s in securities:
            listofsecurities.append([s.uniqueid, s.ticker, s.name])

        df_securities = pd.DataFrame(listofsecurities, columns=['security', 'ticker', 'name'])

        df_transactions = df_transactions.merge(df_securities, on='security')
        df_transactions = df_transactions[['Date', 'security', 'ticker', 'name', 'income_type', 'memo',
                                           'units', 'unit_price']]
        df_transactions['price'] = df_transactions['units'] * df_transactions['unit_price']

        df_transactions = df_transactions.sort_values(by=['Date'])

        return df_transactions

    def gencontrib(self, df_portfoliodata=pd.DataFrame()):
        """
        Generates contribution dataframe in the format [Date, Contribution]
        :param df_portfoliodata:
        :return:
        """

        if df_portfoliodata.empty:
            df_portfoliodata = self.rawdata

        # find total contribution and dividends
        df_portfoliodata['Date'] = pd.to_datetime(df_portfoliodata['Date'])
        df_portfoliodata['Date'] = pd.to_datetime(list(map(lambda x: x.date(), df_portfoliodata['Date'])))

        dfcontrib = df_portfoliodata[df_portfoliodata['memo'] == 'Contribution'][['Date', 'price']]
        dfcontrib.rename({'price': 'contrib'}, axis=1, inplace=True)
        # make the columns float
        dfcontrib['contrib'] = dfcontrib['contrib'].astype('float')

        dfcontrib = dfcontrib.groupby('Date').sum()
        dfcontrib.reset_index(inplace=True)
        # dfcontrib.set_index('Date', inplace=True)

        return dfcontrib

    def getdividends(self, df_portfoliodata=pd.DataFrame()):
        """
        Generate a dividend distribution table with the datafame structure [Date, name, dividend]
        :param df_portfoliodata:
        :return: dfdividends
        """

        if df_portfoliodata.empty:
            df_portfoliodata = self.rawdata

        dfdividends = df_portfoliodata[(df_portfoliodata['memo'] == 'Dividends and Earnings') &
                                       (df_portfoliodata['price'] > 5)][['Date', 'name', 'price']]
        dfdividends = dfdividends.rename(columns={'price': 'dividend'})

        return dfdividends

    def compareportfolio(self, dfcontrib, tickr='SPY', fetchincompletedata=True):
        """
        Compares 401k performance with that of a single ticker symbol.
        This method accepts a ticker and a dataframe containing 401k contributions ONLY.
        Contribution dataframe should be in the format ['Date', 'Contribution']
        Contribution dataframe can be automatically generated by the method gencontrib()
        Returns a dataframe for the ticker performance in the format []

        :param dfcontrib:
        :param tickr:
        :param fetchincompletedata:
        :return: dftickr
        """

        verbose = self.verbose

        if dfcontrib.empty:
            if verbose:
                rflogs.error("Empty dataframe. Expecting a dataframe containing biweekly 401k "
                             "contributions. Use gencontrib(). Exiting.")
            exit(-1)

        # prepare data for loading and comparison
        # transform Date column into datetime object so we can merge the dataframes - stockdata and dfcontrib
        # dfcontrib['Date'] = pd.to_datetime(list(map(lambda x: x.date(), dfcontrib['Date'])))

        startdate = dfcontrib['Date'].iloc[0]
        enddate = dfcontrib['Date'].iloc[-1]

        stock = gd.GetStockData(ticker=tickr, path=self.stockdata, fetchincompletedata=fetchincompletedata,
                                verbose=verbose)
        stockdata = stock.getdata(startdate, enddate)

        if len(stockdata) < 2:  # error: no ticker data
            return pd.DataFrame()

        stockdata = stockdata.reset_index()
        dfcontrib = dfcontrib.reset_index()

        # 'Close vs Close'. We want Close as we want to capture the return due to dividend payouts
        # get rid of extra data like volume etc.
        stockdata = stockdata[['Date', 'Close']]

        # We actually want to know what is the price of SPY on the days we contributed to the 401k portfolio.
        # Direct comparison between unequal sized dataframes are not possible. Instead if we merge (inner=intersection)
        # on the Date column then only the days of contribution will be extracted from the SPY data

        dftickr = pd.merge(stockdata, dfcontrib, on=['Date'], how="inner")

        # the merge leaves behind multiple indices. clean up the dataframe.
        dftickr = dftickr[['Date', 'Close', 'contrib']]

        tickrprice = tickr + 'price'
        tickrunits = tickr + 'units'
        tickrunitstotal = tickr + 'unitstotal'
        tickrportfoliovalue = tickr + 'portfoliovalue'
        tickrreturn = tickr + 'return'

        dftickr.rename({'Close': tickrprice}, axis=1, inplace=True)

        dftickr[tickrunits] = dftickr['contrib'] / dftickr[tickrprice]
        dftickr[tickrunitstotal] = dftickr[tickrunits].cumsum()

        dftickr['totcontrib'] = dftickr['contrib'].cumsum()
        dftickr[tickrportfoliovalue] = dftickr[tickrunitstotal] * dftickr[tickrprice]
        dftickr[tickrreturn] = r((dftickr[tickrportfoliovalue] / dftickr['totcontrib'] - 1) * 100)

        return dftickr[['Date', tickrportfoliovalue]]

    def comparereturn(self, dfcontrib, tickr='SPY', fetchincompletedata=True):
        """ compares current portfolio return to that of a single stock portfolio
        :param dfcontrib:
        :param tickr:
        :param fetchincompletedata:
        :return: tickertotalreturn
        """

        dftickr = self.compareportfolio(dfcontrib, tickr, fetchincompletedata)
        if len(dftickr) == 0:  # error: no ticker data
            return False
        tickrportfoliovalue = tickr + 'portfoliovalue'
        tickertotalreturn = dftickr[tickrportfoliovalue].iloc[-1]

        return r(tickertotalreturn)

    def getcurrentportfoliovalue(self):
        """
        :return: currentval
        """

        if os.path.exists(self.portfoliovalue):
            df_portfoliovalue = pd.read_csv(self.portfoliovalue)
            currentval = float(df_portfoliovalue['PortfolioValue401k'].iloc[-1])
        else:
            rflogs.error(self.portfoliovalue + " not found")
            currentval = input("What is the current value of portfolio: ")

        if currentval == '':
            currentval = 40000

        return currentval

    def getreturn(self, dfcontrib, tickr, fetchincompletedata):
        """
        Calculates ['ticker', 'excessreturn', 'yoyreturn', 'totreturn'] for a single ticker
        :param dfcontrib:
        :param tickr:
        :param fetchincompletedata:
        :return: [tickr, excessreturn, yoyreturn, totreturn]
        """

        ret = self.comparereturn(dfcontrib, tickr, fetchincompletedata)
        if not ret:  # error: no ticker data
            return []

        excessreturn = np.round(ret - self.getcurrentportfoliovalue(), 2)

        startdate = dfcontrib['Date'].iloc[0]
        enddate = dfcontrib['Date'].iloc[-1]
        timeindays = (enddate - startdate).days

        totalcontrib = dfcontrib["contrib"].sum()

        yoyreturn = np.round((np.exp(np.log(ret / totalcontrib) / timeindays) - 1) * 365 * 100, 2)
        totreturn = np.round((ret / totalcontrib - 1) * 100, 2)

        return [tickr, excessreturn, yoyreturn, totreturn]

    @staticmethod
    def maxcontrib():
        """
        Fetches maximum allowed contribution for the year
        :return: maxcontrib
        """

        maxcontribfile = 'maxcontrib.csv'

        if os.path.exists(maxcontribfile):
            dfmaxcontrib = pd.read_csv(maxcontribfile)
            maxcontrib = dfmaxcontrib[(dfmaxcontrib['Year'] == dt.date.today().year)]['Contrib']
        else:
            # For future years, the limit may be indexed for inflation, increasing in increments of $500
            # maxcontrib = 19000 + 500*(dt.date.today().year - 2019)

            url5 = 'https://www.pensions123.com/index.php/401k-limit-graph'
            df = pd.read_html(url5)[0]
            df.columns = df.iloc[1]
            df = df.drop([0, 1])
            maxcontrib = int(df["401(k) &402(g)(1)"].iloc[0])

        return maxcontrib

    def summary(self):
        """Return portfolio summary as a Series with the financials as the index"""

        currentval = self.getcurrentportfoliovalue()
        dfcontrib = self.gencontrib()
        dfdividend = self.getdividends()
        df = self.rawdata

        totalcontrib = r(float(dfcontrib["contrib"].sum()))
        totaldiv = dfdividend["dividend"].sum()
        thisyearstart = dt.datetime(dt.date.today().year, 1, 1)
        ytdcontrib = dfcontrib[(dfcontrib['Date'] > thisyearstart)]["contrib"].sum()

        # find how much is left for annual max 401k contribution
        maxc = self.maxcontrib()
        allowedcontrib = maxc - ytdcontrib

        # calculate portfolio returns
        startdate = df['Date'].iloc[0]
        enddate = df['Date'].iloc[-1]

        totalret = str(r((currentval / totalcontrib - 1) * 100)) + "%"
        totaltime = (enddate - startdate).days
        yearsinvested = totaltime / 365.25
        yoyreturn = str(r((np.exp(np.log(currentval / totalcontrib) / yearsinvested) - 1) * 100)) + "%"

        yearsinvested_str = str(np.round(yearsinvested)) + " years " + str(
            totaltime - np.round(yearsinvested) * 365) + " days"

        summary = pd.Series([currentval, totalcontrib, totaldiv, yearsinvested_str, totalret, yoyreturn, ytdcontrib,
                             maxc, allowedcontrib],
                            index=["Current portfolio value", "Total Contribution", "Total Dividends",
                                   "Total time in the market", "Total return", "YoY return", "YTD Contribution",
                                   "Max Contribution for this year", "Allowed Contribution left"])

        return summary
