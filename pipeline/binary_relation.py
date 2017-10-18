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
            res = self.read_dependency_parse(df)
            dparse = res[0]
            dtree = res[1]
            # Read entities
            filenamestem = df.split('/')[-1].split('.')[0]
            ef = entfilepath+'/'+filenamestem+'.json'
            entities = self.read_entities(ef)
            # Extract binary relations
            relations = self.extract(dparse, dtree, entities)


    # Read the dependency parser output
    def read_dependency_parse(self, filename):
        with open(filename, 'r') as f:
            data = f.read()
        dparse = parse_conllu(data)
        dtree = parse_conllu_tree(data)
        return (dparse, dtree)
        

    # Read the entity linker output
    def read_entities(self, filename):
        with open(filename, 'r') as f:
            entities = json.load(f)
        return entities


    # Convert character offset to token offset
    def convert_offsets(self,sentence):
        conv = {}
        sent = sentence.replace('<entity>','').replace('</entity>','')
        counter = 1
        for x in range(0,len(sent)):
            conv[x] = counter
            if sent[x] == ' ':
                counter += 1
        return conv
    
    
    # Perform the extraction
    def extract(self, dp, dt, ent):
        rels = []
        # Find start and end tokens for entities from character start and offset
        for sent in ent['sentences']:
            sentstring = ent['sentences'][sent]['sentenceStr']
            char_to_tok = self.convert_offsets(sentstring)
            for entity in ent['sentences'][sent]['entities']:
                e = ent['sentences'][sent]['entities'][entity]
                start = e['start']
                offset = e['offset']
#                nestring = e['namedEntity']
#                print(sentstring)
#                print(sent,entity,start,offset,nestring)
                starttok = char_to_tok[start]
                endtok = char_to_tok[start+offset-1]
                ent['sentences'][sent]['entities'][entity]['starttok'] = starttok
                ent['sentences'][sent]['entities'][entity]['endtok'] = endtok
#                tokenrange = (starttok,endtok)
#                print(tokenrange)
#                print('---------------------')
                # Get relations
                dpsentence = dp[int(sent)]
                dpsenttree = [dt[int(sent)]]
                updatedentity = ent['sentences'][sent]['entities'][entity]
                r = self.get_relations(dpsentence, dpsenttree, updatedentity)
        return rels


    def get_relations(self, dp, dt, ent):
        ls = []
        for tok in dp:
            ls.append(tok['form'])
        ss = ' '.join(ls)
        print ss
        print ent
        for root in dt:
            print root.data
            print root.children
        print('------')



if __name__ == "__main__":
    # execute only if run as a script    

    test_data = """
    1       Merkel  Merkel  NOUN    NN      _       2       nsubj   _       _
    2       wuchs   wachsen VERB    VVFIN   _       0       root    _       _
    3       in      in      ADP     APPR    _       5       case    _       _
    4       der     der     DET     ART     _       5       det     _       _
    5       DDR     DDR     PROPN   NE      _       2       obl     _       _
    6       auf     auf     ADP     PTKVZ   _       2       compound:prt    _       _
    7       und     und     CCONJ   KON     _       13      cc      _       _
    8       war     sein    VERB    VAFIN   _       13      cop     _       _
    9       dort    dort    ADV     ADV     _       13      advmod  _       _
    10      als     als     ADP     KOKOM   _       11      case    _       _
    11      Physikerin      Physikerin      NOUN    NN      _       13      nmod    _       _
    12      wissenschaftlich        wissenschaftlich        ADJ     ADJD    _       13      advmod  _       _
    13      tätig   tätig   ADJ     ADJD    _       2       conj    _       _
    14      .       .       PUNCT   $.      _       2       punct   _       _
    
    """

    test_entities = {"2": {"entities": {"0": {"start": 20, "disambiguatedURL": "http://de.dbpedia.org/resource/Deutsche_Demokratische_Republik", "namedEntity": "DDR", "FIGERType": "/location/country", "offset": 3}, "1": {"start": 0, "disambiguatedURL": "http://de.dbpedia.org/resource/Angela_Merkel", "namedEntity": "Merkel", "FIGERType": "/person/politician", "offset": 6}}, "sentenceStr": "<entity>Merkel</entity> wuchs in der <entity>DDR</entity> auf und war dort als Physikerin wissenschaftlich tätig ."}}

    dparse = parse_conllu(data)
    dtree = parse_conllu_tree(data)
