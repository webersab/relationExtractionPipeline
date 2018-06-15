#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Standard
import collections
import simplejson as json
from nltk.parse import DependencyGraph


def dependency_parse_to_graph(filename):
    """
    Read dependency parser output from file and construct graph
    """
    data = ''
    dtree = []
    with open(filename, 'r') as f:
        for line in f:
            if line[0] != '#':
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


def extract_entities_from_dependency_parse(dtrees, postag):
    """
    Extract all tokens / multi-token spans from a dependency parse
    """
    sents = []
    for x in range(0,len(dtrees)):
        tok_list = []
        for node_index in dtrees[x].nodes:
            if node_index != 0:
                node = dtrees[x].nodes[node_index]
                if node['ctag'] == postag:
                    tok_list.append((node['word'],postag))
                else:
                    tok_list.append((node['word'],'O'))
        sents.append(tok_list)
    return sents


def read_json(filename):
    """
    Read a json file to a json object
    """
    with open(filename, 'r') as f:
        data = json.load(f)
    return data


def convert_unicode_to_str(data):
    """
    Convert unicode to string                                                                                                             Taken from StackOverflow:                                                                                                             https://stackoverflow.com/questions/1254454/fastest-way-to-convert-a-dicts-keys-values-from-unicode-to-str  
    """
    if isinstance(data, basestring):
        return data.encode('utf-8')
    elif isinstance(data, collections.Mapping):
        return dict(map(convert_unicode_to_str, data.iteritems()))
    elif isinstance(data, collections.Iterable):
        return type(data)(map(convert_unicode_to_str, data))
    else:
        return data


def write_string_list_to_file(string_list, filename):
    """
    Write list of strings to file, one item per line
    """
    with open(filename, 'w') as f:
        for element in string_list:
            f.write(element+'\n')


def write_nested_string_list_to_file(string_list, filename):
    """
    Write nested list of strings to file, one item per line
    Format of line: list item, index of nested list
    """
    with open(filename, 'w') as f:
        for i in range(0,len(string_list)):
            for element in string_list[i]:
                f.write(element+'\t'+str(i)+'\n')


def group_batches_for_parallel_processing(batchnamesfile, batchgroupsfile, cores):
    """
    Split batch files into groups, one group per available core
    """
    l = [[] for i in range(cores)]
    counter = 0
    with open(batchnamesfile) as f:
        for line in f:
            counter += 1
            filename = line.rstrip('\n')
            group = counter % cores
            l[group].append(filename)
    write_nested_string_list_to_file(l, batchgroupsfile)
    return l
