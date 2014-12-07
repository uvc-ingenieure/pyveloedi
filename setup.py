import os
import re
from setuptools import setup, find_packages


def get_version():
    init = open(os.path.join(os.path.dirname(__file__), 'pyveloedi',
                             '__init__.py')).read()
    return re.search(r"""__version__ = '([0-9.]*)'""", init).group(1)

setup(
    name="pyveloedi",
    url="http://github.com/uvc-ingenieure/pyveloedi",
    author="Max Holtzberg",
    author_email="mh@uvc.de",
    maintainer="Max Holtzberg",
    maintainer_email="mh@uvc.de",
    description="Library for communicating with Veloconnect webservices.",
    long_description="""
pyveloedi
=========

Library for connecting to Veloconnect webservices.

Features:

* Supports URL and XML-Post bindings
* Searching catalog and placing orders
* Winora support with same interface
* MIT License
    """,
    license="MIT License",
    version=get_version(),
    packages=find_packages(exclude=['examples']),
    install_requires=[
        "lxml >= 2.0"
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Communications",
    ])
