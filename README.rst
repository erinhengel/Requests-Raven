Raven
=====

Raven Request is a custom Requests class to log onto Raven, the University of Cambridge's central
web authentication service.


Installation
------------
	
.. code-block:: bash

	$ pip install ravenrequest


Documentation
-------------

Detailed documentation available at `erinhengel.com <http://www.erinhengel.com/software/raven-request/>`_. 


Quickstart
----------

The Raven class logs into Raven and establishes a connection with the host. The ``session`` attribute returns a `Request Session object <http://requests.readthedocs.org/en/latest/user/advanced/#session-objects>`_ with all the methods of the main `Requests API <http://requests.readthedocs.org/en/latest/>`_.


.. code-block:: python

    >>> from ravenrequest import Raven
	
    # Establish Raven connection object for the website www.example.com.
    >>> deets = {'userid': 'ab123', 'pwd': 'XXXX'}
    >>> conn = Raven(url='http://www.example.com', login=deets)
	
    # The final destination url looks something like this
    >>> conn.url
    http://libsta28.cam.ac.uk:2093/
	
    # Generate Session object to access Requests methods.
    >>> s = conn.session
    >>> request = s.get(conn.url+'/secretstuff.html')
    >>> request.text
    ...
	
    # Do stuff with your request object, for example
    >>> from bs4 import beautifulsoup
    >>> soup = BeautifulSoup(request.text, 'html.parser')
    >>> soup.prettify()
    ...


JSTOR and EHOST are Raven subclasses specifically for logging onto www.jstor.org and
www.ebscohost.com, respectively. They include the ``html`` and ``pdf`` attributes to
download the html and pdf, respectively, of a particular document in their databases.

.. code-block:: python
    
    >>> from ravenrequest import JSTOR
	
    # Establish Raven conncection object to the document 10.1068/682574 on jstor.org.
    >>> id = '10.1086/682574'
    >>> conn = JSTOR(login=deets)
	
    # Download the html of the document webpage.
    >>> html = conn.html(doi=id)
    >>> html.text
    ...
	
    # Download the document pdf.
    >>> pdf = conn.pdf(doi=id)
    >>> open('file.pdf', 'wb').write(pdf)

