#!/usr/bin/env python3

import retirementportfolio as rt
import pandas as pd
import matplotlib.pyplot as plt

# -------------------------- MAIN MODULE --------------------------

portfolio = rt.retirementportfolio(importquicken=True)
dfcontrib = portfolio.gencontrib()
currentval = portfolio.getcurrentportfoliovalue()

tickerlist = ['SPY', 'QQQ', 'IWM', 'IBB', 'BND', 'VGT', 'UPRO', 'TQQQ', 'VNQ', 'GLD', 'AAPL', 'MSFT', 'AMZN',
              'GITAX', 'VITAX', 'HAGAX', 'KO', 'COST', 'BABA', 'T', 'TMUS']

# smaller list for testing purposes
# tickerlist = ['SPY', 'QQQ', 'IWM']

df = []
for tickr in tickerlist:
    ret = portfolio.getreturn(dfcontrib, tickr)
    df.append(ret)

df = pd.DataFrame(df, columns=['ticker', 'excessreturn', 'yoyreturn', 'totreturn'])

print(portfolio.summary())

print(df)

df.to_csv('comparereturns.csv')
df.plot(kind='bar', x='ticker', y='excessreturn')
plt.show()

