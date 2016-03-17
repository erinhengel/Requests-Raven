# -*- coding: utf-8 -*-

from requests_raven import Raven
import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode
from bs4 import BeautifulSoup
import re

class OxfordQJE(Raven):
    """ Create Raven connection to www.oxfordjournals.com.
        Download HTML of document's webpage.
        Download PDF of document.
        Download bibliographic data of document.
    """
    
    def __init__(self, login):
        # Establish a Raven connection object.
        Raven.__init__(self, url='http://qje.oxfordjournals.org', login=login)
        
    def search(self, id):
        # Access links from DOI search; to be used by pdf, html & ref methods.
        params = {'submit': 'yes', 'doi': id}
        search_url = self.url + '/search'
        request = self.session.get(search_url, params=params)
        soup = BeautifulSoup(request.text, 'html.parser')
        
        # HTML appears to have changed; added new way to obtain link.
        try:
            frame_link = soup.find(attrs={'rel': 'full-text.pdf'})['href']
            issue = re.search('(content|reprint)/(?P<vol>\d+)/(?P<num>\d+)/(?P<page>\d+).*\?sid=(?P<sid>.*)', frame_link).groupdict()
            gca = 'qje;{}/{}/{}'.format(issue['vol'], issue['num'], issue['page'])
            html_link = '{}/content/{}/{}/{}.abstract?sid={}'.format(self.url, issue['vol'], issue['num'], issue['page'], issue['sid'])
            pdf_link = '{}/content/{}/{}/{}.full.pdf'.format(self.url, issue['vol'], issue['num'], issue['page'])
            
        except AttributeError:
            found_html = soup.find('div', 'cit-extra')
            html_link = found_html.find(attrs={'rel': 'abstract'})['href']
            pdf_link = found_html.find(attrs={'rel': 'full-text.pdf'})['href'].replace('pdf+html', 'pdf')
            gca = soup.find(attrs={'name': 'gca'})['value']
        
        return {'html': html_link, 'pdf': pdf_link, 'gca': gca}
    
    def html(self, id):
        """ Download HTML of document's webpage. """
        links = self.search(id)
        request = self.session.get(links['html'])
        return request.text
        
    def pdf(self, id, file=None):
        """ Download PDF of document.
            If file supplied, save to local disk. """
            
        links = self.search(id)
        request = self.session.get(links['pdf'])
        
        # Save locally if file specified.
        mypdf = request.content
        # TO DO: CHECK TO MAKE SURE ITS A PDF.
        if file:
            with open(file, 'wb') as fh:
                fh.write(mypdf)
        
        return mypdf
    
    def ref(self, id, affiliation=False, standardised=False):
        """ Download bibliographic data of document. 
            If affiliation, find institutions affiliated with authors. """
        
        # Export Bibtex.
        links = self.search(id)
        
        params = {'type': 'bibtex', 'gca' : links['gca']}
        request = self.session.get(self.url+'/citmgr', params=params)
        
        # Parse Bibtex.
        text = request.content.decode('utf8').replace(u'\xa0', u' ')
        try:
            parser = BibTexParser()
            parser.customization = convert_to_unicode
            bibtex = bibtexparser.loads(text, parser=parser).entries[0]
        except IndexError:
            return
        
        # Make sure you got the right record!
        assert id == bibtex['doi']
        
        bibtex['authors'] = bibtex.pop('author')
        bibtex['authors'] = list(map(str.strip, bibtex['authors'].split(' and ')))
        bibtex['authors'] = [{'name': x} for x in bibtex['authors']]
        
        # If affiliation keyword is true, attempt to find each author's affiliation
        # in the text of the HTML.
        if affiliation:
            request = self.session.get(links['html'])
            soup = BeautifulSoup(request.text, 'html.parser')
            
            try:
                citation_authors = soup.find("ol", class_="affiliation-list").find_all('address')
                citation_authors = [x.text.strip() for x in citation_authors if x != '\n']
                if len(citation_authors) == len(bibtex['authors']):
                    for n in range(len(bibtex['authors'])):
                        bibtex['authors'][n]['affiliation'] = citation_authors[n]
                else:
                    for n in range(len(bibtex['authors'])):
                        bibtex['authors'][n]['affiliation'] = ' '.join(citation_authors)
            except AttributeError:
                for n in range(len(bibtex['authors'])):
                    bibtex['authors'][n]['affiliation'] = None
        
        # If standardised, return a standardised set of bibliographic information;
        # otherwise, ref returns whatever is returned by Oxford's citation tool.
        if standardised:
            standard = {
                'Volume': int(bibtex['volume']),
                'Issue': bibtex['number'],
                'Title': bibtex['title'].strip(),
                'Journal': 'QJE',
                'DOI': bibtex['doi'],
                'Abstract': bibtex['abstract'].strip(),
                'JEL': [],
                'Authors': []
            }

            # Publication date.
            if bibtex['number'] == '1':
                standard['PubDate'] = '{}-02-01'.format(bibtex['year'])
            elif bibtex['number'] == '2':
                standard['PubDate'] = '{}-05-01'.format(bibtex['year'])
            elif bibtex['number'] == '3':
                standard['PubDate'] = '{}-08-01'.format(bibtex['year'])
            elif bibtex['number'] == '4':
                standard['PubDate'] = '{}-11-01'.format(bibtex['year'])
            elif bibtex['number'] == 'Supplement':
                standard['PubDate'] = '{}-01-01'.format(bibtex['year'])

            # Page numbers.
            pages = bibtex['pages'].split('-')
            standard['FirstPage'] = int(pages[0])
            standard['LastPage'] = int(pages[1])
            if standard['LastPage'] < standard['FirstPage']:
                substr = len(str(standard['FirstPage'])) - len(str(standard['LastPage']))
                standard['LastPage'] = int(str(standard['FirstPage'])[:substr] + str(standard['LastPage']))
    
            # Find JEL classification codes.
            jel_regex = re.compile(r'(.*) JEL Codes?: (.*)\.$')
            jel_regex_match = jel_regex.search(bibtex['abstract'])
            if jel_regex_match:
                standard['Abstract'] = jel_regex_match.group(1).strip()
                standard['JEL'] = [x.strip() for x in jel_regex_match.group(2).split(',')]

            # Author
            for author in bibtex['authors']:
                aut = {'Name': author['name']}
                if 'affiliation' in author:
                    aut['Affiliation'] = author['affiliation']
                standard['Authors'].append(aut)
            
            bibtex = standard
                    
        return bibtex
