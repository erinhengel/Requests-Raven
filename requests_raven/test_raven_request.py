# -*- coding: utf-8 -*-

from raven_request import *
from bs4 import BeautifulSoup
import sqlite3
import random
import os
import time
import codecs
from urllib.parse import urlparse, parse_qs
import pprint

conn = sqlite3.connect('/Users/erinhengel/Dropbox/Readability/dta/read.db')
conn.text_factory = str
csql = conn.cursor()
dois = csql.execute("SELECT DOI FROM Articles WHERE Journal = 'QJE';").fetchall()

dois = list(sum(dois,()))
print('{} articles to do\n'.format(len(dois)))
dois = dois[130:]
# dois = random.sample(dois, 5)
# dois = ['10.1093/qje/qjs074']

print("Downloading {}.".format(len(dois)))

deets = {'userid': 'eh403', 'pwd': 'pringleHengel'}
c = OxfordQJE(login=deets)

n = 1;
pp = pprint.PrettyPrinter(indent=4)
for doi in dois:
    print("\n{}\t{}".format(n, doi))

    bibtex = c.ref(doi, affiliation=True)
    for author in bibtex['authors']:
        print("\t{}\n\t\t{}".format(author['name'], author['affiliation']))
    n+=1
    time.sleep(2)
    
conn.close()