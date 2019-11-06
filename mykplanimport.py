#!/usr/bin/env python3
# this script converts Quicken format qfx files to csv files
# the script does 3 things:
# 1. Import all qfx files in the directory
# 2. Convert the data to pandas dataframe
# 3. Merge data from all files into a single csv file

from glob import glob
from ofxparse import OfxParser
import pandas as pd
import re


def exporttransactions(qfx):

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

    df_transactions = tempdf[['settleDate', 'security', 'income_type', 'memo', 'type', 'unit_price', 'units', 'total']]
    df_transactions = df_transactions.rename(columns={'settleDate': 'Date'})

    securities = qfx.security_list

    listofsecurities = []
    for s in securities:
        listofsecurities.append([s.uniqueid, s.ticker, s.name])

    df_securities = pd.DataFrame(listofsecurities, columns=['security', 'ticker', 'name'])

    df_transactions = df_transactions.merge(df_securities, on='security')
    df_transactions = df_transactions[['Date', 'security', 'ticker', 'name', 'income_type', 'memo',
                                       'units', 'unit_price'] ]
    df_transactions['price'] = df_transactions['units']*df_transactions['unit_price']

    df_transactions = df_transactions.sort_values(by=['Date'])

    return df_transactions
# ---------------------------------------------------------------------------------------------------------------------


dfs = []
# ignore case of the extension
# this is a workaround. For robust use of ignoring case regex needs to be used
ext = ["*.qfx", "*.QFX"]
files = []
for e in ext:
    files.extend(glob(e))

for qfx_file in files:
    print("Reading ...", qfx_file)
    f = open(qfx_file, "r", encoding="utf-8")
    qfx = OfxParser.parse(f)
    df1 = exporttransactions(qfx)
    dfs.append(df1)

df = pd.concat(dfs)
df=df.drop_duplicates()
df = df.sort_values(by=['Date']).set_index('Date')

# export data to CSV
outputfilename = '401kexport.csv'

df.to_csv(outputfilename)
print("Output written to:", outputfilename)

# find total contribution and dividends
print("Total Contribution:", df[(df['memo'] == 'Contribution')]['price'].sum())
print("Total Dividends:", df[(df['memo'] == 'Dividends and Earnings')]['price'].sum())

