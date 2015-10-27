#!/user/bin/env python

from setuptools import setup

setup(
    name='raven',
    version='0.0.1',
    description='Requests wrapper to log into Raven.',
    author='Erin Hengel',
    url='http://www.erinhengel.com/software/raven/',
    packages = ['raven'],
    install_requires=['requests>=2.8.1'],
    package_dir={'raven': 'raven'},
    include_package_data=True,
    author_email='erin.hengel@gmail.com',
    license='Apache 2.0',
    zip_safe=False,
)
