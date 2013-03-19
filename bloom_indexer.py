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

DEFAULT_INFILE = None  # None makes this argument mandatory
DEFAULT_FIELDS = []    # Empty list means 'all'
DEFAULT_SKIP_LINES = 1
DEFAULT_FALSE_POSITIVE_RATE = 0.00001
DEFAULT_DELIMITER = ';'
DEFAULT_INDEX_DOMAINS_RECURSIVELY = False

_VERBOSE = False       # switched by the --verbose argument

_EXITCODE_OK = 0
_EXITCODE_IMPORT_ERROR = 1
_EXITCODE_INVALID_ARG = 2
_EXITCODE_MISSING_ARG = 3

import os
import sys
import csv
import getopt
from collections import defaultdict
from isdomain import is_domain

try:
    from pybloom import BloomFilter
except ImportError, e:
    sys.stderr.write("\nError: Failed to import pybloom: %s\n"
                     "Have you installed 'python-bloomfilter'?\n\n" % e)
    sys.exit(_EXITCODE_IMPORT_ERROR)


class Conf:
    """Provides the keys to the config dictionary."""
    Infile = 'infile'
    FalsePositiveRate = 'false-positive-rate'
    SkipLines = 'skip-lines'
    Fields = 'fields'
    Delimiter = 'delimiter'
    IndexDomainsRecursively = 'index-domains-recursively'


class InvalidArgument(Exception):
    pass


class MissingArgument(Exception):
    pass


def main():
    try:
        config = parse_arguments(sys.argv)

    except InvalidArgument, e:
        sys.stderr.write("\nInvalid argument: %s\n" % e)
        usage()
        sys.exit(_EXITCODE_INVALID_ARG)

    except MissingArgument, e:
        sys.stderr.write("\nMissing required argument(s): %s\n" % e)
        usage()
        sys.exit(_EXITCODE_MISSING_ARG)

    if not config:
        sys.exit(_EXITCODE_OK)

    with open(config[Conf.Infile], 'r') as csvfile:
        result = create_index(
            config[Conf.Infile],
            csvfile,
            config[Conf.FalsePositiveRate],
            config[Conf.SkipLines],
            config[Conf.Fields],
            config[Conf.Delimiter],
            config[Conf.IndexDomainsRecursively])

    for (outfile, num_entries) in result.items():
        debug("%s : %s entries\n" % (outfile, num_entries))


def parse_arguments(argv):
    """
    Parse out whatever arguments are available on the command line and call the
    approriate validate function on them. Throw InvalidArgument or
    MissingArgument.
    """
    try:
        (opts, args) = getopt.getopt(
            argv[1:],
            "i:f:s:e:d:rhv",
            ['infile=', 'fields=', 'skip-lines=', 'false-positive-rate=',
             'delimiter=', 'index-domains-recursively', 'help', 'verbose'])
    except getopt.GetoptError as err:
        raise InvalidArgument(err)

    if args:
        raise InvalidArgument(' '.join(args))

    config = {
        Conf.Infile: DEFAULT_INFILE,
        Conf.Fields: DEFAULT_FIELDS,
        Conf.SkipLines: DEFAULT_SKIP_LINES,
        Conf.FalsePositiveRate: DEFAULT_FALSE_POSITIVE_RATE,
        Conf.Delimiter: DEFAULT_DELIMITER,
        Conf.IndexDomainsRecursively: DEFAULT_INDEX_DOMAINS_RECURSIVELY,
    }

    for (opt, arg) in opts:
        if opt in ('-i', '--infile'):
            config[Conf.Infile] = validate_infile(arg)

        elif opt in ('-f', '--fields'):
            config[Conf.Fields] = validate_fields(arg)

        elif opt in ('-s', '--skip-lines'):
            config[Conf.SkipLines] = validate_skip_lines(arg)

        elif opt in ('-e', '--false-positive-rate'):
            config[Conf.FalsePositiveRate] = validate_false_positive_rate(arg)

        elif opt in ('-d', '--delimiter'):
            config[Conf.Delimiter] = validate_delimiter(arg)

        elif opt in ('-r', '--index-domains-recursively'):
            config[Conf.IndexDomainsRecursively] = True

        elif opt in ('-v', '--verbose'):
            global _VERBOSE
            _VERBOSE = True

        elif opt in ('-h', '--help'):
            usage()
            return None

    if None in config.values():
        raise MissingArgument(', '.join([key for key, value in config.items()
                                         if value is None]))
    return config


def validate_infile(arg):
    """
    Validate that the filename is a valid file.

    >>> validate_infile('/non/existent/file')
    Traceback (most recent call last):
    ...
    InvalidArgument: infile is not a file: '/non/existent/file'
    """
    if not os.path.isfile(arg):
        raise InvalidArgument("infile is not a file: '%s'" % arg)
    return arg


def validate_false_positive_rate(arg):
    """
    Convert to float and validate it's positive.
    >>> validate_false_positive_rate('0.25')
    0.25
    >>> validate_false_positive_rate('-0.5')
    Traceback (most recent call last):
    ...
    InvalidArgument: false-positive rate cannot be < 0: '-0.5'
    """
    try:
        rate = float(arg)
    except ValueError:
        raise InvalidArgument("false-positive-rate not a float: '%s'" % arg)

    if rate < 0:
        raise InvalidArgument("false-positive rate cannot be < 0: '%s'" % arg)

    return rate


def validate_delimiter(arg):
    """
    Validate that the delimiter is a single character.
    >>> validate_delimiter(';')
    ';'

    >>> validate_delimiter(';;')
    Traceback (most recent call last):
    ...
    InvalidArgument: delimiter not a single character: ';;'
    """
    if len(arg) != 1:
        raise InvalidArgument("delimiter not a single character: '%s'" % arg)
    return arg


def validate_fields(arg):
    """
    Convert a comma-separated string of integers into a list, checking that
    each is greater than zero. The special value 'all' should return an
    empty list.

    >>> validate_fields('1,2,3')
    [1, 2, 3]

    >>> validate_fields('all')
    []

    >>> validate_fields('foo')
    Traceback (most recent call last):
    ...
    InvalidArgument: fields not a list of integers: 'foo'

    >>> validate_fields('0,1,2')
    Traceback (most recent call last):
    ...
    InvalidArgument: fields must all be > zero: '0,1,2'
    """
    if arg.lower() == 'all':
        return []

    try:
        fields = [int(field) for field in arg.split(',')]
    except ValueError:
        raise InvalidArgument("fields not a list of integers: '%s'" % arg)

    if len(filter(lambda x: x <= 0, fields)):
        raise InvalidArgument("fields must all be > zero: '%s'" % arg)

    return fields


def validate_skip_lines(arg):
    """
    Convert to integer and validate that the value is >= 0
    >>> validate_skip_lines('2')
    2

    >>> validate_skip_lines(-1)
    Traceback (most recent call last):
    ...
    InvalidArgument: skip-lines must be positive: '-1'

    >>> validate_skip_lines('one')
    Traceback (most recent call last):
    ...
    InvalidArgument: skip-lines not an integer: 'one'
    """
    try:
        lines = int(arg)
    except ValueError:
        raise InvalidArgument("skip-lines not an integer: '%s'" % arg)

    if lines < 0:
        raise InvalidArgument("skip-lines must be positive: '%s'" % arg)

    return lines


def usage():
    text = (
        "\nUsage: %s -v -i <file.csv>\n\n"
        "  -i, --infile=FILENAME            "
        "open the CSV given by FILENAME\n"
        "  -f, --fields=field1,field2       "
        "fields/columns to index, eg 1,2,5 [default all]\n"
        "  -s, --skip-lines=NUMBER          "
        "skip NUMBER rows of header data from the top of the CSV file\n"
        "  -e, --false-positive-rate=RATE   "
        "error rate of bloom filter, [default %f]\n"
        "  -d, --delimiter=SYMBOL           "
        "CSV delimiter character [default %s]\n"
        "  -r, --index-domains-recursively  "
        "expand domains to subdomain components [default %s].\n"
        "  -v, --verbose                    "
        "produce output to stderr\n"
        "  -h, --help                       "
        "display this message.\n\n" % (
            sys.argv[0], DEFAULT_FALSE_POSITIVE_RATE, DEFAULT_DELIMITER,
            DEFAULT_INDEX_DOMAINS_RECURSIVELY))
    sys.stderr.write(text)


def debug(text):
    """Print text to stderr if _VERBOSE has been set."""
    if _VERBOSE:
        sys.stderr.write(text)


def create_index(infile, csvfile, error_rate, skip_lines, limit_columns,
                 delimiter, recursive_domains):
    """
    Parse the file-like object given by csvfile using the csv module. Add each
    unique entry in each field/column (specified by limit_columns) to a bloom
    filter and save with a filename derived from the input filenamd and field.
    """

    column_values_map = parse_csv_file(
        csvfile, delimiter, recursive_domains, limit_columns, skip_lines)

    index_stats = {}
    for (column_number, values) in column_values_map.items():
        (bloom, num_added) = create_bloom_filter(values, error_rate=error_rate)

        out_fn = out_filename(infile, column_number)
        index_stats[out_fn] = num_added

        write_bloom_filter(bloom, out_fn)

    return index_stats


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


def out_filename(infile, column_number):
    """
    Return the output filename for this input filename and column.
    >>> out_filename('test.csv', 1)
    'test.csv.1.bfindex'
    """
    return "%s.%d.bfindex" % (infile, column_number)


def create_bloom_filter(values, error_rate):
    """
    Create a BloomFilter object with the given error rate and a capacity
    given by the number of unique items in values. Add each value in values
    to the BloomFilter and return.
    """
    value_set = set(filter(lambda x: len(x), values))

    debug("Creating bloom filter, capacity=%d, error_rate=%f (%.4f%%)\n" % (
        len(value_set), error_rate, 100 * error_rate))
    b = BloomFilter(capacity=len(value_set), error_rate=error_rate)
    for value in value_set:
        debug("Adding '%s'\n" % value)
        b.add(value)

    return (b, len(value_set))


def write_bloom_filter(bloom_filter, out_filename):
    """Write a BloomFilter instance to the given filename."""
    with open(out_filename, 'wb') as out_file:
        bloom_filter.tofile(out_file)


if __name__ == '__main__':
    main()
