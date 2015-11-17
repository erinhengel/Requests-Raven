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
        Download html of document's webpage.
        Download pdf of document.
    """
    def __init__(self, login):
        Raven.__init__(self, url='http://www.jstor.org', login=login)
    
    def pdf(self, id, params={'acceptTC': 'true'}, redirect=4):
        """ Download pdf of document. """
        
        for n in range(0, redirect):
            request = self.session.get(self.url+'/stable/pdfplus/'+id+'.pdf', params=params)
            if 'application/pdf' in request.headers['Content-Type']:
                return request.content
        print("PDF not found.")
    
    def html(self, id):
        """ Download html of document's webpage. """
        request = self.session.get(self.url+'/stable/info/'+id)
        return request.text
        
    def ref(self, id, affiliation=False):
        """ Download bibliographic data of document. """
        request = self.session.get(self.url+'/citation/text/'+id)
        try:
            parser = BibTexParser()
            parser.customization = convert_to_unicode
            bibtex = bibtexparser.loads(request.text, parser=parser).entries[0]
            bibtex['author'] = list(map(str.strip, bibtex['author'].split(',')))
        except IndexError:
            return
        
        if affiliation:
            html = self.html(id=id)
            soup = BeautifulSoup(html, 'html.parser')
            
            authinfo = soup.find('div', class_='authorInfo')
            authors = []
            for author in bibtex['author']:
                authdict = {'name':author}
                if authinfo:
                    regex = '\s'.join(author.split())
                    affiliation = authinfo.find(string=re.compile(regex, re.UNICODE))
                    if affiliation:
                        authdict['affiliation'] = affiliation.next_element.string.strip()
                authors.append(authdict)
            bibtex['author'] = authors
        
        return bibtex
        
class EHOST(Raven):
    """ Create Raven connection to www.ebscohost.com.
        Download html of document's webpage.
        Download pdf of document.
    """
    def __init__(self, login):
        Raven.__init__(self, url='http://search.ebscohost.com/login.aspx', login=login)
    
    def page(self, id):
        params = {
            'direct': 'true',
            'db': 'bth',
            'AN': str(id),
            'site':'ehost-live',
            'scope':'site'
        }
        request = self.session.get(self.url, params=params)
        return request
    
    def pdf(self, id):
        request = self.page(id)
        url_ps = urlparse(request.url)
        url_qy = parse_qs(url_ps.query)
        viewer_url = url_ps.scheme + '://' + url_ps.netloc + '/ehost/pdfviewer/pdfviewer'
        params = {
            'sid': url_qy['sid'][0],
            'vid': url_qy['vid'][0],
            'hid': url_qy['hid'][0]
        }
        request = self.session.get(viewer_url, params=params)
        soup = BeautifulSoup(request.text, 'html.parser')
        pdf_url = soup.find(attrs={'name': 'pdfUrl'}).attrs['value']
        request = self.session.get(pdf_url)
        return request.content
    
    def html(self, id):
        request = self.page(id)
        return request.text

