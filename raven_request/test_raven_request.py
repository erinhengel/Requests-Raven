# -*- coding: utf-8 -*-

from raven_request import *
# from raven import EHOST, JSTOR
from bs4 import BeautifulSoup
import sqlite3
import random

conn = sqlite3.connect('/Users/erinhengel/Dropbox/Readability/dta/read.db')
csql = conn.cursor()
dois = csql.execute("SELECT DOI FROM Articles WHERE DOI LIKE '10.1086%';").fetchall()
dois = random.sample(list(sum(dois,())), 5)
conn.close()

# # EHOST
# c = EHOST(login={'userid': 'eh403', 'pwd': 'pringleHengel'})
#
# html = c.html(id='53725320')
# soup = BeautifulSoup(html, 'html.parser')
# print(soup.title.text.strip())
#
# pdf = c.pdf(id='53725320')
# with open('/Users/erinhengel/Desktop/53725320.pdf', 'wb') as fh:
#     fh.write(pdf)

# JSTOR
c = JSTOR(login={'userid': 'eh403', 'pwd': 'pringleHengel'})

for doi in dois:
    print(doi)
    html = c.html(id=doi)
    soup = BeautifulSoup(html, 'html.parser')
    print(soup.title.text.strip())

    pdf = c.pdf(id=doi)
    with open('/Users/erinhengel/Desktop/'+doi, 'wb') as fh:
        fh.write(pdf)

    c.url
    ref = c.ref(id=doi, affiliation=True)
    if ref:
        for author in ref['author']:
            print(author)
            