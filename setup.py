#! /usr/bin/env python

from setuptools import setup

DISTNAME = 'python-winbuilder'
DESCRIPTION = 'MinGW-based build environment for Python projects'
MAINTAINER = 'Olivier Grisel'
MAINTAINER_EMAIL = 'olivier.grisel@ensta.org'
URL = 'http://github.com/ogrisel/python-winbuilder'
LICENSE = 'MIT'
VERSION = "0.1.1"

setup(
    name=DISTNAME,
    maintainer=MAINTAINER,
    maintainer_email=MAINTAINER_EMAIL,
    description=DESCRIPTION,
    license=LICENSE,
    url=URL,
    version=VERSION,
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved',
        'Programming Language :: Python',
        'Topic :: Software Development',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Operating System :: Unix',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
    py_modules=['pywinbuilder'],
)
