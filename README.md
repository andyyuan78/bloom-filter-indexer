# Bloom Filter Indexer

Opens and parses a CSV file, adding the values from each column to a separate
Bloom Filter search index. This is a fast, probablistic set implementation
which allows quick and compact querying of a given value's existence in the set.

To get started right away, type the following:

    ./bloom_indexer.py --verbose --infile=sample/python-bloom-indexer-sample.csv --fields=1,2 --index-domains-recursively --skip-lines=2

To run tests for the module, type the following:
    
    python test.py
