import unittest

from jsonconfigparser import JSONConfigParser


class JSONConfigTestCase(unittest.TestCase):
    def test_init(self):
        JSONConfigParser()

    def test_read_string(self):
        string = '[section]\n' + \
                 'foo = "bar"\n'

        cf = JSONConfigParser()
        cf.read_string(string)

        self.assertEqual(cf.get('section', 'foo'), 'bar')


suite = unittest.TestLoader().loadTestsFromTestCase(JSONConfigTestCase)
