# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import requests
import sys
import traceback
import getpass


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
        