import unittest
from bloom_indexer import (parse_arguments, create_index, InvalidArgument,
                           MissingArgument)


class ParseArgumentsTest(unittest.TestCase):

    def test_infile_short(self):
        config = parse_arguments(['', '-i', '/path/to/some/file'])
        self.assertEqual('/path/to/some/file', config['in_filename'])

    def test_infile_long(self):
        config = parse_arguments(['', '--infile=/path/to/some/file'])
        self.assertEqual('/path/to/some/file', config['in_filename'])

    def test_infile_default(self):
        pass

    def test_false_positive_rate_short(self):
        config = parse_arguments(['', '-e', '0.1234'])
        self.assertEqual(0.1234, config['false_positive_rate'])

    def test_false_positive_rate_long(self):
        config = parse_arguments(['', '--false-positive-rate=0.5678'])
        self.assertEqual(0.5678, config['false_positive_rate'])

    def test_skip_lines_short(self):
        pass

    def test_skip_lines_long(self):
        pass

    def test_skip_lines_default(self):
        pass

    def test_delimiter_short(self):
        pass

    def test_delimiter_long(self):
        pass

    def test_delimiter_default(self):
        pass

    def test_fields_short(self):
        pass

    def test_fields_long(self):
        pass

    def test_fields_default(self):
        pass

    def test_index_domains_recursively_short(self):
        pass

    def test_index_domains_recursively_long(self):
        pass

    def test_index_domains_recursively_default(self):
        pass


class ValidateArgumentsTest(unittest.TestCase):
    def test_false_positive_rate_negative(self):
        config = parse_arguments(['', '--false-positive-rate=-0.5678'])
        self.assertRaises(InvalidArgument)


if __name__ == '__main__':
    unittest.main()
