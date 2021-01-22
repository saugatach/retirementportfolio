#!/usr/bin/env python3

# this is a class file
# to download data from ADP website
import argparse
import glob

from stockanalysis import helpers

import datetime as dt
import getpass
import os
import re
import time

import numpy as np
import pandas as pd
from selenium import webdriver


# ---==================[reusable code [start]]===================--- #
def genrandomint(n):
    return n + np.random.randint(2)


def sleepy(sleepytime=3):
    time.sleep(sleepytime + np.random.randint(2))


def loaddatafromfile(filename):
    f = open(filename, "r")
    data = f.read().strip()
    return data


def getlogininfo():
    pwd = ""
    uname = input("Enter username: ") or "X"
    if uname == "X":
        print("Username skipped. Exiting.")
        exit(-1)
    try:
        pwd = getpass.getpass()
    except Exception as error:
        print(error, "Password skipped. Exiting.")
        exit(-2)

    return [uname, pwd]


def currencytofloat(balance):
    return float(''.join(re.findall(r'\d|\.', balance)))


def getstartenddates(startyear):
    return "01/01/" + str(startyear), "12/31/" + str(startyear)


def datetostr(dts):
    return dt.datetime.strftime(dts, "%m/%d/%Y")



class Mykplan:
    """This class automates the download of contribution data from ADP website"""

    def __init__(self,
                 url='https://mykplan.adp.com/public/Login/index',
                 startdate=dt.date(2017, 9, 1),
                 login=False,
                 auto=True,
                 headless=True,
                 verbose=False):

        if verbose:
            print("Loading module Mykplan")

        # load configurations from settings file
        settings = helpers.load_settings_stocks()

        self.PARENT_DIRECTORY = settings['data_dir']
        self.inputdir = settings['input_dir']
        self.outputdir = settings['output_dir']
        self.mykplandata_dir = settings['mykplandata_dir']
        logincredfile = settings['login_cred']
        self.fund_names_file = settings['fund_names_file']
        self.alldatafile = settings['401kexport']
        self.portfoliovalue = settings['portfoliovalue']
        self.portfolio_allocation_history = settings['portfolio_allocation_history']
        self.fund_prices_history = settings['fund_prices_history']

        self.mykplandata_dir = os.path.abspath(self.mykplandata_dir)
        download_dir = self.mykplandata_dir
        self.manuallogin = login

        # load driver
        self.driver = self.load_webdriver(url, download_dir=download_dir, headless=headless,
                                          incognito=False, verbose=verbose)
        # log into website
        self.login(logincredfile, verbose=verbose)

        # if auto=TRUE then automatically download everything -
        # - contribution data, portfolio allocation, current portfolio value, fund prices
        if auto:
            self.download_quicken(startdate=startdate, verbose=verbose)
            dfdata = self.getportfoliodata(verbose)
            self.portfoliobalancehistory(dfdata, verbose)
            self.portfolioallocationhistory(dfdata, verbose)
            self.fundpricehistory(dfdata, verbose)
            self.close()

    # -----------------------[Open ChromeDriver]------------------------ #
    def load_webdriver(self, url, download_dir='.', headless=False, incognito=False, verbose=True):
        """
        Loads ChromeDriver with ChromeOptions[--incognito, download.default_directory, user-agent]
        :param download_dir:
        :param url:
        :param headless:
        :param incognito:
        :param verbose:
        :return:
        """

        # use an user-agent to mimic real user
        user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) ' \
                     'Chrome/60.0.3112.50 Safari/537.36'

        # set default download directory and user0agent with ChromeOptions
        chromeoptions = webdriver.ChromeOptions()
        if incognito:
            chromeoptions.add_argument("--incognito")
        if headless:
            chromeoptions.add_argument('--headless')
        chromeoptions.add_argument('user-agent={0}'.format(user_agent))
        prefs = {"download.default_directory": download_dir}
        chromeoptions.add_experimental_option("prefs", prefs)

        driver1 = webdriver.Chrome(options=chromeoptions)
        driver1.get(url)
        if verbose:
            print("Opening ", url)
        sleepy()  # Let the user actually see something!
        return driver1

    # ---===================[reusable code [end]]====================--- #

    # -----------------------------[Login]------------------------------ #
    # cookies don't work with this website across sessions
    def login(self, logincredf, verbose=True):
        """
        Logs into the website using stored credentials form the file login.cred
        :param logincredf:
        :param verbose:
        :return:
        """

        if self.manuallogin:
            if verbose:
                print("Manual login")
                uname, pwd = getlogininfo()
        elif not os.path.exists(logincredf):
            print(logincredf, "not found")
            uname, pwd = getlogininfo()
        else:
            # login credentials from file to avoid exposing them in code
            f = open(logincredf, "r")
            uname = f.readline().strip()
            pwd = f.readline().strip()
            f.close()
            sleepy()

        username = self.driver.find_element_by_xpath('//*[@id="uid"]')
        password = self.driver.find_element_by_xpath('//*[@id="pwd"]')
        submit = self.driver.find_element_by_xpath('//*[@class="btn-signin"]')
        username.clear()
        username.click()
        username.send_keys(uname)
        sleepy()

        password.clear()
        password.click()
        password.send_keys(pwd)
        sleepy()

        submit.click()

        if verbose:
            print('Successfull login')

        sleepy(5)

    # ---------------------------[End Login]---------------------------- #

    # ---================[DOWNLOAD TRANSACTION DATA]=================--- #
    def download_quicken(self, startdate=dt.date(2017, 9, 1), verbose=True):

        if verbose:
            print("< download_quicken >")
        # delete existing gradebooks and download latest version
        # ignore case of the extension
        # this is a workaround. For robust use of ignoring case regex needs to be used
        ext = [self.mykplandata_dir + "/*.qfx", self.mykplandata_dir + "/*.QFX"]
        files = []
        for e in ext:
            files.extend(glob.glob(e))

        if len(files) > 0:
            for qfx_file in files:
                if verbose:
                    print("Deleting ", qfx_file)
                os.remove(qfx_file)

        url2 = 'https://www.mykplan.adp.com/ParticipantSecure_Net/TransactionHistory.aspx'

        startyear = startdate.year
        enddate = dt.date(startyear, 12, 31)
        startdate_str = datetostr(startdate)
        enddate_str = datetostr(enddate)

        if verbose:
            print("Opening ", url2)

        self.driver.get(url2)
        sleepy(3)

        self.driver.find_element_by_id("_ctl0_PageContent_RadioButtonUDef").click()

        startdate_textbox = self.driver.find_element_by_id("_ctl0_PageContent_TextBoxStartDate")
        enddate_textbox = self.driver.find_element_by_id("_ctl0_PageContent_TextBoxEndDate")
        submit_button = self.driver.find_element_by_id("_ctl0_PageContent_btnSubmit")

        startdate_textbox.click()
        startdate_textbox.send_keys(startdate_str)
        sleepy()

        enddate_textbox.click()
        enddate_textbox.send_keys(enddate_str)
        sleepy()

        submit_button.click()
        sleepy(3)

        downloadquicken = self.driver.find_element_by_xpath('//a[contains(@href,"TransactionHistoryDownloads")]')

        # verify if link is truly grabbed else exit(-1)
        if downloadquicken.text == 'DOWNLOAD to QUICKEN':
            # if link is successfully grabbed then scrape out the random id
            linkrand = re.findall(r'\d+', downloadquicken.get_attribute('href'))[0]
            url3 = 'https://www.mykplan.adp.com/ParticipantSecure_Net/TransactionHistoryDownloads.aspx?Rand=' + str(
                linkrand)
            if verbose:
                print("Opening ", url3)

            self.driver.get(url3)
            sleepy()
        else:
            exit(-1)

        if verbose:
            print("Downloading QFX")

        # first download the date range startdate -> year end of that year
        self.download_quicken_date_range(startdate_str, enddate_str, verbose)

        # continue to scrape data in 1 year increment
        startyear = startyear + 1

        while startyear < dt.datetime.today().year:
            startdate_str, enddate_str = getstartenddates(startyear)
            self.download_quicken_date_range(startdate_str, enddate_str, verbose)
            startyear = startyear + 1
            # end while loop

        # cannot download till year end so exit while loop and download YTD manually
        # but first make sure when the code is run on a weekend the enddate is always Friday
        # todayweekday = dt.date.today().weekday()
        # TODO: the 2 might cause issue here. check later
        # deduct_days = int(todayweekday / 5) * (todayweekday % 5) + (2 - int(todayweekday / 5))
        deduct_days = 1
        enddate = dt.date.today() - dt.timedelta(days=deduct_days)

        startdate_str = "01/01/" + str(dt.date.today().year)
        enddate_str = dt.date.strftime(enddate, "%m/%d/%Y")
        self.download_quicken_date_range(startdate_str, enddate_str, verbose)

        if verbose:
            print("Download of QFX complete")

    # ---===============[ENTER DATES IN DOWNLOAD FORM]===============--- #
    def download_quicken_date_range(self, startdate_str, enddate_str, verbose=True):

        startdate_textbox = self.driver.find_element_by_id("_ctl0_PageContent_txtStartDate")
        enddate_textbox = self.driver.find_element_by_id("_ctl0_PageContent_txtEndDate")
        download_button = self.driver.find_element_by_xpath('//input[@value="Download"]')

        startdate_textbox.click()
        startdate_textbox.clear()
        startdate_textbox.send_keys(startdate_str)
        sleepy()

        enddate_textbox.click()
        enddate_textbox.clear()
        enddate_textbox.send_keys(enddate_str)
        sleepy()

        if verbose:
            print("Downloading data from {0} to {1}".format(startdate_str, enddate_str))

        download_button.click()
        sleepy()

    # ---==================GET PORTFOLIO ALLOCATION==================--- #
    def getportfoliodata(self, verbose=True):
        url4 = 'https://www.mykplan.adp.com/ParticipantSecure_Net/AccountBalancePartDetailsByInv.aspx'
        if verbose:
            print("Opening ", url4)

        self.driver.get(url4)
        page_html = self.driver.page_source
        df = pd.read_html(page_html)
        df = df[4]

        # clean the dataframe
        # first two rows are useless data
        df = df.drop([0, 1])
        # index is required in next step so reset the index after dropping rows
        df.reset_index(drop=True, inplace=True)
        return df

    def portfoliobalancehistory(self, df, verbose=True):
        # get portfolio balance
        balance = df['Balance'].iloc[-1]
        # balance = driver1.find_element_by_id("_ctl0_PageContent_lblEndBal").text
        # strip off everything ($,) except numbers and .
        portfoliovalue = currencytofloat(balance)

        if verbose:
            print("Reading current portfolio value from this page")

        if os.path.exists(self.portfoliovalue):
            df_portfoliovalue = pd.read_csv(self.portfoliovalue)
        else:
            df_portfoliovalue = pd.DataFrame(columns=['Date', 'PortfolioValue401k'])

        todaydate_str = dt.date.strftime(dt.date.today(), "%m/%d/%Y")
        # add a new row of portfolio value but make sure it is not already added
        # (which happens if the code runs multiple times in a single day)
        if df_portfoliovalue[(df_portfoliovalue['Date'] == todaydate_str)].empty:
            df_portfoliovalue = df_portfoliovalue.append({'Date': todaydate_str, 'PortfolioValue401k': portfoliovalue},
                                                         ignore_index=True)
            df_portfoliovalue.to_csv(self.portfoliovalue, index=False)

            if verbose:
                print("Saving current portfoliovalue to CSV file: ", self.portfoliovalue)
        else:
            if verbose:
                print("PortfolioValue already written to file today. Multiple runs will not add any more data to file.")

    def mergefundnames(self, df):

        # import fund_names_file and map ticker values to fund names
        if os.path.exists(self.fund_names_file):
            df_fund_names = pd.read_csv(self.fund_names_file)
        else:
            print("Ticker mapping database must exist")
            df_fund_names = \
                pd.DataFrame({'fund_name': {0: 'PIMCO Total Return Fund - Class A',
                                            1: 'Franklin Strategic Income Fund - Class A',
                                            2: 'T. Rowe Price Retirement 2050 Fund - Class R',
                                            3: 'T. Rowe Price Retirement Balanced Fund - Class R',
                                            4: 'Invesco Comstock Fund - Class A',
                                            5: 'Neuberger Berman Sustainable Equity Fund - Trust Class',
                                            6: 'State Street S&P 500 Index Securities Lending Series Fund - Class IX',
                                            7: 'Victory Sycamore Established Value Fund - Class A',
                                            8: 'State Street S&P MidCap Index Non-Lending Series Fund - Class J',
                                            9: 'Carillon Eagle Mid Cap Growth Fund - Class A',
                                            10: 'State Street Russell Small Cap Index Securities Lending Series Fund - '
                                                'Class VIII',
                                            11: 'Franklin Small Cap Growth Fund - Class A',
                                            12: 'T. Rowe Price International Value Equity Fund - Advisor Class',
                                            13: 'State Street International Index Securities Lending Series Fund - '
                                                'Class VIII',
                                            14: 'Oppenheimer International Growth Fund - Class A',
                                            15: 'Prudential Jennison Natural Resources Fund - Class A',
                                            16: 'Oppenheimer Gold & Special Minerals Fund - Class A',
                                            17: 'Fidelity Advisor Real Estate Fund - Class M',
                                            18: 'Goldman Sachs Technology Opportunities Fund - Class A'},
                              'ticker': {0: 'PTTRX', 1: 'FRSTX', 2: 'RRTFX', 3: 'RRTIX', 4: 'ACSTX', 5: 'NBSTX',
                                         6: 'SVSPX',
                                         7: 'VEVIX',
                                         8: 'IVOO', 9: 'HAGAX', 10: 'IWM', 11: 'FSGRX', 12: 'PAIGX', 13: 'VXUS',
                                         14: 'OIGAX',
                                         15: 'PGNAX', 16: 'OPGSX',
                                         17: 'FHETX', 18: 'GITAX'}})
            df_fund_names.to_csv(self.fund_names_file, index=False)

        # merge the fund ticker names onto the dataframe df to complete mapping
        dfmergedwfunds = df.merge(df_fund_names, on='fund_name')
        return dfmergedwfunds

    def portfolioallocationhistory(self, df, verbose=True):
        # clean df

        # The dataframe contains 2 tables - list of funds in user portfolio and list of all available funds
        # The 2 lists are separated by a row of NaN values
        # Index of the separating row can be identified by searching for the row where the column "Balance" has NaN
        # df['Balance'].isna() returns a list which is True for the 2 separating rows
        # df.index[df['Balance'].isna()] returns the index of the separating rows
        # of which the first index is the one we want
        myportfolio_index_end = df.index[df['Balance'].isna()][0]

        # select user portfolio allocation only
        df = df[:myportfolio_index_end]

        # remove extra columns
        df = df[['Investment Fund', 'Price', '% of Assets']]
        df = df.rename(columns={'Investment Fund': 'fund_name'})
        # On the 'Price' column, strip off everything ($,) except numbers and "."
        df['Price'] = list(map(currencytofloat, df['Price']))

        dfwfundnames = self.mergefundnames(df)

        # ------------ PORTFOLIO ALLOCATION ------------
        # set these dataframes to empty in case the files do not exist
        df_portfolio_allocation = pd.DataFrame()

        # import portfolio allocation file which contains historical portfolio allocation data
        if os.path.exists(self.portfolio_allocation_history):
            df_portfolio_allocation = pd.read_csv(self.portfolio_allocation_history)

        # historical data will be added as a new column with today's date as the column header
        today_str = dt.date.strftime(dt.date.today(), "%d-%b-%Y")

        if verbose:
            print("Reading portfolio allocation from this page")

        # merging on the ticker will map the current portfolio allocation to the correct ticker symbols
        try:
            df_portfolio_allocation = df_portfolio_allocation.merge(
                dfwfundnames[['ticker', '% of Assets']].rename(columns={'% of Assets': today_str}),
                on='ticker', how='outer', suffixes=(False, False)).fillna(0)
            df_portfolio_allocation.to_csv(self.portfolio_allocation_history, index=False)

            if verbose:
                print("Writing historical portfolio allocation data to file:", self.portfolio_allocation_history)

        # if the code is run multiple times in a single day the merge will fail with ValueError exception
        # since pandas was forced to abandon its attempt to rename identical columns with suffixes _x, _y
        except ValueError:
            if verbose:
                print("Historical ticker portfolio allocation data already written to file today. "
                      "Multiple runs will not add any more data to file.")

    def fundpricehistory(self, df, verbose=True):

        # clean df
        df = df.drop(df[df['Balance'].isna()].index.values).reset_index(drop=True)
        df = df.drop(
            df[(df['Balance'] == 'Available Funds') | (df['Investment Fund'] == 'Total')].index.values).reset_index(
            drop=True)
        df = df[['Investment Fund', 'Price']]
        df = df.rename(columns={'Investment Fund': 'fund_name'})
        # On the 'Price' column, strip off everything ($,) except numbers and "."
        df['Price'] = list(map(currencytofloat, df['Price']))

        dfwfundnames = self.mergefundnames(df)

        # ------------ FUND PRICE ------------
        # import portfolio allocation file which contains historical prices for the funds that were in the portfolio
        if os.path.exists(self.fund_prices_history):
            df_fund_price = pd.read_csv(self.fund_prices_history)

        # historical data will be added as a new column with today's date as the column header
        today_str = dt.date.strftime(dt.date.today(), "%d-%b-%Y")

        # merging on the ticker will map the current prices to the correct ticker symbols
        try:
            df_fund_price = df_fund_price.merge(dfwfundnames[['ticker', 'Price']].
                                                rename(columns={'Price': today_str}),
                                                on='ticker', how='outer', suffixes=(False, False)).fillna(0)
            df_fund_price.to_csv(self.fund_prices_history, index=False)

            if verbose:
                print("Writing historical ticker price data to file:", self.fund_prices_history)

        # if the code is run multiple times in a single day the merge will fail with ValueError exception since pandas
        # was forced to abandon its attempt to rename identical columns with suffixes _x, _y
        except ValueError:
            if verbose:
                print("Historical ticker price data already written to file today. "
                      "Multiple runs will not add amy more data to file.")

    def close(self):
        self.driver.close()
        print("ChromeDriver Shutdown")


def getargs():
    # parse command-line arguments using argparse()
    parser = argparse.ArgumentParser(description='Download contribution data and portfolio allocation '
                                                 'from retirement account.')
    parser.add_argument('-o', '--headless', help='Headless mode [Default=Off]', action='store_true')
    parser.add_argument('-v', '--verbose', help='Verbose mode [Default=Off]', action='store_true')
    parser.add_argument('-m', '--manuallogin', help='Login manually instead of stored credential file [Default=Off]',
                        action='store_true')
    parser.add_argument('-n', '--nodownload', help='Do not download contribution data [Default=On]',
                        action='store_false')
    args = parser.parse_args()
    return args


def main():
    args = getargs()
    headless = args.headless
    verbose = args.verbose
    manuallogin = args.manuallogin
    download = args.nodownload

    print("headless:", headless)
    print("verbose:", verbose)
    print("manual login:", manuallogin)
    print("download:", download)

    mykplanobj = Mykplan(headless=headless, login=manuallogin, auto=download, verbose=verbose)


if __name__ == '__main__':
    main()
