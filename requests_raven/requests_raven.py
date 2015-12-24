# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import requests
import re
import os
import sys
from urllib.parse import urlparse, parse_qs
import traceback
import getpass
import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode
import xmltodict


class Raven(object):
    """ Creates a custom Requests class to:
            1. authenticate the Raven user;
            2. complete the SAML handshake;
            3. access the destination URL.
        Requests Session object stored in session attribute for reuse.
    """
    def __init__(self, url, login={}):
        
        # Ask for username and password if not supplied.
        if 'userid' not in login:
            login['userid'] = input('CRSid (userid): ')
        if 'pwd' not in login:
            login['pwd'] = getpass.getpass(stream=sys.stderr, prompt='Raven password (pwd): ')
        
        # Input value to submit form.
        login['submit'] = 'Login'
        
        # Start session and store in session attribute.
        self.session = requests.Session()
        
        # Log into Raven.
        raven_login = 'https://raven.cam.ac.uk/auth/authenticate2.html'
        self.session.post(raven_login, data=login)
        
        # SAML request.
        ezproxy = "http://ezproxy.lib.cam.ac.uk:2048/login"
        request = self.session.get(ezproxy+'?url='+url)
        soup = BeautifulSoup(request.text, 'html.parser')
        saml = {
            'SAMLRequest': soup.find(attrs={'name': 'SAMLRequest'})['value'],
            'RelayState': soup.find(attrs={'name': 'RelayState'})['value'],
            'url1': soup.find(attrs={'name': 'EZproxyForm'})['action']
        }
        
        # SAML response.
        response = self.session.post(saml['url1'], data=saml)
        soup = BeautifulSoup(response.text, 'html.parser')
        try:
            saml['SAMLResponse'] = soup.find(attrs={'name': 'SAMLResponse'})['value']
            saml['url2'] = soup.find('form')['action']
        except TypeError: # Username and password probably entered incorrectly.
            traceback.print_exc(file=sys.stdout)
            print("You're getting this error probably because your CRSid or password are incorrect.")
            print("If this error persists, we have a problem so say something: github.com/erinhengel/raven-request.")
            sys.exit(1)
        
        # Complete SAML handshake.
        post = self.session.post(saml['url2'], data=saml)
        
        # Save destination URL.
        self.url = post.url


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
        for n in range(len(a_info['au'])):
            if affiliation:
                authors.append({'name': a_info['au'][n], 'affiliation': a_info['affil'][n]})
            else:
                authors.append({'name': a_info['au'][n]})
        bibtex['authors'] = authors
        
        return bibtex
        
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
        
        frame_link = soup.find(attrs={'rel': 'full-text.pdf'})['href']
        issue = re.search('(content|reprint)/(?P<vol>\d+)/(?P<num>\d+)/(?P<page>\d+).*\?sid=(?P<sid>.*)', frame_link).groupdict()
        
        html_link = '{}/content/{}/{}/{}.abstract?sid={}'.format(self.url, issue['vol'], issue['num'], issue['page'], issue['sid'])
        pdf_link = '{}/content/{}/{}/{}.full.pdf'.format(self.url, issue['vol'], issue['num'], issue['page'])
        
        return {'html': html_link, 'pdf': pdf_link, 'issue': issue}
    
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
        if file:
            with open(file, 'wb') as fh:
                fh.write(mypdf)
        
        return mypdf
    
    def ref(self, id, affiliation=False):
        """ Download bibliographic data of document. 
            If affiliation, find institutions affiliated with authors. """
        
        # Export Bibtex.
        links = self.search(id)
        gca = 'qje;{}/{}/{}'.format(links['issue']['vol'], links['issue']['num'], links['issue']['page'])
        params = {'type': 'bibtex', 'gca' : gca}
        request = self.session.get(self.url+'/citmgr', params=params)
        
        # Parse Bibtex.
        text = request.content.decode('utf8').replace(u'\xa0', u' ')
        try:
            parser = BibTexParser()
            parser.customization = convert_to_unicode
            bibtex = bibtexparser.loads(text, parser=parser).entries[0]
        except IndexError:
            return
        
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
                    
        return bibtex
