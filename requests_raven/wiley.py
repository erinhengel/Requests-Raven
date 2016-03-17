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
                bibtex['Authors'][n]['Affiliation'] = text_clean(next_element['content'])
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
        bibtex = {'Authors': [], 'Keywords': []}
        for item in raw_text:
            match = re.match('(?P<key>[A-Z]{2})\s{2}-\s(?P<value>.*)', item)
            if match:
                value = match.group('value')
                key = match.group('key')
                if key =='AU':
                    bibtex['Authors'].append({'Name': value})
                elif key == 'TI':
                    bibtex['Title'] = text_clean(value)
                elif key == 'JO':
                    bibtex['Journal'] = text_clean(value)
                elif key == 'VL':
                    bibtex['Volume'] = int(text_clean(value))
                elif key == 'IS':
                    bibtex['Issue'] = text_clean(value)
                elif key == 'PB':
                    bibtex['Publisher'] = text_clean(value)
                elif key == 'SP':
                    bibtex['FirstPage'] = int(text_clean(value))
                elif key == 'EP':
                    bibtex['LastPage'] = int(text_clean(value))
                elif key == 'KW':
                    bibtex['Keywords'].append(text_clean(value))
                elif key == 'PY':
                    bibtex['Year'] = text_clean(value)
                elif key == 'AB':
                    bibtex['Abstract'] = text_clean(value)
                elif key == 'DO':
                    bibtex['DOI'] = text_clean(value)
                elif key == 'SN':
                    bibtex['ISSN'] = text_clean(value)
                elif key == 'PY':
                    bibtex['PubDate'] = int(text_clean(value))
        
        # If affiliation keyword is true, attempt to find each author's affiliation
        # in the text of the HTML.
        if affiliation:
            abstract_url = '{}/doi/{}/abstract'.format(self.url, id)
            request = self.session.get(abstract_url)
            soup = BeautifulSoup(request.text, 'html.parser')
            
            n = -1
            citation_authors = soup.find_all(attrs={'name': 'citation_author'})
            for author in bibtex['Authors']:
                n += 1
                found = False
                
                # Try to find an exact match.
                for citation_author in citation_authors:
                    if citation_author['content'] == author['Name']:
                        found = find_affiliation(citation_author.next_element, n)
                        break
                if found: continue
                
                # Try to find match using author's last name.
                nlist = author['Name'].split(', ')
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
                bibtex['Authors'][n]['Affiliation'] = None
                
            n = 0
            for author in bibtex['Authors']:
                bibtex['Authors'][n]['Name'] = text_clean(author['Name'])
                n += 1
        
        # If standardised, return a standardised set of bibliographic information;
        # otherwise, ref returns whatever is returned by Wiley's citation tool.
        
        # TO DO.
            
        return bibtex
