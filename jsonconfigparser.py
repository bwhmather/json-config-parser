from collections import MutableMapping, OrderedDict, ChainMap

import itertools

import re
import json

__all__ = ['ParseError',
           'InvalidSectionNameError', 'InvalidOptionNameError',
           'NoSectionError', 'NoOptionError',
           'DuplicateSectionError', 'DuplicateOptionError',
           'JSONConfigParser']

DEFAULT_SECT = 'DEFAULT'
_UNSET = object()

_JSON_ERROR_TMPL = r"""
    ^
    (?P<message> .*):                           # message
    \ line\ (?P<lineno> [0-9]+)                 # line number
    \ column\ (?P<column> [0-9]+)               # column
    (\ -\ line\ [0-9]+\ column\ [0-9]+\ -)?     # optional end of error
    \ \(char\ ([0-9]+)\)                        # index in string
    $
    """
_json_error_re = re.compile(_JSON_ERROR_TMPL, re.VERBOSE | re.MULTILINE)


class ParseError(ValueError):
    def __init__(self, message, *,
                 filename=None, section=None,
                 lineno=None, column=None,
                 line=None):
        super(ParseError, self).__init__(self)

        self.message = message
        self.filename = filename
        self.section = section
        self.lineno = lineno
        self.column = column
        self.line = line

    def __str__(self):
        location = []
        if self.filename:
            location.append('File: %s' % repr(self.filename))
        if self.lineno is not None:
            location.append('Line: %i' % self.lineno)
        if self.section:
            location.append('in %s' % self.section)

        output = ', '.join(location)
        if output:
            output += '\n'

        if self.line:
            output += '  ' + self.line.strip() + '\n'

        output += '%s: %s' % (self.__class__.__name__, self.message)

        return output


class MissingSectionHeaderError(ParseError):
    """Raised if an option occurs before the first header
    """
    def __init__(self, **kwargs):
        msg = 'No section header before first option.'
        ParseError.__init__(self, msg, **kwargs)


class InvalidSectionNameError(ParseError):
    def __init__(self, section, **kwargs):
        msg = 'Invalid section name: %s' % repr(section)
        ParseError.__init__(self, msg, **kwargs)


class InvalidOptionNameError(ParseError):
    def __init__(self, option, **kwargs):
        msg = 'Invalid option name: %s' % repr(option)
        ParseError.__init__(self, msg, **kwargs)


class DuplicateSectionError(ParseError):
    """Raised when a section is repeated in an input source.

    Possible repetitions that raise this exception are: multiple creation
    using the API or when a section is found more than once in a single input
    file, string or dictionary.
    """
    def __init__(self, section, **kwargs):
        msg = 'Section %s already declared' % repr(section)
        ParseError.__init__(self, msg, **kwargs)


class DuplicateOptionError(ParseError):
    """Raised by parser when an option is repeated in an input source.

    Current implementation raises this exception only when an option is found
    more than once in a single file, string or dictionary.
    """

    def __init__(self, option, **kwargs):
        msg = 'Duplicate definition of option: %s' % repr(option)
        ParseError.__init__(self, msg, **kwargs)


class NoSectionError(KeyError):
    pass


class NoOptionError(KeyError):
    pass


def parse_json_error(json_error):
    mo = _json_error_re.match(json_error)
    if not mo:
        raise Exception("TODO")
    return (
        mo.group('message'),
        int(mo.group('lineno')),
        int(mo.group('column'))
    )


def get_line(string, idx):
    """ Given a string and the index of a character in the string, returns the
    number and contents of the line containing the referenced character and the
    index of the character on that line.

    Spectacularly inefficient but only called in exception handling
    """
    for lineno, line in enumerate(string.splitlines(True)):
        if idx < len(line):
            return lineno + 1, idx, line
        idx -= len(line)
    raise IndexError()


class JSONConfigParser(MutableMapping):

    _BLANK_TMPL = r"""
        ^
        (\#[^\n\r]*)?                # optional comment
        [\n\r]*([\n\r]|\Z)           # end-of-line or end-of-file
        """

    _HEADER_TMPL = r"""
        ^
        \[
        (?P<section>[\-\w]+)
        \]
        [\n\r]*([\n\r]|\Z)          # end-of-line or end-of-file
        """

    _KEY_TMPL = r"""
        ^
        (?P<key>[\-\w]+)            # at least one letter underscore or hyphen
        \s*                         # optional whitespace
        =                           # followed by '='
        \s*                         # optional whitespace
        """

    _EOL_TMPL = r"""
        [\n\r]*([\n\r]|\Z)          # end-of-line or end-of-file
        """

    _blank_re = re.compile(_BLANK_TMPL, re.VERBOSE | re.MULTILINE)
    _header_re = re.compile(_HEADER_TMPL, re.VERBOSE | re.MULTILINE)
    _key_re = re.compile(_KEY_TMPL, re.VERBOSE | re.MULTILINE)
    _eol_re = re.compile(_EOL_TMPL, re.VERBOSE | re.MULTILINE)

    _json_decoder = json.JSONDecoder()

    def __init__(self, defaults=None, *,
                 dict_type=OrderedDict, default_section=DEFAULT_SECT):
        self._dict = dict_type
        self._default_section = default_section
        self._defaults = self._dict()
        self._sections = self._dict()
        self._proxies = self._dict()
        self._proxies[default_section] = SectionProxy(self, default_section)
        if defaults:
            self.read_dict({default_section: defaults})

    def sections(self):
        """Return a list of section names, excluding [DEFAULT]"""
        return self._sections.keys()

    def add_section(self, section):
        """Create a new section in the configuration.

        Raises ValueError if name is the same as the default section.
        If section name is valid, returns True if it already exists and False
        otherwise.
        """
        if section == self.default_section:
            raise ValueError('Invalid section name: %r' % section)

        if section in self._sections:
            return True

        self._sections[section] = ChainMap({}, self._defaults)
        self._proxies[section] = SectionProxy(self, section)

        return False

    def has_section(self, section):
        return section in self._sections

    def remove_section(self, section):
        """Delete a section.

        Returns True if the section existed previously, False otherwise.
        """
        existed = section in self._sections
        if existed:
            del self._sections[section]
            del self._proxies[section]
        return existed

    def __getitem__(self, key):
        if key != self.default_section and not self.has_section(key):
            raise KeyError(key)
        return self._proxies[key]

    def __setitem__(self, key, value):
        # To conform with the mapping protocol, overwrites existing values in
        # the section.
        if key == self.default_section:
            self._defaults.clear()
        elif key in self._sections:
            self._sections[key].clear()
        self.read_dict({key: value})

    def __delitem__(self, key):
        if key == self.default_section:
            raise ValueError("Cannot remove the default section.")
        if not self.remove_section(key):
            raise KeyError(key)

    def __contains__(self, key):
        return key == self.default_section or key in self._sections

    def __len__(self):
        return len(self._sections) + 1

    def __iter__(self):
        return itertools.chain((self.default_section,), self._sections.keys())

    def options(self, section):
        """Return a list of option names for the given section name."""
        if not self.has_section(section):
            raise NoSectionError(section)

        return self._sections.keys()

    def get(self, section, option, fallback=_UNSET, *, vars=None):
        """Get an option value for a given section.

        If `vars' is provided, it must be a dictionary. The option is looked up
        in `vars' (if provided), `section', and in `DEFAULTSECT' in that order.
        If the key is not found and `fallback' is provided, it is used as
        a fallback value. `None' can be provided as a `fallback' value.

        The section DEFAULT is special.
        """
        if section is self.default_section:
            section_dict = self._defaults
        elif section in self._sections:
            section_dict = self._sections[section]
        else:
            raise NoSectionError(section)

        if vars is not None:
            section_dict = ChainMap(vars, section_dict)

        if option in section_dict:
            return section_dict[option]

        if fallback is _UNSET:
            raise NoOptionError(option)

        return fallback

    def has_option(self, section, option):
        if not section or section == self.default_section:
            return option in self._defaults
        elif section in self._sections:
            return option in self._sections[section]
        else:
            return False

    def set(self, section, option, value=None):
        if not section or section == self.default_section:
            sectdict = self._defaults
        else:
            try:
                sectdict = self._sections[section]
            except KeyError:
                raise NoSectionError(section)
        sectdict[option] = value

    def remove_option(self, section, option):
        if not section or section == self._default_section:
            section_dict = self._defaults
        elif section in self._sections:
            section_dict = self._sections[section]
        else:
            raise NoSectionError(section)

        try:
            section_dict.pop(option)
        except KeyError:
            return False
        return True

    def read(self, filenames, encoding=None, *, skip=False):
        if isinstance(filenames, str):
            filenames = [filenames]
        for f in filenames:
            try:
                with open(f, 'r', encoding=encoding) as fp:
                    self.read_file(fp)
            except OSError:
                # if file could not be found, skip it
                if skip:
                    continue
                else:
                    raise

    def read_file(self, fp, fpname=None):
        self.read_string(fp.read(), fpname=fpname)

    def read_dict(self, dictionary):
        # validate dictionary
        for section, options in dictionary.items():
            if not re.match(r'^\w[\-\w]*$', section):
                raise InvalidSectionNameError(section)

            for option in options:
                if not re.match(r'^\w[\-\w]*$', option):
                    raise InvalidOptionNameError(option, section=section)

        # update config
        for section, options in dictionary.items():
            if section not in self:
                self.add_section(section)

            self[section].update(options)

    def read_string(self, string, fpname=None):
        config = {}
        section = None

        idx = 0

        while idx < len(string):
            if string[idx] == '[':
                mo = self._header_re.match(string, idx)
                if not mo:
                    lineno, column, line = get_line(string, idx)
                    raise ParseError(
                        'could not parse section header',
                        filename=fpname,
                        lineno=lineno, column=column,
                        line=line
                    )
                section = mo.group('section')

                # check that section has not occured in this file before
                if section in config:
                    raise DuplicateSectionError(section)

                # find or create the section
                if section not in config:
                    config[section] = {}

                idx = mo.end()
            elif string[idx] in ['#', '\n', '\r']:
                # consume blank lines and comments
                mo = self._blank_re.match(string, idx)
                idx = mo.end()
            else:
                # hopefully a key value pair
                # read option
                mo = self._key_re.match(string, idx)
                if not mo:
                    lineno, column, line = get_line(string, idx)
                    raise ParseError(
                        "expected section, option, comment or empty line",
                        filename=fpname, section=section,
                        lineno=lineno, column=column,
                        line=line
                    )

                if section is None:
                    raise MissingSectionHeaderError()

                option = mo.group('key')
                if option in config[section]:
                    raise DuplicateOptionError(section, option,
                                               fpname, lineno)

                idx = mo.end()

                # read value
                try:
                    value, idx = self._json_decoder.raw_decode(string, idx)
                except ValueError as e:
                    message, lineno, column = parse_json_error(e.args[0])
                    line = string.splitlines()[lineno-1]
                    raise ParseError(
                        message,
                        filename=fpname, section=section,
                        lineno=lineno, column=column,
                        line=line
                    )

                config[section][option] = value

                # consume remaining comments and whitespace
                mo = self._eol_re.match(string, idx)
                if not mo:
                    lineno, column, line = get_line(string, idx)
                    raise ParseError(
                        "unexpected symbol or whitespace",
                        filename=fpname, section=section,
                        lineno=lineno, column=column,
                        line=line
                    )
                idx = mo.end()
        self.read_dict(config)

    @property
    def default_section(self):
        # default section should be read-only
        return self._default_section


class SectionProxy(MutableMapping):
    """A proxy for a single section from a parser."""

    def __init__(self, parser, name):
        """Creates a view on a section of the specified `name` in `parser`."""
        self._parser = parser
        self._name = name

    def __repr__(self):
        return '<Section: {}>'.format(self._name)

    def __getitem__(self, key):
        if not self._parser.has_option(self._name, key):
            raise KeyError(key)
        return self._parser.get(self._name, key)

    def __setitem__(self, key, value):
        return self._parser.set(self._name, key, value)

    def __delitem__(self, key):
        if not self._parser.remove_option(self._name, key):
            raise KeyError(key)

    def __contains__(self, key):
        return self._parser.has_option(self._name, key)

    def __len__(self):
        return len(self._options())

    def __iter__(self):
        return self._options().__iter__()

    def _options(self):
        if self._name != self._parser.default_section:
            return self._parser.options(self._name)
        else:
            return self._parser.defaults()

    def get(self, option, *args, **kwargs):
        return self._parser.get(self._name, option, *args, **kwargs)

    @property
    def parser(self):
        # The parser object of the proxy is read-only.
        return self._parser

    @property
    def name(self):
        # The name of the section on a proxy is read-only.
        return self._name
