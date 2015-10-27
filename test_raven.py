from raven import *

# EHOST
c = EHOST(login={'userid': 'eh403', 'pwd': 'pringleHengel'})

html = c.html(doi='53725320')
soup = BeautifulSoup(html, 'html.parser')
print(soup.title.text)

pdf = c.pdf(doi='53725320')
with open('/Users/erinhengel/Desktop/53725320.pdf', 'wb') as fh:
    fh.write(pdf)

# JSTOR
c = JSTOR(login={'userid': 'eh403', 'pwd': 'pringleHengel'})

html = c.html(doi='10.1086/682574')
soup = BeautifulSoup(html, 'html.parser')
print(soup.title.text)

pdf = c.pdf(doi='10.1086/682574')
with open('/Users/erinhengel/Desktop/682574.pdf', 'wb') as fh:
    fh.write(pdf)
    
    