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

_DEBUG = True

import sys
import os
import csv
from collections import defaultdict
from pybloom import BloomFilter
from isdomain import is_domain

def main():
    usage()
    create_index('test_data/names.csv', 0.00001, 1, [1, 2], ';', True)

def usage():
    text = (
        "\nUsage: %s --infile=<file.csv> --fields=1,2,3\n\n"
        "  -f, --fields=field1,field2       "
        "fields/columns to index, default all\n"
        "  -e, --false-positive-rate=RATE   "
        "error rate of bloom filter, default 0.00001\n"
        "  -d, --delimiter=SYMBOL           "
        "CSV delimiter character, default ;\n"
        "  -r, --index-domains-recursively  "
        "expand domains to subdomain components.\n"
        "  -h, --help                       "
        "display this message.\n\n" % (
            sys.argv[0],))
    sys.stderr.write(text)

def debug(text):
    if _DEBUG:
        sys.stderr.write(text)

def create_index(in_filename, error_rate, skip_lines, limit_columns,
        delimiter, recursive_domains):

    with open(in_filename, 'rb') as csvfile:
        column_values_map = parse_csv_file(
                csvfile, delimiter, recursive_domains, limit_columns, skip_lines)

    for (column_number, values) in column_values_map.items():
        bloom = create_bloom_filter(values, error_rate=error_rate)

        write_bloom_filter(bloom, out_filename(in_filename, column_number))

def parse_csv_file(csvfile, delimiter, recursive_domains, limit_columns,
        skip_lines):
    """
    Opens the file-like-object with the CSV reader module and advances past
    the specified number of header lines. Uses another function to process
    the values into a list-per-column format.
    """

    csv_reader = csv.reader(csvfile, delimiter=delimiter, quotechar='|')
    skip_header_lines(csv_reader, skip_lines)

    return get_values_by_column(csv_reader, limit_columns, recursive_domains)

def get_values_by_column(csv_reader, limit_columns, expand_domains=False):
    """
    From a CSV reader object, returns a dictionary where the column number
    (1-indexed) maps to a list of values for that column. If a value is a valid
    domain name, is it resursively expanded, according to the expand_domains
    flag.

    >>> get_values_by_column([['Red', 'Apple'], ['Blue', 'Banana']], None)
    {1: ['Red', 'Blue'], 2: ['Apple', 'Banana']}
    
    >>> get_values_by_column([['Red', 'Apple'], ['Blue', 'Banana']], [1])
    {1: ['Red', 'Blue']}
    """
        
    data = defaultdict(list)
    for row in csv_reader:
        for (column_number, value) in enumerate(row, start=1):
            if limit_columns and column_number not in limit_columns:
                continue

            if expand_domains and is_domain(value):
                data[column_number].extend(recurse_domain(value))
            else:
                data[column_number].append(value)

    return dict(data)

def skip_header_lines(csv_reader, num_lines):
    """Advance the CSV reader object by num_lines to skip over headers."""
    for i in xrange(num_lines):
        debug("Skipping %s\n" % csv_reader.next())

def recurse_domain(domain):
    """
    Return all sub-parts of the domain down to the top-level domain.

    >>> recurse_domain('www.server1.google.com')
    ['www.server1.google.com', 'server1.google.com', 'google.com', 'com']

    >>> recurse_domain('domain.com')
    ['domain.com', 'com']
    """
    sub_parts = []
    parts = domain.split('.')
    for num_parts in xrange(len(parts)):
        sub_parts.append('.'.join(parts[num_parts:]))
    return sub_parts

def out_filename(in_filename, column_number):
    """
    Return the output filename for this input filename and column.
    >>> out_filename('test.csv', 1)
    'test.csv.1.bfindex'
    """
    return "%s.%d.bfindex" % (in_filename, column_number)

def create_bloom_filter(values, error_rate):
    """
    Create a BloomFilter object with the given error rate and a capacity
    given by the number of unique items in values. Add each value in values
    to the BloomFilter and return.
    """
    value_set = set(values)

    debug("Creating bloom filter, capacity=%d, error_rate=%f (%.4f%%)\n" % (
        len(value_set), error_rate, 100 * error_rate))
    b = BloomFilter(capacity=len(value_set), error_rate=error_rate)
    [b.add(value) for value in value_set]
    for value in value_set:
        debug("Adding '%s'\n" % value)
        b.add(value)

    return b

def write_bloom_filter(bloom_filter, out_filename):
    """Write a BloomFilter instance to the given filename."""
    with open(out_filename, 'wb') as out_file:
        bloom_filter.tofile(out_file)


if __name__ == '__main__':
    main()
