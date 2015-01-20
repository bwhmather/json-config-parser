from setuptools import setup

setup(
    name='json-config-parser',
    version='0.1.1',
    author='Ben Mather',
    author_email='bwhmather@bwhmather.com',
    description='A straightforward and unambiguous config file parser.',
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
    py_packages=['jsonconfigparser', 'jsonconfigparser.tests'],
    test_suite='jsonconfigparser.tests.suite',
    )
