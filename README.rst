Json Config Parser
==================

|build-status|

A straightforward and unambiguous config file parser.

This package was originally based on the configparser module that comes in the standard python distribution but has been almost entirely rewritten.

The main branch won't support python 2 as it is missing keyword only arguments and ``ChainMap`` is not in the standard library.
If you need legacy support then there are a couple of forks which look like they do the job.


Installation
------------

Available on pypi as `json-config-parser <pypi_>`_

To install run

.. code:: sh

    pip install json-config-parser


Alternatively grab the code from `github <project_page_>`_ and run:

.. code:: sh

    python setup.py install


Syntax
------

Files are structured using square bracket sections, ``#`` comments and ``$key = $value`` options.  Option values are written in json and can lists and dictionaries be spread over any number of lines.
To keep parsing simple and files neat, comments, section headers and keys can not be indented and no whitespace is allowed on empty lines.

Comments start at the beginning of a line with a ``#`` symbol and extend to the line's end.


Usage
-----

.. code:: python

    cfg = JSONConfigParser()

    cfg.read_string("""
    [section]
    number = 3.141592654
    dictionary = {"key": "value"}
    list = [1,
            2,
            3]
    nested = {"list": [1,2,3]}
    true = true
    none = null
    
    [DEFAULT]
    # settings in the default section are inherited
    # by all other sections.
    default-setting = "default"
    """)

    # read a setting
    cfg.get("section", "number")

    # read a setting using index notation
    cfg["section"]["true"]

    # settings inherited from DEFAULT
    cfg.get("section", "default-setting")


Bugs
----

Please report any problems on the `bugtracker`_ and I will do my best to fix them.
Pull requests are also welcome.


.. |build-status| image:: https://travis-ci.org/bwhmather/json-config-parser.png?branch=develop
    :target: http://travis-ci.org/bwhmather/json-config-parser
    :alt: Build Status
.. _pypi: https://pypi.python.org/pypi/json-config-parser/
.. _project_page: https://github.com/bwhmather/json-config-parser
.. _bugtracker: https://github.com/bwhmather/json-config-parser/issues
