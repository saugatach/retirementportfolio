# stockanalysis

To run the code use

$ python3 stock-analysis.py

needs pandas-datareader==0.5.0

will not work with pandas-datareader==0.6.0

If you have pandas-datareader==0.6.0 installed then either uninstall 0.6.0 and 
install 0.5.0 or create a conda environment with pandas-datareader==0.5.0




Common errors:

1. Dateutil errors

Multiple errors of the form

--AttributeError: module 'dateutil' has no attribute '__version__'	

can occur when the wrong or multiple versions of dateutil package is installed

Solution: Remove all dateutil packages by

$ pip3 uninstall python-dateutil

Repeat till pip3 produces error

--Cannot uninstall requirement python-dateutil, not installed

Now install a fresh python-dateutil package 

$ pip3 install python-dateutil --upgrade

2. pandas import fails

--ImportError: cannot import name 'is_list_like'

This is an error in the file fred.py because is_list_like has been moved from 
pandas.core.common to pandas.api.types

Solution:

Go to the local python repositoy

$ cd ~/.local/lib/python3.5/site-packages/pandas_datareader

$ gedit fred.python

Replace 

from pandas.core.common import is_list_like

with

from pandas.api.types import is_list_like




