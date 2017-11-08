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


# Extract all tokens / multi-token spans from a dependency parse
def extract_entities_from_dependency_parse(dtrees, postag):
    d = {'sentences': {}}
    for x in range(0,len(dtrees)):
        d['sentences'][x+1] = {'entities':{}}
        counter = 0
        tok_list = []
        index_list = []
        for node_index in dtrees[x].nodes:
            node = dtrees[x].nodes[node_index]
            if node['ctag'] == postag:
                tok_list.append(node['word'])
                index_list.append(node_index)
            else:
                if tok_list != []:
                    # Add entity to dictionary
                    span = ' '.join(tok_list)
                    starttok = index_list[0]
                    endtok = index_list[-1]
                    entity = {'entity': span, 'starttok': starttok, 'endtok': endtok}
                    d['sentences'][x+1]['entities'][counter] = entity
                    counter += 1
                    tok_list = []
                    index_list = []
    return d


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
