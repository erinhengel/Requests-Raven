#-*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import requests
import re
import os
import sys
from urllib.parse import urlparse, parse_qs


class Raven(object):
    def __init__(self, url, login):
        self.session = requests.Session()
        
        ezproxy = "http://ezproxy.lib.cam.ac.uk:2048/login"
        raven_login = 'https://raven.cam.ac.uk/auth/authenticate2.html'

        # Log into Raven.
        login['submit'] = 'Login'
        self.session.post(raven_login, data=login)
        
        # SAML request.
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
        saml['SAMLResponse'] = soup.find(attrs={'name': 'SAMLResponse'})['value']
        saml['url2'] = soup.find('form')['action']
        
        # Final post.
        post = self.session.post(saml['url2'], data=saml)
        self.url = post.url


class JSTOR(Raven):
    def __init__(self, login):
        Raven.__init__(self, url='http://www.jstor.org', login=login)

    def pdf(self, doi, params={'acceptTC': 'true'}, redirect=4):
        for n in range(0, redirect):
            request = self.session.get(self.url+'/stable/pdfplus/'+doi+'.pdf', params=params)
            if 'application/pdf' in request.headers['Content-Type']:
                return request.content
        print("PDF not found.")


    def html(self, doi):
        request = self.session.get(self.url+'/stable/'+doi)
        return request.text


class EHOST(Raven):
    def __init__(self, login):
        Raven.__init__(self, url='http://search.ebscohost.com/login.aspx', login=login)
    
    def page(self, doi):
        params = {
            'direct': 'true',
            'db': 'bth',
            'AN': str(doi),
            'site':'ehost-live',
            'scope':'site'
        }
        request = self.session.get(self.url, params=params)
        return request
    
    def html(self, doi):
        request = self.page(doi)
        return request.text
        
    def pdf(self, doi):
        request = self.page(doi)
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


