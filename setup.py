from setuptools import setup, find_packages

setup(
    packages = ['yieldfrom', 'yieldfrom.http'], #find_packages(), #['http', 'yieldfrom.http'],
    package_dir = {'yieldfrom': 'yieldfrom'},
    version = '0.1.1',
    namespace_packages = ['yieldfrom'],
    name = 'yieldfrom.http.client',
    description = 'asyncio version of http.client',
    install_requires = ['setuptools',],

    author = 'David Keeney',
    author_email = 'dkeeney@rdbhost.com',
    license = 'Python Software Foundation License',

    keywords = 'asyncio, http, http.client',
    url = 'http://github.com/rdbhost/',
    zip_safe=False,
    )