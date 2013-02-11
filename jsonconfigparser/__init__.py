from collections.abc import MutableMapping
from collections import OrderedDict

import itertools

import re
import json

__all__ = ["DuplicateSectionError", "DuplicateOptionError",
           "JSONConfigParser"]

DEFAULT_SECT = "DEFAULT"
_UNSET = object()


class ParseError(BaseException):
    def __init__(self, message, **kwargs):

        info = []
        if 'filename' in kwargs:
            info.append('file: %s' % kwargs['filename'])
        if 'section' in kwargs:
            info.append('section: %s' % kwargs['section'])
        if 'lineno' in kwargs:
            info.append('line: %s' % kwargs['lineno'])

        if len(info):
            message.append(', '.join(info) + '\n')

        if 'line' in kwargs:
            message.append(kwargs['line'])

        BaseException.__init__(self, message)


class MissingSectionHeaderError(ParseError):
    """Raised if an option occurs before the first header
    """
    def __init__(self, filename, lineno, line):
        BaseException.__init__(
            self,
            'No section header before first option.\n' +
            'file: %s, line: %d\n%r' %
            (filename, lineno, line))


class InvalidSectionNameError(ParseError):
    def __init__(self, section, **kwargs):
        msg = 'Invalid section name: %s' % repr(section)
        ParseError.__init__(self, msg, **kwargs)


class InvalidOptionNameError(ParseError):
    def __init__(self, option, **kwargs):
        msg = 'Invalid option name: %s' % repr(option)
        ParseError.__init__(self, msg, **kwargs)


class NoSectionError(KeyError):
    pass


class NoOptionError(KeyError):
    pass


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


class JSONConfigParser(MutableMapping):

    _BLANK_TMPL = r"""
        ^
        (\#[^\n\r]*)?                # optional comment
        [\n\r]+                      #eol
        """

    _HEADER_TMPL = r"""
        #^
        \[
        (?P<section>[\-\w]+)
        \]
        [\n\r]+                      #eol
        """

    _KEY_TMPL = r"""
        (?P<key>[\-\w]+)            # at least one letter underscore or hyphen
        \s*                         # optional whitespace
        =                           # followed by '='
        \s*                         # optional whitespace
        """

    _EOL_TMPL = r"""
        \s*                         # optional whitespace
        [\n\r]+                     # eol
        """

    _blank_re = re.compile(_BLANK_TMPL, re.VERBOSE | re.MULTILINE)
    _header_re = re.compile(_HEADER_TMPL, re.VERBOSE | re.MULTILINE)
    _key_re = re.compile(_KEY_TMPL, re.VERBOSE | re.MULTILINE)
    _eol_re = re.compile(_EOL_TMPL, re.VERBOSE | re.MULTILINE)

    _json_decoder = json.JSONDecoder()

    def __init__(self, defaults=None, *,
                 dict_type=OrderedDict, default_section='DEFAULTS'):
        self._dict = dict_type
        self._default_section = default_section
        self._sections = self._dict()
        self._defaults = self._dict()
        self._proxies = self._dict()
        self._proxies[default_section] = SectionProxy(self, default_section)
        if defaults:
            self.read_dict({default_section: defaults})

    def sections(self):
        """Return a list of section names, excluding [DEFAULT]"""
        return self._sections.keys()

    def add_section(self, section):
        """Create a new section in the configuration.

        Raise DuplicateSectionError if a section by the specified name
        already exists. Raise ValueError if name is DEFAULT.
        """
        if (section == self.default_section) or \
           (not self._section_re.match(section)):
            raise ValueError('Invalid section name: %r' % section)

        if section in self._sections:
            raise DuplicateSectionError(section)
        self._sections[section] = self._dict()
        self._proxies[section] = SectionProxy(self, section)

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
        return key == self.default_section or key in self.sections

    def __len__(self):
        return len(self._sections) + 1

    def __iter__(self):
        return itertools.chain((self.default_section,), self._sections.keys())

    def options(self, section):
        """Return a list of option names for the given section name."""
        try:
            opts = iter(set(self._sections[section].keys() +
                            self._defaults.keys()))
        except KeyError:
            raise NoSectionError(section)
        return opts

    def get(self, section, option, fallback=_UNSET, *, vars=None):
        """Get an option value for a given section.

        If `vars' is provided, it must be a dictionary. The option is looked up
        in `vars' (if provided), `section', and in `DEFAULTSECT' in that order.
        If the key is not found and `fallback' is provided, it is used as
        a fallback value. `None' can be provided as a `fallback' value.

        The section DEFAULT is special.
        """
        try:
            d = self._unify_values(section, vars)
        except NoSectionError:
            if fallback is _UNSET:
                raise
            else:
                return fallback
        option = self.optionxform(option)
        try:
            value = d[option]
        except KeyError:
            if fallback is _UNSET:
                raise NoOptionError(option, section)
            else:
                return fallback
        return value

    def has_option(self, section, option):
        if not section or section == self.default_section:
            return option in self._defaults
        elif section in self._sections:
            return (option in self._sections[section] or
                    option in self._defaults)
        else:
            return False

    def set(self, section, option, value=None):
        if not section or section == self.default_section:
            sectdict = self.defaults
        else:
            try:
                sectdict = self._sections[section]
            except KeyError:
                raise NoSectionError(section)
            sectdict[option] = value

    def read(self, filnames, encoding=None):
        pass

    def read_file(self, fp, filename=None):
        pass

    def read_dict(self, dictionary):
        pass

    def read_string(self, string, fpname=None):
        sections_added = set()
        entries_added = set()

        sectname = None
        cursect = None

        idx = 0
        lineno = 0

        while idx < len(string):
            mo = self._header_re.match(string, idx)
            if mo:
                sectname = mo.group('section')

                # check that section has not occured in this file before
                if sectname in sections_added:
                    raise DuplicateSectionError(sectname)
                sections_added.add(sectname)
                entries_added = set()

                # find or create the section
                if sectname == self.default_section:
                    cursect = self._defaults
                elif sectname in self._sections:
                    cursect = self._sections[sectname]
                else:
                    cursect = self._dict()
                    self._sections[sectname] = cursect
                    self._proxies[sectname] = SectionProxy(self, sectname)

                idx = mo.end()
            else:
                # consume blank lines and comments
                mo = self._blank_re.match(string, idx)
                if mo:
                    idx = mo.end()
                else:
                    mo = self._key_re.match(string, idx)
                    if not mo:
                        raise ParseError(
                            "expected section, comment or newline")

                    # read key
                    optname = mo.group('key')
                    idx = mo.end()
                    if optname in entries_added:
                        raise DuplicateOptionError(sectname, optname,
                                                   fpname, lineno)
                    entries_added.add(optname)

                    # read value
                    # TODO increment lineno
                    optval, idx = self._json_decoder.raw_decode(string, idx)
                    cursect[optname] = optval

                    # consume remaining comments and whitespace
                    mo = self._eol_re.match(string, idx)
                    if not mo:
                        raise ParseError(repr(string[idx:]))
                    idx = mo.end()

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
        self._parser._validate_value_types(option=key, value=value)
        return self._parser.set(self._name, key, value)

    def __delitem__(self, key):
        if not (self._parser.has_option(self._name, key) and
                self._parser.remove_option(self._name, key)):
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
