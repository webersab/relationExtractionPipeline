#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Standard
import io
import sys
import codecs
import glob
import csv
import ConfigParser
import logging
import simplejson as json
from conllu.parser import parse as parse_conllu
from conllu.parser import parse_tree as parse_conllu_tree

class BinaryRelation():

    def __init__(self, config):
        self.config = config
        self.home = self.config.get('General', 'home')

        
    # Extract binary relations by combining output of the dependency parser and entity linker
    def extract_binary_relations(self):
        print('process: Extract binary relations')
        entfilepath = self.config.get('Agdistis', 'out_dir')
        dpindir = self.config.get('UnstableParser','post_proc_out_dir')
        dpfiles = glob.glob(self.home+'/'+dpindir+'/*')
        for df in dpfiles:
            # Read dependency parse
            dparse = self.read_dependency_parse(df)
            # Read entities
            filenamestem = df.split('/')[-1].split('.')[0]
            ef = entfilepath+'/'+filenamestem+'.json'
            entities = self.read_entities(ef)
            # Extract binary relations
            relations = self.extract(dparse, entities)


    # Read the dependency parser output
    def read_dependency_parse(self, filename):
        with open(filename, 'r') as f:
            data = f.read()
        dparse = parse_conllu(data)
        return dparse
        

    # Read the entity linker output
    def read_entities(self, filename):
        with open(filename, 'r') as f:
            entities = json.load(f)
        return entities


    # Convert character offset to token offset
    def convert_offsets(self,sentence):
        conv = {}
        sent = sentence.replace('<entity>','').replace('</entity>','')
        print(len(sent))
        counter = 1
        for x in range(0,len(sent)):
            conv[x] = counter
            if sent[x] == ' ':
                counter += 1
        return conv
    
    
    # Perform the extraction
    def extract(self, dp, ent):
        rels = []
        for sent in ent['sentences']:
            sentstring = ent['sentences'][sent]['sentenceStr']
            char_to_tok = self.convert_offsets(sentstring)
            for entity in ent['sentences'][sent]['entities']:
                e = ent['sentences'][sent]['entities'][entity]
                start = e['start']
                offset = e['offset']
                nestring = e['namedEntity']
                print(sentstring)
                print(sent,entity,start,offset,nestring)
                starttok = char_to_tok[start]
                endtok = char_to_tok[start+offset-1]
                tokenrange = (starttok,endtok)
                print(tokenrange)
                print('---------------------')
        return rels
