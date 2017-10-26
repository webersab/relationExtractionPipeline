#!/usr/bin/env python
# -*- coding: utf-8 -*-

import collections
import simplejson as json
from nltk.parse import DependencyGraph


# Read dependency parser output from file and construct graph
def dependency_parse_to_graph(filename):
    data = ''
    dtree = []
    with open(filename, 'r') as f:
        for line in f:
            if 'root' in line:
                elements = line.split('\t')
                if elements[7] == 'root':
                    elements[7] = 'ROOT'
                    line = '\t'.join(elements)
            data += line
            if line == '\n':
                dg = DependencyGraph(data.decode('utf8'))
                dtree.append(dg)
                data = ''
    return dtree


# Extract all tokens / multi-token spans of a particular PoS from a dependency parse
def extract_pos_from_dependency_parse(dtrees, postag):
    l = []
    for x in range(0,len(dtrees)):
        for node_index in dtrees[x].nodes:
            node = dtrees[x].nodes[node_index]
            if node['ctag'] == postag:
                l.append((x, node_index, node['ctag'], node['word']))
    return l


# Read a json file to a json object
def read_json(filename):
    with open(filename, 'r') as f:
        data = json.load(f)
    return data


# Convert unicode to string
# Taken from StackOverflow:
# https://stackoverflow.com/questions/1254454/fastest-way-to-convert-a-dicts-keys-values-from-unicode-to-str
def convert_unicode_to_str(data):
    if isinstance(data, basestring):
        return data.encode('utf-8')
    elif isinstance(data, collections.Mapping):
        return dict(map(convert_unicode_to_str, data.iteritems()))
    elif isinstance(data, collections.Iterable):
        return type(data)(map(convert_unicode_to_str, data))
    else:
        return data
