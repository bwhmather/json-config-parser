import unittest
import tempfile

from jsonconfigparser import JSONConfigParser


class JSONConfigTestCase(unittest.TestCase):
    def test_init(self):
        JSONConfigParser()

    def test_read_string(self):
        string = '[section]\n' + \
                 '# comment comment\n' + \
                 'foo = "bar"\n' + \
                 '\n' + \
                 '[section2]\n' + \
                 'bar = "baz"\n'


        cf = JSONConfigParser()
        cf.read_string(string)

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

        cf.set(cf.default_section, 'defaults', 'set-in-defaults')
        self.assertEqual(cf.get('section', 'defaults'), 'set-in-defaults')

        self.assertEqual(cf.get('section', 'vars',
                                vars={'vars': 'set-in-vars'}),
                         'set-in-vars')

        self.assertEqual(cf.get('section', 'unset', 'fallback'), 'fallback')


suite = unittest.TestLoader().loadTestsFromTestCase(JSONConfigTestCase)
