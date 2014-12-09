import unittest
import tempfile

from jsonconfigparser import JSONConfigParser, NoSectionError, ParseError


class JSONConfigTestCase(unittest.TestCase):
    def test_init(self):
        JSONConfigParser()

    def test_read_string(self):
        cf = JSONConfigParser()

        cf.read_string((
            '[section]\n'
            '# comment comment\n'
            'foo = "bar"\n'
            '\n'
            '[section2]\n'
            'bar = "baz"\n'
        ))

        self.assertEqual(cf.get('section', 'foo'), 'bar')

    def test_read_file(self):
        string = '[section]\n' + \
                 'foo = "bar"'

        fp = tempfile.NamedTemporaryFile('w+')
        fp.write(string)
        fp.seek(0)

        cf = JSONConfigParser()
        cf.read_file(fp)

        self.assertEqual(cf.get('section', 'foo'), 'bar')

    def test_get(self):
        cf = JSONConfigParser()

        cf.add_section('section')
        cf.set('section', 'section', 'set-in-section')
        self.assertEqual(cf.get('section', 'section'), 'set-in-section')

    def test_get_from_defaults(self):
        cf = JSONConfigParser()

        cf.set(cf.default_section, 'option', 'set-in-defaults')
        try:
            cf.get('section', 'option')
        except NoSectionError:
            pass
        else:
            self.fail("Only fall back to defaults if section exists")

        cf.add_section('section')
        self.assertEqual(cf.get('section', 'option'), 'set-in-defaults',
                         msg="get should fall back to defaults if value not \
                              set in section")

        cf.set('section', 'option', 'set-normally')
        self.assertEqual(cf.get('section', 'option'), 'set-normally',
                         msg="get shouldn't fall back if option is set \
                              normally")

    def test_get_from_vars(self):
        cf = JSONConfigParser()
        cf.add_section('section')
        cf.set('section', 'option', 'set-in-section')

        self.assertEqual(cf.get('section', 'option',
                                vars={'option': 'set-in-vars'}),
                         'set-in-vars',
                         msg="vars should take priority over options in \
                              section")

        self.assertEqual(cf.get('section', 'option', vars={}),
                         'set-in-section',
                         msg="get should fall back to section if option not \
                              in vars")

    def test_get_from_fallback(self):
        cf = JSONConfigParser()
        cf.add_section('section')

        # returns from fallback if section exists
        self.assertEqual(cf.get('section', 'unset', 'fallback'), 'fallback')

        try:
            cf.get('nosection', 'unset', 'fallback')
        except NoSectionError:
            pass
        else:
            self.fail()

    def test_has_option(self):
        cf = JSONConfigParser()

        # option in nonexistant section does not exist
        self.assertFalse(cf.has_option('nonexistant', 'unset'))

        cf.add_section('section')
        self.assertFalse(cf.has_option('section', 'unset'),
                         msg="has_option should return False if section \
                              exists but option is unset")

        cf.set('section', 'set', 'set-normally')
        self.assertTrue(cf.has_option('section', 'set'),
                        msg="has option should return True if option is set \
                             normally")

        cf.set(cf.default_section, 'default', 'set-in-defaults')
        self.assertTrue(cf.has_option('section', 'default'),
                        msg="has_option should return True if option set in \
                             defaults")

    def test_remove_option(self):
        cf = JSONConfigParser()

        cf.add_section('section')
        cf.set('section', 'normal', 'set-normally')
        cf.set(cf.default_section, 'default', 'set-in-defaults')

        # can remove normal options
        self.assertTrue(cf.remove_option('section', 'normal'))
        self.assertFalse(cf.has_option('section', 'normal'))

        # can't remove defaults accidentally (maybe there should be shadowing)
        self.assertFalse(cf.remove_option('section', 'default'))
        self.assertEqual(cf.get('section', 'default'), 'set-in-defaults')

    def test_invalid_section(self):
        cf = JSONConfigParser()

        try:
            cf.read_string((
                '[valid]\n'
                'irrelevant = "meh"\n'
                '[]'
            ))
        except ParseError as e:
            self.assertEqual(e.lineno, 3)

            # check that nothing was added
            self.assertEqual(sum(1 for _ in cf.sections()), 0)
        else:
            self.fail()

        try:
            cf.read_string((
                '[nooooooooooooooooooo'
            ))
        except ParseError as e:
            self.assertEqual(e.lineno, 1)

            # check that nothing was added
            self.assertEqual(sum(1 for _ in cf.sections()), 0)
        else:
            self.fail()

    def test_invalid_values(self):
        cf = JSONConfigParser()

        try:
            cf.read_string((
                '[section]\n'
                'unmatched = [1,2,3}'
            ))
        except ParseError as e:
            self.assertEqual(e.lineno, 2)

            # check that nothing was added
            self.assertEqual(sum(1 for _ in cf.sections()), 0)
        else:
            self.fail()

        try:
            cf.read_string((
                '[section]\n'
                'unterminated = "something\n'
            ))
        except ParseError as e:
            self.assertEqual(e.lineno, 2)

            # check that nothing was added
            self.assertEqual(sum(1 for _ in cf.sections()), 0)
        else:
            self.fail()


suite = unittest.TestLoader().loadTestsFromTestCase(JSONConfigTestCase)
