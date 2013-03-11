#!/usr/bin/python

# Copyright (c) 2013, Paul Michael Furley <paul@paulfurley.com>
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# - Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
# - Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# - Neither the name of the <ORGANIZATION> nor the names of its contributors
#   may be used to endorse or promote products derived from this software
#   without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

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
