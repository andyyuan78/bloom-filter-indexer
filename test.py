#!/usr/bin/python
import unittest
import os
import glob

from cStringIO import StringIO
from pybloom import BloomFilter

from bloom_indexer import (parse_arguments, create_index, MissingArgument)

TEST_FILE_CONTENT = (
    "FieldA,FieldB,FieldC\n"
    "apple,carrot,example.domain.com\n"
    "banana,potato,www.google.co.uk\n"
    "orange,leek,subdomain.yahoo.com\n"
    "pear,cauliflower,\n"
    "pineapple,bean,\n"
    ",broccoli,\n")


class TopLevelTest(unittest.TestCase):
    def setUp(self):
        self.test_file = StringIO(TEST_FILE_CONTENT)

    def tearDown(self):
        for tmpfile in glob.glob('/tmp/fake.csv.*.bfindex'):
            os.unlink(tmpfile)

    def test_insert_then_test(self):
        result = create_index(
            '/tmp/fake.csv',  # input filename
            self.test_file,   # file-like object
            0.0001,           # error rate
            1,                # skip lines
            [1, 2],           # fields
            ',',              # delimiter
            False)            # recursive domain
        self.assertEqual(
            {'/tmp/fake.csv.2.bfindex': 6,
             '/tmp/fake.csv.1.bfindex': 5},
            result)
        b1 = BloomFilter.fromfile(open('/tmp/fake.csv.1.bfindex', 'rb'))
        b2 = BloomFilter.fromfile(open('/tmp/fake.csv.2.bfindex', 'rb'))

        self.assertEqual(False, 'FieldA' in b1)
        self.assertEqual(False, 'FieldB' in b2)

        for word in ('apple', 'banana', 'orange', 'pear', 'pineapple'):
            self.assertEqual(True, word in b1)
            self.assertEqual(False, word in b2)

        for word in ('carrot', 'potato', 'leek', 'cauliflower', 'bean'):
            self.assertEqual(True, word in b2)
            self.assertEqual(False, word in b1)

    def test_recursive_domains(self):
        result = create_index(
            '/tmp/fake.csv',  # input filename
            self.test_file,   # file-like object
            0.0001,           # error rate
            1,                # skip lines
            [3],              # fields
            ',',              # delimiter
            True)             # recursive domain
        self.assertEqual(
            {'/tmp/fake.csv.3.bfindex': 9},
            result)

        b = BloomFilter.fromfile(open('/tmp/fake.csv.3.bfindex', 'rb'))

        for word in ('subdomain.yahoo.com', 'yahoo.com', 'com',
                     'example.domain.com', 'domain.com', 'www.google.co.uk',
                     'google.co.uk', 'co.uk', 'uk'):
            self.assertEqual(True, word in b)


class ParseArgumentsTest(unittest.TestCase):
    def test_long_version(self):
        config = parse_arguments([
            'fake.py',
            '--infile=/etc/profile',
            '--fields=2,6',
            '--skip-lines=3',
            '--false-positive-rate=0.00123',
            '--delimiter=,',
            '--index-domains-recursively'])
        self.assertEqual(
            {'delimiter': ',',
             'false-positive-rate': 0.00123,
             'fields': [2, 6],
             'index-domains-recursively': True,
             'infile': '/etc/profile',
             'skip-lines': 3},
            config)

    def test_short_version(self):
        config = parse_arguments([
            'fake.py',
            '-i/etc/profile',
            '-f2,6',
            '-s3',
            '-e0.00123',
            '-d,',
            '-r'])
        self.assertEqual(
            {'delimiter': ',',
             'false-positive-rate': 0.00123,
             'fields': [2, 6],
             'index-domains-recursively': True,
             'infile': '/etc/profile',
             'skip-lines': 3},
            config)

    def test_missing_infile(self):
        self.assertRaises(
            MissingArgument,
            lambda: parse_arguments([
                'fake.py',
                '--fields=2,6',
                '--skip-lines=3',
                '--false-positive-rate=0.00123',
                '--delimiter=,',
                '--index-domains-recursively']))

    def test_missing_fields(self):
        self.assertRaises(
            MissingArgument,
            lambda: parse_arguments([
                'fake.py',
                '--infile=/etc/profile',
                '--skip-lines=3',
                '--false-positive-rate=0.00123',
                '--delimiter=,',
                '--index-domains-recursively']))

    def test_defaults(self):
        config = parse_arguments([
            'fake.py',
            '--infile=/etc/profile',
            '--fields=2,6'])
        self.assertEqual(
            {'delimiter': ';',
             'false-positive-rate': 1e-05,
             'fields': [2, 6],
             'index-domains-recursively': False,
             'infile': '/etc/profile',
             'skip-lines': 1},
            config)

if __name__ == '__main__':
    import doctest
    import bloom_indexer
    if doctest.testmod(bloom_indexer).failed > 0:
        import sys
        sys.exit(1)
    unittest.main()
