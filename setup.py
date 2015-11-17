#!/user/bin/env python

from setuptools import setup

setup(
    name='raven-request',
    version='0.0.1',
    description='Requests wrapper to log into Raven.',
    author='Erin Hengel',
    url='http://www.erinhengel.com/software/raven-request/',
    packages = ['raven_request'],
    install_requires=['requests>=2.8.1', 'beautifulsoup4>=4.4.1'],
    package_dir={'raven_requests': 'raven_requests'},
    include_package_data=True,
    author_email='erin.hengel@gmail.com',
    license='Apache 2.0',
    zip_safe=False,
)
