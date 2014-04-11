"""
JSON Config Parser
==================

A straightforward and unambiguous config file parser.
Parses ini style files with json keys.
"""
from setuptools import setup

setup(
    name='json-config-parser',
    version='0.0.1',
    author='Ben Mather',
    author_email='bwhmather@bwhmather.com',
    description='A straightforward and unambiguous config file parser.',
    long_description=__doc__,
    url='https://github.com/bwhmather/json-config-parser/',
    license='BSD',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Python Software Foundation License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: BSD License',
        ],
    platforms='any',
    py_modules=['jsonconfigparser'],
    test_suite='test_jsonconfigparser.suite',
    )
