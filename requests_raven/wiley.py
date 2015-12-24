# -*- coding: utf-8 -*-

from requests_raven import Raven
from bs4 import BeautifulSoup
import re

class Wiley(Raven):
    """ Create Raven connection to onlinelibrary.wiley.com.
        Download HTML of document's webpage.
        Download PDF of document.
        Download bibliographic data of document.
    """
    
    def __init__(self, login):
        # Establish a Raven connection object.
        Raven.__init__(self, url='http://onlinelibrary.wiley.com', login=login)
        
    def html(self, id):
        """ Download HTML of document's webpage. """
        url = '{}/doi/{}/abstract'.format(self.url, id)
        request = self.session.get(url)
        return request.text
        
    def pdf(self, id, file=None):
        """ Download PDF of document.
            If file supplied, save to local disk. """
        
        # Get the webpage of the PDF; find the redirect URL in HTML to access PDF.
        pdf_url = '{}/doi/{}/pdf'.format(self.url, id)
        request = self.session.get(pdf_url)
        soup = BeautifulSoup(request.text, 'html.parser')
        pdf_url = soup.find(attrs={'id': 'pdfDocument'}).attrs['src']
        request = self.session.get(pdf_url)
        
        # Save locally if file specified.
        mypdf = request.content
        if file:
            with open(file, 'wb') as fh:
                fh.write(mypdf)
        
        return mypdf
        
    def ref(self, id, affiliation=False):
        """ Download bibliographic data of document. 
            If affiliation, find institutions affiliated with authors. """
        
        # Clean text, remove whitespace.
        def text_clean(string):
            return string.strip().replace(u'\xa0', u' ')
        
        # Find affiliation given an author's name.
        def find_affiliation(next_element, n):
            if next_element['name'] == 'citation_author_institution':
                bibtex['authors'][n]['affiliation'] = text_clean(next_element['content'])
                return True
        
        # Get bibliographic information using Wiley's export function.
        ref_url = '{}/documentcitationdownloadformsubmit'.format(self.url)
        payload = {
            'fileFormat': 'PLAIN_TEXT',
            'hasAbstract': 'CITATION_AND_ABSTRACT',
            'doi': id
        }
        request = self.session.post(ref_url, data=payload)
        raw_text = list(iter(request.text.splitlines()))
        bibtex = {'authors': [], 'keywords': []}
        for item in raw_text:
            match = re.match('(?P<key>[A-Z]{2})\s{2}-\s(?P<value>.*)', item)
            if match:
                value = match.group('value')
                key = match.group('key')
                if key =='AU':
                    bibtex['authors'].append({'name': value})
                elif key == 'TI':
                    bibtex['title'] = text_clean(value)
                elif key == 'JO':
                    bibtex['journal'] = text_clean(value)
                elif key == 'VL':
                    bibtex['volume'] = text_clean(value)
                elif key == 'IS':
                    bibtex['issue'] = text_clean(value)
                elif key == 'PB':
                    bibtex['publisher'] = text_clean(value)
                elif key == 'SP':
                    bibtex['start_page'] = text_clean(value)
                elif key == 'EP':
                    bibtex['end_page'] = text_clean(value)
                elif key == 'KW':
                    bibtex['keywords'].append(text_clean(value))
                elif key == 'PY':
                    bibtex['year'] = text_clean(value)
                elif key == 'AB':
                    bibtex['abstract'] = text_clean(value)
        
        # If affiliation keyword is true, attempt to find each author's affiliation
        # in the text of the HTML.
        if affiliation:
            abstract_url = '{}/doi/{}/abstract'.format(self.url, id)
            request = self.session.get(abstract_url)
            soup = BeautifulSoup(request.text, 'html.parser')
            
            n = -1
            citation_authors = soup.find_all(attrs={'name': 'citation_author'})
            for author in bibtex['authors']:
                n += 1
                found = False
                
                # Try to find an exact match.
                for citation_author in citation_authors:
                    if citation_author['content'] == author['name']:
                        found = find_affiliation(citation_author.next_element, n)
                        break
                if found: continue
                
                # Try to find match using author's last name.
                nlist = author['name'].split(', ')
                for citation_author in citation_authors:
                    citation_nlist = citation_author['content'].split(', ')
                    if citation_nlist[0].strip() == nlist[0].strip():
                        found = find_affiliation(citation_author.next_element, n)
                        break
                if found: continue
                
                # Try to find match using author's first name.
                for citation_author in citation_authors:
                    citation_nlist = citation_author['content'].split(', ')
                    if citation_nlist[1].strip() == nlist[1].strip():
                        found = find_affiliation(citation_author.next_element, n)
                        break
                if found: continue
                
                # Return None if no author found.
                bibtex['authors'][n]['affiliation'] = None
                
            n = 0
            for author in bibtex['authors']:
                bibtex['authors'][n]['name'] = text_clean(author['name'])
                n += 1
            
        return bibtex
