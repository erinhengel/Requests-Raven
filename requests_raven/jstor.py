# -*- coding: utf-8 -*-

from requests_raven import Raven
import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode
from bs4 import BeautifulSoup

class JSTOR(Raven):
    """ Create Raven connection to www.jstor.org.
        Download HTML of document's webpage.
        Download PDF of document.
        Download bibliographic data of docuemnt.
    """
    def __init__(self, login):
        # Establish a Raven connection object.
        Raven.__init__(self, url='http://www.jstor.org', login=login)
    
    def html(self, id):
        """ Download html of document's webpage. """
        html_url = '{}/stable/info/{}'.format(self.url, id)
        request = self.session.get(html_url)
        return request.text
    
    def pdf(self, id, file=None, params={'acceptTC': 'true'}, redirect=4):
        """ Download pdf of document.
            If file supplied, save to local disk. """
        
        # Downloading PDFs on JSTOR requires accepting the TOCs (done via acceptTC=true in params).
        # Need to make initial request and then a second request the first time you download a PDF
        # using your Raven object. Set to make a maximum of 4 requests, just to be safe.
        for n in range(0, redirect):
            pdf_url = '{}/stable/pdfplus/{}.pdf'.format(self.url, id)
            request = self.session.get(pdf_url, params=params)
            if 'application/pdf' in request.headers['Content-Type']:
                mypdf = request.content
                if file:
                    with open(file, 'wb') as fh:
                        fh.write(mypdf)
                return mypdf
        
        # If number of redirects exceeded, return None.
        print("PDF not found.")
        return
    
    def ref(self, id, affiliation=False):
        """ Download bibliographic data of document. 
            If affiliation, find institutions affiliated with authors. """
        
        ref_url = '{}/citation/text/{}'.format(self.url, id)
        request = self.session.get(ref_url)
        text = request.content.decode('utf8').replace(u'\xa0', u' ')
        
        # Parse BibTeX.
        try:
            parser = BibTexParser()
            parser.customization = convert_to_unicode
            bibtex = bibtexparser.loads(text, parser=parser).entries[0]
        except IndexError:
            return
        
        # Change 'author' to list of dictionaries with key value 'authors'. 
        bibtex['authors'] = bibtex.pop('author')
        bibtex['authors'] = list(map(str.strip, bibtex['authors'].split(',')))
        bibtex['authors'] = [{'name': x} for x in bibtex['authors']]
        
        bibtex['issn'] = list(map(str.strip, bibtex['issn'].split(',')))
        bibtex['year'] = int(bibtex['year'])
        
        # If affiliation keyword is true, attempt to find each author's affiliation
        # in the text of the HTML.
        if affiliation:
            html = self.html(id=id)
            soup = BeautifulSoup(html, 'html.parser')
            authinfo = soup.find('div', class_='authorInfo')
            print(authinfo)
            if authinfo:
                for n in range(len(bibtex['authors'])):
                    regex = '\s'.join(bibtex['authors'][n]['name'].split())
                    affiliation = authinfo.find(string=re.compile(regex, re.UNICODE))
                    if affiliation:
                        bibtex['authors'][n]['affiliation'] = affiliation.next_element.string.strip()
                        
        return bibtex
