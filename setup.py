#!/usr/bin/env python

from setuptools import setup
import sys

if sys.version_info[0] == 3 and sys.version_info[1] < 4:
    sys.exit('Sorry, Python < 3.4 is not supported')

setup(
    name='macke',
    version='0.1-alpha',
    packages=['macke'],
    url="https://github.com/tum-i22/macke",
    author="Saahil Ognawala",
    author_email="ognawala@in.tum.de",
    license="Apache Software License",
    entry_points={
        'console_scripts': [
            'macke = macke.__main__:main',
            'macke-analyze = macke.analyse.everything:main',
        ]
    },
    classifiers=[
        'License :: OSI Approved :: Apache Software License',
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ]
)
