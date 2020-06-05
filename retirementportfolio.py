# this is a class file
# to analyse 401k portfolio. This file is not executable

import datetime as dt
import numpy as np
from stockanalysis import getstockdata as gd
import os
from glob import glob
from ofxparse import OfxParser
import pandas as pd
import re


class retirementportfolio:
    """ This class helps to analyse a 401k portfolio."""

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

    def __init__(self, importquicken=True, csvfile='401kexport.csv',
                 working_directory='/home/jones/grive/coding/python/stock-python/401k-analysis/data/', verbose=True):

        self.PARENT_DIRECTORY = working_directory
        csv = self.PARENT_DIRECTORY + csvfile

        # override [importquicken=True] if quicken files were very recently imported
        if dt.datetime.fromtimestamp(os.path.getmtime(csv)).date() == dt.date.today():
            if verbose:
                print(csvfile, "already imported today. Ignoring [importquicken=True]")
            importquicken = False

        if importquicken:
            self.rawdata = self.importquicken(csv)
        else:
            if os.path.exists(csv):
                self.rawdata = pd.read_csv(csv, parse_dates=True, header=0)
            else:
                if verbose:
                    print(csv, " not found")
                    print("Exiting.")
                exit(-2)

    # imports and merges all quicken files in the directory and exports the merged data to a CSV file
    def importquicken(self, csvfile, exporttocsv=True, verbose=True):
        dfs = []
        # ignore case of the extension
        # this is a workaround. For robust use of ignoring case regex needs to be used
        ext = [self.PARENT_DIRECTORY + "*.qfx", self.PARENT_DIRECTORY + "*.QFX"]
        files = []
        for e in ext:
            files.extend(glob(e))

        if len(files) == 0:
            if verbose:
                print("No QFX files found in working directory:", self.PARENT_DIRECTORY)
                print("Either download the portfolio data manually to this directory or "
                      "change the working directory by passing the argument <working_directory>\n"
                      "     portfolio = rt.retirementportfolio(working_directory='/home/me/401k/')")
                print("Exiting ...")
            exit(-2)

        for qfx_file in files:
            if verbose:
                print("Reading ...", qfx_file)
            f = open(qfx_file, "r", encoding="utf-8")
            qfx = OfxParser.parse(f)
            df1 = self.exporttransactions(qfx)
            dfs.append(df1)

        df = pd.concat(dfs)
        df = df.drop_duplicates()
        df = df.sort_values(by=['Date'])

        if exporttocsv:
            # export data to CSV
            df.to_csv(csvfile, index=False)
            if verbose:
                print("Output written to:", csvfile)

        return df

    # exports transactions from quicken files into an internal dataframe. internal calls only
    def exporttransactions(self, qfx):

        transactions = qfx.account.statement.transactions
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

    # shortcut to round to 2 decimal places
    def r(self, num):
        return np.round(num, 2)

    # justified print
    def printf(self, str1, str2="", str3=""):
        try:
            val = float(str2)
            print("| ", str1.ljust(35), "|", (str(self.r(val)) + str3).ljust(20), "|")
        except:
            print("| ", str1.ljust(35), "|", str2.ljust(20), "|")

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

    def compareportfolio(self, dfcontrib, tickr='SPY', verbose=True):
        """
        Compares 401k performance with that of a single ticker symbol.
        This method accepts a ticker and a dataframe containing 401k contributions ONLY.
        Contribution dataframe should be in the format ['Date', 'Contribution']
        Contribution dataframe can be automatically generated by the method gencontrib()
        Returns a dataframe for the ticker performance in the format []

        :param dfcontrib:
        :param tickr:
        :return: dftickr
        """

        if dfcontrib.empty:
            if verbose:
                print("ERROR: Empty dataframe. Expecting a dataframe containing biweekly 401k contributions. "
                      "Use gencontrib(). Exiting.")
            exit(-1)

        # prepare data for loading and comparison
        # transform Date column into datetime object so we can merge the dataframes - stockdata and dfcontrib
        # dfcontrib['Date'] = pd.to_datetime(list(map(lambda x: x.date(), dfcontrib['Date'])))

        startdate = dfcontrib['Date'].iloc[0]
        enddate = dfcontrib['Date'].iloc[-1]

        stock = gd.GetStockData(tickr)

        stockdata = stock.getdata(startdate, enddate)

        stockdata = stockdata.reset_index()
        dfcontrib = dfcontrib.reset_index()

        # 'Adj Close vs Close'. We want Adj Close as we want to capture the return due to dividend payouts
        # get rid of extra data like volume etc.
        stockdata = stockdata[['Date', 'Adj Close']]

        # We actually want to know what is the price of SPY on the days we contributed to the 401k portfolio.
        # Direct comparison between unequal sized dataframes are not possible. Instead if we merge (inner=intersection)
        # on the Date column then only the days of contribution will be extracted from the SPY data

        dftickr = pd.merge(stockdata, dfcontrib, on=['Date'], how="inner")

        # the merge leaves behind multiple indices. clean up the dataframe.
        dftickr = dftickr[['Date', 'Adj Close', 'contrib']]

        tickrprice = tickr + 'price'
        tickrunits = tickr + 'units'
        tickrunitstotal = tickr + 'unitstotal'
        tickrportfoliovalue = tickr + 'portfoliovalue'
        tickrreturn = tickr + 'return'

        dftickr.rename({'Adj Close': tickrprice}, axis=1, inplace=True)

        dftickr[tickrunits] = dftickr['contrib'] / dftickr[tickrprice]
        dftickr[tickrunitstotal] = dftickr[tickrunits].cumsum()

        dftickr['totcontrib'] = dftickr['contrib'].cumsum()
        dftickr[tickrportfoliovalue] = dftickr[tickrunitstotal] * dftickr[tickrprice]
        dftickr[tickrreturn] = self.r((dftickr[tickrportfoliovalue] / dftickr['totcontrib'] - 1) * 100)

        return dftickr[['Date', tickrportfoliovalue]]

    def comparereturn(self, dfcontrib, tickr='SPY'):
        """ compares current portfolio return to that of a single stock portfolio
        :param dfcontrib:
        :param tickr:
        :return: tickertotalreturn
        """

        dftickr = self.compareportfolio(dfcontrib, tickr)
        tickrportfoliovalue = tickr + 'portfoliovalue'
        tickertotalreturn = dftickr[tickrportfoliovalue].iloc[-1]

        return self.r(tickertotalreturn)

    def getcurrentportfoliovalue(self):
        """
        :return: currentval
        """

        portfoliovalue_csv = self.PARENT_DIRECTORY + 'portfoliovalue_401k.csv'
        if os.path.exists(portfoliovalue_csv):
            df_portfoliovalue = pd.read_csv(portfoliovalue_csv)
            currentval = float(df_portfoliovalue['PortfolioValue401k'].iloc[-1])

        else:
            currentval = input("What is the current value of portfolio:")

        if currentval == '':
            currentval = 40000

        return currentval

    def getreturn(self, dfcontrib, tickr):
        """
        Calculates ['ticker', 'excessreturn', 'yoyreturn', 'totreturn'] for a single ticker
        :param dfcontrib:
        :param tickr:
        :return: [tickr, excessreturn, yoyreturn, totreturn]
        """

        ret = self.comparereturn(dfcontrib, tickr)
        excessreturn = np.round(ret - self.getcurrentportfoliovalue(), 2)

        startdate = dfcontrib['Date'].iloc[0]
        enddate = dfcontrib['Date'].iloc[-1]
        timeindays = (enddate - startdate).days

        totalcontrib = dfcontrib["contrib"].sum()

        yoyreturn = np.round((np.exp(np.log(ret / totalcontrib) / timeindays) - 1) * 365 * 100, 2)
        totreturn = np.round((ret / totalcontrib - 1) * 100, 2)

        return [tickr, excessreturn, yoyreturn, totreturn]

    def maxcontrib(self):
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

        totalcontrib = self.r(float(dfcontrib["contrib"].sum()))
        totaldiv = dfdividend["dividend"].sum()
        thisyearstart = dt.datetime(dt.date.today().year, 1, 1)
        ytdcontrib = dfcontrib[(dfcontrib['Date'] > thisyearstart)]["contrib"].sum()

        # find how much is left for annual max 401k contribution
        max = self.maxcontrib()
        allowedcontrib = max - ytdcontrib

        # calculate portfolio returns
        startdate = df['Date'].iloc[0]
        enddate = df['Date'].iloc[-1]

        totalret = str(self.r((currentval / totalcontrib - 1) * 100)) + "%"
        totaltime = (enddate - startdate).days
        yearsinvested = totaltime / 365.25
        yoyreturn = str(self.r((np.exp(np.log(currentval / totalcontrib) / yearsinvested) - 1) * 100)) + "%"

        yearsinvested_str = str(np.round(yearsinvested)) + " years " + str(
            totaltime - np.round(yearsinvested) * 365) + " days"

        summary = pd.Series([currentval, totalcontrib, totaldiv, yearsinvested_str, totalret, yoyreturn, ytdcontrib,
                             max, allowedcontrib],
                            index=["Current portfolio value", "Total Contribution", "Total Dividends",
                                   "Total time in the market", "Total return", "YoY return", "YTD Contribution",
                                   "Max Contribution for this year", "Allowed Contribution left"])

        return summary
