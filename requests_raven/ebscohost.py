# -*- coding: utf-8 -*-

from requests_raven import Raven
from urllib.parse import urlparse, parse_qs
import xmltodict
from bs4 import BeautifulSoup
from pprint import pprint

class EBSCOhost(Raven):
    """ Create Raven connection to www.ebscohost.com.
        Download HTML of document's webpage.
        Download PDF of document.
    """
    def __init__(self, login):
        # Establish a Raven connection object.
        Raven.__init__(self, url='http://search.ebscohost.com/login.aspx', login=login)
    
    def page(self, id, db='bth'):
        # Access webpage; to be used by pdf, html & ref methods.
        params = {
            'direct': 'true',
            'db': db,
            'AN': str(id),
            'site':'ehost-live',
            'scope':'site'
        }
        request = self.session.get(self.url, params=params)
        return request
    
    def html(self, id, db='bth'):
        """ Download HTML of document's webpage. """
        request = self.page(id, db)
        return request.text
    
    def pdf(self, id, file=None, db='bth'):
        """ Download PDF of document.
            If file supplied, save to local disk. """
            
        # Get the webpage of the document.
        request = self.page(id, db)
        url_ps = urlparse(request.url)
        url_qy = parse_qs(url_ps.query)
        viewer_url = '{}://{}/ehost/pdfviewer/pdfviewer'.format(url_ps.scheme, url_ps.netloc)
        params = {
            'sid': url_qy['sid'][0],
            'vid': url_qy['vid'][0],
            'hid': url_qy['hid'][0]
        }
        request = self.session.get(viewer_url, params=params)
        
        # Find the PDF URL; save locally if file specified.
        soup = BeautifulSoup(request.text, 'html.parser')
        pdf_url = soup.find(attrs={'name': 'pdfUrl'}).attrs['value']
        request = self.session.get(pdf_url)
        mypdf = request.content
        if file:
            with open(file, 'wb') as fh:
                fh.write(mypdf)
        
        return mypdf
        
    def ref(self, id, db='bth'):
        """ Download bibliographic data of document. 
            If affiliation, find institutions affiliated with authors. """
        
        # Get the webpage of the document. Using parameters from initial GET,
        # construct URL to access EBSCOhost's bibliography export function.
        request = self.page(id, db)
        url_ps = urlparse(request.url)
        url_qy = parse_qs(url_ps.query)        
        export_url = '{}://{}/ehost/delivery/ExportPanelSave/{}__{}__AN'.format(url_ps.scheme, url_ps.netloc, db, id)
        params = {
            'sid': url_qy['sid'][0],
            'vid': url_qy['vid'][0],
            'hid': url_qy['hid'][0],
            'bdata': url_qy['bdata'],
            'theExportFormat': 6
        }        
        request = self.session.get(export_url, params=params)
        
        # Parse XML into dictionary.
        root = xmltodict.parse(request.text)
        data = root['records']['rec']['header']
        bibtex = {
            'AN': data['@uiTerm'],
            'url': data['displayInfo']['pLink']['url'],
            'shortDbName': data['@shortDbName'],
            'longDbName': data['@longDbName'],
            'journal': data['controlInfo']['jinfo']['jtl'],
            'issn': data['controlInfo']['jinfo']['issn'],
            'year': data['controlInfo']['pubinfo']['dt']['@year'],
            'month': data['controlInfo']['pubinfo']['dt']['@month'],
            'vol': data['controlInfo']['pubinfo']['vid'],
            'no': data['controlInfo']['pubinfo']['iid'],
            'pg': data['controlInfo']['artinfo']['ppf'],
            'pg_count': data['controlInfo']['artinfo']['ppct'],
            'title': data['controlInfo']['artinfo']['tig']['atl'],
            'subject': [x['#text'] for x in data['controlInfo']['artinfo']['sug']['subj']],
            'abstract': data['controlInfo']['artinfo']['ab'],
            'pubtype': data['controlInfo']['artinfo']['pubtype'],
            'doctype': data['controlInfo']['artinfo']['doctype']
        }
        
        # If author affiliations are available, return in author names & affiliations in
        # dictionary format.
        a_info = data['controlInfo']['artinfo']['aug']
        affiliation = any('affil' in item for item in a_info.items())
        authors = []
        # ERROR; FIXED: Single authored articles come out [{'name': J}, {'name': o}, ...]
        # Solo-authors are strings.
        if isinstance(a_info['au'], str):
            if affiliation:
                authors.append({'name': a_info['au'], 'affiliation': a_info['affil']})
            else:
                authors.append({'name': a_info['au']})
        # Multiple authors are lists.
        else:
            for n in range(len(a_info['au'])):
                if affiliation:
                    # If only one affiliation for all authors.
                    if isinstance(a_info['affil'], str):
                        authors.append({'name': a_info['au'][n], 'affiliation': a_info['affil']})
                    # If more or fewer affiliations than authors.
                    elif len(a_info['affil']) != len(a_info['au']):
                        authors.append({'name': a_info['au'][n], 'affiliation': ' '.join(a_info['affil'])})
                    # If number of affiliations equals number of authors.
                    else:
                        authors.append({'name': a_info['au'][n], 'affiliation': a_info['affil'][n]})
                else:
                    authors.append({'name': a_info['au'][n]})
        bibtex['authors'] = authors
        
        return bibtex
