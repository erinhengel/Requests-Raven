Requests-Raven
==============

Requests-Raven is a custom `Requests <http://requests.readthedocs.org/en/latest/>`_ class to log onto `Raven <https://raven.cam.ac.uk>`_, the University of Cambridge's central
web authentication service.


Installation
------------
	
.. code-block:: bash

	$ pip install requests_raven


Documentation
-------------

Detailed documentation available at `erinhengel.com/software/requests_raven <http://www.erinhengel.com/software/requests-raven/>`_. 


Quickstart
----------

The ``Raven`` class logs onto Raven and establishes a connection with the host. The ``session`` attribute
returns a `Request Session object <http://requests.readthedocs.org/en/latest/user/advanced/#session-objects>`_
with all the methods of the main `Requests API <http://requests.readthedocs.org/en/latest/>`_.


.. code-block:: python

    >>> from requests_raven import Raven
	
    # Establish Raven connection object for the website http://qje.oxfordjournals.org.
    >>> deets = {'userid': 'ab123', 'pwd': 'XXXX'}
    >>> conn = Raven(url='http://qje.oxfordjournals.org', login=deets)
	
    # The final destination url looks something like this.
    >>> conn.url
    'http://libsta28.lib.cam.ac.uk:2314'
	
    # Use session attribute to access Requests methods.
    >>> url = conn.url + '/content/130/4/1623.full'
    >>> request = conn.session.get(url)
    >>> request.status_code
    200
	
    # Do stuff with your request object.
    >>> from bs4 import BeautifulSoup
    >>> soup = BeautifulSoup(request.text, 'html.parser')
    >>> soup.title
    <title>Behavioral Hazard in Health Insurance </title>


``JSTOR``, ``EBSCOhost`` and ``Wiley`` are ``Raven`` subclasses specifically for logging onto `www.jstor.org <http://www.jstor.org>`_,
`www.ebscohost.com <http://www.ebscohost.com>`_ and `onlinelibrary.wiley.com <http://onlinelibrary.wiley.com/>`_, respectively.
They include the ``html``, ``pdf`` and ``ref`` methods to download the webpage HTML, PDF and bibliographic
information of a particular document.

.. code-block:: python
    
    >>> from requests_raven import JSTOR
	
    # Establish Raven connection object to the document 10.1068/682574 on jstor.org.
    >>> conn = JSTOR(login=deets)
	
    # Download the HTML on the document webpage.
    >>> doc_id = '10.1086/682574'
    >>> html = conn.html(id=doc_id)
	
    # Download the document PDF.
    >>> pdf = conn.pdf(id=doc_id, file='article.pdf')
    
    # Download the bibliographic information.
    >>> biblio = conn.ref(id=doc_id)
    >>> biblio['authors']
    [{'name': 'Per Krusell'}, {'name': 'Anthony A. Smith'}]

