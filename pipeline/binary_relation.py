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
from nltk.parse import DependencyGraph
from itertools import chain

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
            dtree = self.read_dependency_parse(df)
            # Read entities
            filenamestem = df.split('/')[-1].split('.')[0]
            ef = entfilepath+'/'+filenamestem+'.json'
            entities = self.read_entities(ef)
            # Extract binary relations
            relations = self.extract(dtree, entities)


    # Read the dependency parser output
    def read_dependency_parse(self, filename):
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
    def extract(self, dt, ent):
        rels = []
        # Find start and end tokens for entities from character start and offset
        for sent in ent['sentences']:
            sentstring = ent['sentences'][sent]['sentenceStr']
            char_to_tok = self.convert_offsets(sentstring)
            for entity in ent['sentences'][sent]['entities']:
                e = ent['sentences'][sent]['entities'][entity]
                start = e['start']
                offset = e['offset']
                starttok = char_to_tok[start]
                endtok = char_to_tok[start+offset-1]
                ent['sentences'][sent]['entities'][entity]['starttok'] = starttok
                ent['sentences'][sent]['entities'][entity]['endtok'] = endtok
                # Get relations
                dpsenttree = dt[int(sent)]
            updatedentities = ent['sentences'][sent]['entities']
            r = self.get_relations(dpsenttree, updatedentities)
        return rels


    def get_sentence(self, dt):
        t = []
        for node_index in dt.nodes:
            word = dt.nodes[node_index]['word']
            if word:
                t.append(word)
        s = ' '.join(t)
        return s
    

    def get_relations(self, dt, ent):
        sentence = self.get_sentence(dt)
        print dt
        print sentence
        print('...ENTITY SPANS...')
        ent_span_heads = {}
        # Won't handle overlapping entities - not sure if we'd ever see these though
        for entity in ent:
            for x in range(ent[entity]['starttok'],ent[entity]['endtok']+1):
                ent_span_heads[x] = entity
        # Remove non-heads
        l = ent_span_heads.keys()
        for i in l:
            if dt.nodes[i]['head'] in ent_span_heads:
                del ent_span_heads[i]
        print(ent_span_heads)
        print('...TRAVERSAL...')
        res = self.traverse_parse_tree(dt, ent_span_heads, 0, [], {})
        rel_deps = res[0]
        preds = res[1]
        print(rel_deps)
        print(preds)
        for rd in rel_deps:
            entity_number = ent_span_heads[rd[0]]
            entity_string = ent[entity_number]['namedEntity'].replace(' ','_')
            pred = dt.nodes[rd[1]]['word'] # Replace with lemma?
            if rd[1] in preds:
                for element in preds[rd[1]]['compound']:
                    pred += '_'+dt.nodes[element]['word'] # Change order and use lemma so that wuchs_auf -> aufwachsen?
                if preds[rd[1]]['case']:
                    case = dt.nodes[preds[rd[1]]['case']]['word']
                    pred += ':' + case
            print(entity_string, pred, rd[2])
        print('------') 
        

    def traverse_parse_tree(self, dt, e, node_index, rels, preds):
        children = sorted(chain.from_iterable(dt.nodes[node_index]['deps'].values()))
        for child_index in children:
            child_node = dt.nodes[child_index]
            res = self.rels_and_preds(rels, preds, e, child_index, child_node)
            rels = res[0]
            preds = res[1]
            self.traverse_parse_tree(dt, e, child_index, rels, preds)
        return (rels, preds)


    def rels_and_preds(self, rels, preds, e, child_index, child_node):
        # Get arcs pointing from the entity node (outgoing)
        if child_index in e:
            rels.append((child_index, child_node['head'], child_node['rel']))
            # Maintain a dictionary of predicates to be used for recording compounds
            if child_node['head'] not in preds:
                preds[child_node['head']] = {'compound': [], 'case': None}
        # Get arcs pointing from the node to the entity node (incoming)
        elif child_node['head'] in e and child_node['rel'] == 'case': # Case only for now
            head_chain = [item for item in rels if item[0] == child_node['head']]
            if head_chain[0][1] in preds:
                preds[head_chain[0][1]]['case'] = child_index
        # Record (compound) particle verbs (serial verbs do not appear to apply to German)
        elif child_node['head'] in preds and child_node['rel'] == 'compound:prt':
            preds[child_node['head']]['compound'].append(child_index)
        return(rels, preds)

    
if __name__ == "__main__":
    # execute only if run as a script    

    configfile = 'config.ini'
    cfg = ConfigParser.ConfigParser()
    cfg.read(configfile)
    bin_rel = BinaryRelation(cfg)
    
    dtree = bin_rel.read_dependency_parse('test.conllu')
    
    test_entities = {"file": "none", "sentences": {0: {"entities": {0: {"start": 20, "disambiguatedURL": "http://de.dbpedia.org/resource/Deutsche_Demokratische_Republik", "namedEntity": "DDR", "FIGERType": "/location/country", "offset": 3}, 1: {"start": 0, "disambiguatedURL": "http://de.dbpedia.org/resource/Angela_Merkel", "namedEntity": "Merkel", "FIGERType": "/person/politician", "offset": 6}}, "sentenceStr": "<entity>Merkel</entity> wuchs in der <entity>DDR</entity> auf und war dort als Physikerin wissenschaftlich tätig ."}, 1: {"entities": {0: {"start": 0, "disambiguatedURL": "http://de.dbpedia.org/resource/David_Bowie", "namedEntity": "David Bowie", "FIGERType": "/person", "offset": 11}, 1: {"start": 20, "disambiguatedURL": "null", "namedEntity": "britischer", "FIGERType": "none", "offset": 10}}, "sentenceStr": "<entity>David Bowie</entity> war ein <entity>britischer</entity> Musiker , Sänger , Produzent und Schauspieler ."}}}

    bin_rel.extract(dtree,test_entities)
