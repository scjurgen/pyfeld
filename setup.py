# coding=UTF-8
this_version = '0.9.27'

import sys
if sys.version_info < (3,0):
    sys.exit('Sorry, Python < 3.0 is not supported')

import os
from setuptools import setup, find_packages
from codecs import open
from os import path


long_description = 'Raumfeld controlled by python scripts'
here = path.abspath(path.dirname(__file__))
s = path.join(here, 'README.rst')

if os.path.exists(s):
    long_description = open('README.rst', 'r', encoding='utf8').read()
else:
    print("cant open readme.rst")

setup(
    name='pyfeld',
    version=this_version,
    author='Jürgen Schwietering',
    author_email='scjurgen@yahoo.com',
    description='Raumfeld controlled by python scripts',
    long_description=long_description,
    license='MIT',
    keywords=['raumfeld', 'wlan-speakers', 'loudspeakers', 'upnp', 'audio', 'media', 'casting', 'streaming'],
    url='http://github.com/scjurgen/pyfeld',
    packages=['pyfeld', ],
    include_package_data=True,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Utilities',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],
    #py_modules=['pyfeld','DirBrowse'],
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=['requests', 'texttable', 'urllib3', 'python-daemon'],
    # 'python-Levenshtein',  'futures'
    #packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    entry_points={
        'console_scripts': [
            'pyfeld=pyfeld.rfcmd:run_main',
            'pyfeldui=pyfeld.tkui:run_main',
            'pyfeldmacro=pyfeld.rfmacro:run_main',
        ],
    }
)

