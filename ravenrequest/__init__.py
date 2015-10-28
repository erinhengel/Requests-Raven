#-*- coding: utf-8 -*-
"""
Raven Request is a custom Requests class to log onto Raven, the University of Cambridge's central
web authentication service. Basic usage:
    
    >>> from ravenrequest import Raven
    >>> deets = {'userid': 'ab123', 'pwd': 'XXXX'}
    >>> s = Raven(url='http://www.example.com', login=deets).session
    
JSTOR and EHOST are Raven subclasses specifically for logging onto www.jstor.org and
www.ebscohost.com, respectively.
    
    >>> from ravenrequest import JSTOR
    >>> id = '10.1086/682574'
    >>> conn = JSTOR(login=deets)
    >>> html = conn.html(doi=id)
    >>> html.text
    ...
    >>> pdf = conn.pdf(doi=id)
    >>> open('file.pdf', 'wb').write(pdf)
    
Full documentation at <http://www.erinhengel.com/software/raven>.

:copyright: (c) 2015 by Erin Hengel.
:license: Apache 2.0, see LICENSE for more details.

"""

__title__ = 'ravenrequest'
__version__ = '0.0.1'
__author__ = 'Erin Hengel'
__license__ = 'Apache 2.0'
__copyright__ = 'Copyright 2015 Erin Hengel'

from .ravenrequest import *
