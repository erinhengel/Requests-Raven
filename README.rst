Raven
=====

Raven Request is a custom Requests class to log onto Raven, the University of Cambridge's central
web authentication service.


Installation
------------
	
.. code-block:: bash

	$ pip install raven_request


Documentation
-------------

Detailed documentation available at `erinhengel.com <http://www.erinhengel.com/software/raven-request/>`_. 


Quickstart
----------

The Raven class logs into Raven and establishes a connection with the host. The ``session`` attribute returns a `Request Session object <http://requests.readthedocs.org/en/latest/user/advanced/#session-objects>`_ with all the methods of the main `Requests API <http://requests.readthedocs.org/en/latest/>`_.


.. code-block:: python

    >>> from raven_request import Raven
	
    # Establish Raven connection object for the website www.example.com.
    >>> deets = {'userid': 'ab123', 'pwd': 'XXXX'}
    >>> conn = Raven(url='http://qje.oxfordjournals.org', login=deets)
	
    # The final destination url looks something like this.
    >>> conn.url
    http://libsta28.lib.cam.ac.uk:2924
	
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


JSTOR, EBSCOhost and Wiley are Raven subclasses specifically for logging onto www.jstor.org,
www.ebscohost.com and `onlinelibrary.wiley.com <http://onlinelibrary.wiley.com/>`_ respectively.
They include the ``html``, ``pdf`` and ``ref`` methods to download the webpage, pdf and bibliographic
information, respectively, of a particular document in their databases.

.. code-block:: python
    
    >>> from raven_request import JSTOR
	
    # Establish Raven conncection object to the document 10.1068/682574 on jstor.org.
    >>> doi = '10.1086/682574'
    >>> conn = JSTOR(login=deets)
	
    # Download the html of the document webpage.
    >>> html = conn.html(id=doi)
	
    # Download the document pdf.
    >>> pdf = conn.pdf(id=doi)
    
    # Download the biliographic information.
    >>> biblio = conn.ref(id=doi)
    >>> biblio['authors']
    [{'name': 'Per Krusell'}, {'name': 'Anthony A. Smith'}]

