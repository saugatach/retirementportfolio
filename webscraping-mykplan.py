#!/usr/bin/env python3

import os
import pickle

import pandas as pd
import numpy as np
import re
import time
import datetime as dt
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException


# ---==================[reusable code [start]]===================--- #
def genrandomint(n):
    return n + np.random.randint(2)


def sleepy(sleepytime=3):
    time.sleep(sleepytime + np.random.randint(2))


def loaddatafromfile(filename):
    f = open(filename, "r")
    data = f.read().strip()
    return data


# -----------------------[Open ChromeDriver]------------------------ #
def load_webdriver(url, incognito=False):
    """
    Loads ChromeDriver with ChromeOptions[--incognito, download.default_directory, user-agent]
    :return:
    """

    # use an user-agent to mimic real user
    user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) ' \
                 'Chrome/60.0.3112.50 Safari/537.36'

    # set default download directory and user0agent with ChromeOptions
    chromeoptions = webdriver.ChromeOptions()
    prefs = {"download.default_directory": PARENT_DIRECTORY}
    chromeoptions.add_experimental_option("prefs", prefs)
    if incognito:
        chromeoptions.add_argument("--incognito")
    chromeoptions.add_argument('user-agent={0}'.format(user_agent))
    chromeoptions.add_argument('--headless')

    driver1 = webdriver.Chrome(options=chromeoptions)
    driver1.get(url)
    if verbose:
        print("Opening ", url)
    sleepy()  # Let the user actually see something!
    return driver1
# ---===================[reusable code [end]]====================--- #


# -----------------------------[Login]------------------------------ #
# cookies don't work with this website across sessions
def login(driver, logincredfile):
    """
    Logs into the website using stored credentials form the file login.cred
    :param driver:
    :param url_login:
    :param logincredfile:
    :param cookiesfile:
    :return:
    """

    # BEGIN MANUAL LOGIN
    # login credentials from file to avoid exposing them in code
    f = open(logincredfile, "r")
    uname = f.readline().strip()
    pwd = f.readline().strip()
    f.close()
    sleepy()

    username = driver.find_element_by_xpath('//*[@id="txtUserID"]')
    password = driver.find_element_by_xpath('//*[@id="txtPassword"]')
    password1 = driver.find_element_by_xpath('//*[@id="txtstatus"]')
    submit = driver.find_element_by_xpath('//*[@id="cmdLogin"]')
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


def currencytofloat(balance):
    return float(''.join(re.findall(r'\d|\.', balance)))


def getstartenddates(startyear):
    return "01/01/"+str(startyear), "12/31/"+str(startyear)


def datetostr(d):
    return dt.datetime.strftime(d, "%m/%d/%Y")


# ---===============[ENTER DATES IN DOWNLOAD FORM]===============--- #
def download_quicken_date_range(driver, startdate_str, enddate_str, verbose=True):

    startdate_textbox = driver.find_element_by_id("_ctl0_PageContent_txtStartDate")
    enddate_textbox = driver.find_element_by_id("_ctl0_PageContent_txtEndDate")
    download_button = driver.find_element_by_xpath('//input[@value="Download"]')

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


# ---================[DOWNLOAD TRANSACTION DATA]=================--- #
def download_quicken(driver, verbose=True, startdate=dt.date(2017, 9, 1)):

    url2 = 'https://www.mykplan.adp.com/ParticipantSecure_Net/TransactionHistory.aspx'

    startyear = startdate.year
    enddate = dt.date(startyear, 12, 31)
    startdate_str = datetostr(startdate)
    enddate_str = datetostr(enddate)

    if verbose:
        print("Opening ", url2)

    driver.get(url2)

    sleepy(3)

    driver.find_element_by_id("_ctl0_PageContent_RadioButtonUDef").click()

    startdate_textbox = driver.find_element_by_id("_ctl0_PageContent_TextBoxStartDate")
    enddate_textbox = driver.find_element_by_id("_ctl0_PageContent_TextBoxEndDate")
    submit_button = driver.find_element_by_id("_ctl0_PageContent_btnSubmit")

    startdate_textbox.click()
    startdate_textbox.send_keys(startdate_str)
    sleepy()

    enddate_textbox.click()
    enddate_textbox.send_keys(enddate_str)
    sleepy()

    submit_button.click()
    sleepy(3)

    download_quicken = driver.find_element_by_xpath('//a[contains(@href,"TransactionHistoryDownloads")]')

    # verify if link is truly grabbed else exit(-1)
    if download_quicken.text == 'DOWNLOAD to QUICKEN':
        # if link is successfully grabbed then scrape out the random id
        linkrand = re.findall(r'\d+', download_quicken.get_attribute('href'))[0]
        url3 = 'https://www.mykplan.adp.com/ParticipantSecure_Net/TransactionHistoryDownloads.aspx?Rand='+str(linkrand)
        if verbose:
            print("Opening ", url3)

        driver.get(url3)
        sleepy()
    else:
        exit(-1)

    if verbose:
        print("Downloading QFX")

    # first download the date range startdate -> year end of that year
    download_quicken_date_range(driver, startdate_str, enddate_str, verbose)

    # continue to scrape data in 1 year increment
    startyear = startyear + 1

    while startyear < dt.datetime.today().year:

        startdate_str, enddate_str = getstartenddates(startyear)
        download_quicken_date_range(driver, startdate_str, enddate_str, verbose)
        startyear = startyear + 1
        # end while loop

    # cannot download till year end so exit while loop and download YTD manually
    # but first make sure when the code is run on a weekend the enddate is always Friday
    todayweekday = dt.date.today().weekday()
    deduct_days = int(todayweekday/5)*(todayweekday%5) + (2-int(todayweekday/5))
    enddate = dt.date.today() - dt.timedelta(days=deduct_days)

    startdate_str = "01/01/"+str(dt.date.today().year)
    enddate_str = dt.date.strftime(enddate, "%m/%d/%Y")
    download_quicken_date_range(driver, startdate_str, enddate_str, verbose)

    if verbose:
        print("Download of QFX complete")


# ---==================GET PORTFOLIO ALLOCATION==================--- #
def get_portfolio_allocation(driver, verbose=True):

    url4 = 'https://www.mykplan.adp.com/ParticipantSecure_Net/AccountBalancePartDetailsByInv.aspx'
    if verbose:
        print("Opening ", url4)

    driver.get(url4)
    page_html = driver.page_source
    df = pd.read_html(page_html)
    df = df[4]

    # get portfolio balance
    balance = df['Balance'].iloc[-1]

    # strip off everything ($,) except numbers and .
    portfoliovalue = currencytofloat(balance)

    if verbose:
        print("Reading current portfolio value from this page")

    # read portfoliovalue_csv file to import historical portfolio values
    portfoliovalue_csv = PARENT_DIRECTORY + 'portfoliovalue_401k.csv'

    if os.path.exists(portfoliovalue_csv):
        df_portfoliovalue = pd.read_csv(portfoliovalue_csv)
    else:
        df_portfoliovalue = pd.DataFrame(columns=['Date', 'PortfolioValue401k'])

    todaydate_str = dt.date.strftime(dt.date.today(), "%m/%d/%Y")
    # add a new row of portfolio value but make sure it is not already added
    # (which happens if the code runs multiple times in a single day)
    if df_portfoliovalue[(df_portfoliovalue['Date'] == todaydate_str)].empty:
        df_portfoliovalue = df_portfoliovalue.append({'Date': todaydate_str, 'PortfolioValue401k': portfoliovalue},
                                                     ignore_index=True)
        df_portfoliovalue.to_csv(portfoliovalue_csv, index=False)

        if verbose:
            print("Saving current portfoliovalue to CSV file: ", portfoliovalue_csv)
    else:
        if verbose:
            print("PortfolioValue already written to file today. Multiple runs will not add any more data to file.")

    # clean the dataframe
    # first two rows are useless data
    df = df.drop([0, 1])
    # index is required in next step so reset the index after dropping rows
    df.reset_index(drop=True, inplace=True)
    # The dataframe contains 2 tables - list of funds in user portfolio and list of all available funds
    # The 2 lists are separated by a row of NaN values
    # Index of the separating row can be identified by searching for the row where the column "Balance" has NaN values
    # df['Balance'].isna() returns a list which is True for the 2 separating rows
    # df.index[df['Balance'].isna()] returns the index of the separating rows of which the first index is the one we want
    myportfolio_index_end = df.index[df['Balance'].isna()][0]

    # select user portfolio allocation only
    df = df[:myportfolio_index_end]

    # remove extra columns
    df = df[['Investment Fund', 'Price', '% of Assets']]
    df = df.rename(columns={'Investment Fund': 'fund_name'})
    # On the 'Price' column, strip off everything ($,) except numbers and .
    df['Price'] = list(map(currencytofloat, df['Price']))

    # get the databases containing fund ticker names, historical portfolio allocation, and historical fund price data
    fund_names_file = PARENT_DIRECTORY + 'fund_names.csv'
    portfolio_allocation_file = PARENT_DIRECTORY + 'portfolio_allocation_history.csv'
    fund_prices_file = PARENT_DIRECTORY + 'fund_prices_history.csv'

    # import fund_names_file and map ticker values to fund names
    if os.path.exists(fund_names_file):
        df_fund_names = pd.read_csv(fund_names_file)
    else:
        print("Ticker mapping database must exist")
        df_fund_names = pd.DataFrame({'fund_name': {0: 'PIMCO Total Return Fund - Class A',
              1: 'Franklin Strategic Income Fund - Class A',
              2: 'T. Rowe Price Retirement 2050 Fund - Class R',
              3: 'T. Rowe Price Retirement Balanced Fund - Class R',
              4: 'Invesco Comstock Fund - Class A',
              5: 'Neuberger Berman Sustainable Equity Fund - Trust Class',
              6: 'State Street S&P 500 Index Securities Lending Series Fund - Class IX',
              7: 'Victory Sycamore Established Value Fund - Class A',
              8: 'State Street S&P MidCap Index Non-Lending Series Fund - Class J',
              9: 'Carillon Eagle Mid Cap Growth Fund - Class A',
              10: 'State Street Russell Small Cap Index Securities Lending Series Fund - Class VIII',
              11: 'Franklin Small Cap Growth Fund - Class A',
              12: 'T. Rowe Price International Value Equity Fund - Advisor Class',
              13: 'State Street International Index Securities Lending Series Fund - Class VIII',
              14: 'Oppenheimer International Growth Fund - Class A',
              15: 'Prudential Jennison Natural Resources Fund - Class A',
              16: 'Oppenheimer Gold & Special Minerals Fund - Class A',
              17: 'Fidelity Advisor Real Estate Fund - Class M',
              18: 'Goldman Sachs Technology Opportunities Fund - Class A'},
             'funds': {0: 'PTTRX', 1: 'FRSTX', 2: 'RRTFX', 3: 'RRTIX', 4: 'ACSTX',  5: 'NBSTX', 6: 'SVSPX', 7: 'VEVIX',
              8: 'IVOO', 9: 'HAGAX', 10: 'IWM', 11: 'FSGRX', 12: 'PAIGX', 13: 'VXUS', 14: 'OIGAX', 15: 'PGNAX', 16: 'OPGSX',
              17: 'FHETX', 18: 'GITAX'}})
        df_fund_names.to_csv(fund_names_file, index=False)

    # merge the fund ticker names onto the dataframe df to complete mapping
    df = df.merge(df_fund_names, on='fund_name')

    # historical data will be added as a new column with today's date as the column header
    today_str = dt.date.strftime(dt.date.today(), "%d-%b-%Y")

    # set these dataframes to empty in case the files do not exist
    df_portfolio_allocation = df_fund_price = pd.DataFrame()

    if verbose:
        print("Reading portfolio allocation from this page")

    # ------------ PORTFOLIO ALLOCATION ------------
    # import portfolio allocation file which contains historical portfolio allocation data
    if os.path.exists(portfolio_allocation_file):
        df_portfolio_allocation = pd.read_csv(portfolio_allocation_file)

    # merging on the ticker will map the current portfolio allocation to the correct ticker symbols
    try:
        df_portfolio_allocation = df_portfolio_allocation.merge(
            df[['ticker', '% of Assets']].rename(columns={'% of Assets': today_str}),
            on='ticker', how='outer', suffixes=(False, False)).fillna(0)
        df_portfolio_allocation.to_csv(portfolio_allocation_file, index=False)

        if verbose:
            print("Writing historical portfolio allocation data to file:", portfolio_allocation_file)

    # if the code is run multiple times in a single day the merge will fail with ValueError exception since the pandas
    # was forced to abandon its attempt to rename identical columns with suffixes _x, _y
    except ValueError:
        if verbose:
            print("Historical ticker portfolio allocation data already written to file today. "
                  "Multiple runs will not add any more data to file.")

    # ------------ FUND PRICE ------------
    # import portfolio allocation file which contains historical prices for the funds that were in the portfolio
    if os.path.exists(fund_prices_file):
        df_fund_price = pd.read_csv(fund_prices_file)

    # merging on the ticker will map the current prices to the correct ticker symbols
    try:
        df_fund_price = df_fund_price.merge(df[['ticker', 'Price']].rename(columns={'Price': today_str}),
                                            on='ticker', how='outer', suffixes=(False, False)).fillna(0)
        df_fund_price.to_csv(fund_prices_file, index=False)

        if verbose:
            print("Writing historical ticker price data to file:", fund_prices_file)

    # if the code is run multiple times in a single day the merge will fail with ValueError exception since the pandas
    # was forced to abandon its attempt to rename identical columns with suffixes _x, _y
    except ValueError:
        if verbose:
            print("Historical ticker price data already written to file today. "
                  "Multiple runs will not add amy more data to file.")


# ---=======================[MAIN MODULE]========================--- #
verbose = True

# set environ variables
PARENT_DIRECTORY = '/home/jones/grive/coding/python/stock-python/401k-analysis/data/'
url_login = 'https://www.mykplan.com/participantsecure_net/login.aspx'
logincredfile = PARENT_DIRECTORY + '/login-mykplan.cred'

# load driver
driver = load_webdriver(url_login, incognito=False)
# log into website
login(driver, logincredfile)

# this might break in future if no popup button is there
try:
    closepopupbutton = driver.find_element_by_id("pendo-close-guide-e306c46d")
    closepopupbutton.click()
    if verbose:
        print("Closing popup ...")
    sleepy()
except NoSuchElementException:
    d = 1

download_quicken(driver, verbose)
get_portfolio_allocation(driver, verbose)

driver.close()

if verbose:
    print("ChromeDriver Shutdown")

