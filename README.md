# Bloom Filter Indexer

Opens and parses a CSV file, adding the values from each column to a separate
Bloom Filter search index. This is a fast, probablistic set implementation
which allows quick and compact querying of a given value's existence in the set.
