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
                starttok = char_to_tok[start]
                endtok = char_to_tok[start+offset-1]
                ent['sentences'][sent]['entities'][entity]['starttok'] = starttok
                ent['sentences'][sent]['entities'][entity]['endtok'] = endtok
                # Get relations
                dpsentence = dp[int(sent)]
                dpsenttree = [dt[int(sent)]]
            updatedentities = ent['sentences'][sent]['entities']
            r = self.get_relations(dpsentence, dpsenttree, updatedentities)
        return rels


    def traverse_parse_tree(self, dt, e, deps, preds):
        for node in dt:
            d = node.data
            # Get arcs pointing from the entity token (outgoing)
            if d['id'] in e:
                deps.append((d['id'], d['head'], d['deprel']))
                # Maintain a dictionary of predicates to be used for recording compounds
                if d['head'] not in preds:
                    preds[d['head']] = {'compound': [], 'case': None}
            # Get arcs pointing from the token to the entity (incoming)
            elif d['head'] in e and d['deprel'] == 'case': # Case only for now
                head_chain = [item for item in deps if item[0] == d['head']]
                if head_chain[0][1] in preds:
                    preds[head_chain[0][1]]['case'] = d['id']
            # Record (compound) particle verbs (serial verbs do not appear to apply to German)    
            elif d['head'] in preds and d['deprel'] == 'compound:prt':
                preds[d['head']]['compound'].append(d['id'])
            self.traverse_parse_tree(node.children, e, deps, preds)
        return (deps, preds)


    def get_relations(self, dp, dt, ent):
        ls = []
        for tok in dp:
            ls.append(tok['form'])
        ss = ' '.join(ls)
        print ss
        print ent
        print dt
        print('...ENTITY SPANS...')
        ent_spans = {}
        # Won't handle overlapping entities - not sure if we'd ever see these though
        for entity in ent:
            for x in range(ent[entity]['starttok'],ent[entity]['endtok']+1):
                ent_spans[x] = entity
        print(ent_spans)
        print('...TRAVERSAL...')
        res = self.traverse_parse_tree(dt, ent_spans, [], {})
        rel_deps = res[0]
        preds = res[1]
        print(rel_deps)
        print(preds)
        for rd in rel_deps:
            pred = dp[rd[1]-1]['form'] # Replace with lemma?
            if rd[1] in preds:
                for element in preds[rd[1]]['compound']:
                    pred += '_'+dp[element-1]['form'] # Change order and use lemma so that wuchs_auf -> aufwachsen?
                if preds[rd[1]]['case']:
                    case = dp[preds[rd[1]]['case']-1]['form']
                else:
                    case = ''
                pred += ':' + case
            print(dp[rd[0]-1]['form'], pred, rd[2])
        print('------')



if __name__ == "__main__":
    # execute only if run as a script    

    configfile = 'config.ini'
    cfg = ConfigParser.ConfigParser()
    cfg.read(configfile)
    bin_rel = BinaryRelation(cfg)
    
    p = bin_rel.read_dependency_parse('test.conllu')
    dparse = p[0]
    dtree = p[1]
    
    test_entities = {"file": "/afs/inf.ed.ac.uk/user/l/lguillou/Code/question-answering/pipeline/03a-ner-output/de-input-1.tsv", "sentences": {"0": {"entities": {"0": {"start": 20, "disambiguatedURL": "http://de.dbpedia.org/resource/Deutsche_Demokratische_Republik", "namedEntity": "DDR", "FIGERType": "/location/country", "offset": 3}, "1": {"start": 0, "disambiguatedURL": "http://de.dbpedia.org/resource/Angela_Merkel", "namedEntity": "Merkel", "FIGERType": "/person/politician", "offset": 6}}, "sentenceStr": "<entity>Merkel</entity> wuchs in der <entity>DDR</entity> auf und war dort als Physikerin wissenschaftlich tätig ."}}}

    bin_rel.extract(dparse,dtree,test_entities)
