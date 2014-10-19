from setuptools import setup, find_packages

setup(
    packages = ['yieldfrom', 'yieldfrom.urllib',],
    package_dir = {'yieldfrom': 'yieldfrom'},
    version = '0.1.1',
    namespace_packages = ['yieldfrom'],
    name = 'yieldfrom.urllib.request',
    description = 'asyncio version of urllib.request (urllib2)',
    install_requires = ['setuptools',],

    author = 'David Keeney',
    author_email = 'dkeeney@rdbhost.com',
    license = 'Python Software Foundation License',

    keywords = 'asyncio, http, http, urllib',
    url = 'http://github.com/rdbhost/yieldfromUrllib2',
    zip_safe=False,
    )