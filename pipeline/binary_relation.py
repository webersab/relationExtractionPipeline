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
            # Get arcs pointing from the entity token
            if node.data['id'] in e:
                d = node.data
                deps.append((d['id'], d['head'], d['deprel']))
                # Maintain a dictionary of predicates to be used for recording compounds
                if d['head'] not in preds:
                    preds[d['head']] = {'compound': [], 'case': None}
            # Record (compound) particle verbs (serial verbs do not appear to apply to German)    
            elif node.data['head'] in preds and node.data['deprel'] == 'compound:prt':
                preds[d['head']]['compound'].append(node.data['id'])
            elif node.data['head'] in e and node.data['deprel'] == 'case':
                pass ### CONTINUE ...
            self.traverse_parse_tree(node.children, e, deps, preds)
        return (deps, preds)


    #[TreeNode(data=OrderedDict([('id', 2), ('form', 'wuchs'), ('lemma', 'wachsen'), ('upostag', 'VERB'), ('xpostag', 'VVFIN'), ('feats', None), ('head', 0), ('deprel', 'root'), ('deps', None), ('misc', None)]), children=[TreeNode(data=OrderedDict([('id', 1), ('form', 'Merkel'), ('lemma', 'Merkel'), ('upostag', 'NOUN'), ('xpostag', 'NN'), ('feats', None), ('head', 2), ('deprel', 'nsubj'), ('deps', None), ('misc', None)]), children=[]), TreeNode(data=OrderedDict([('id', 5), ('form', 'DDR'), ('lemma', 'DDR'), ('upostag', 'PROPN'), ('xpostag', 'NE'), ('feats', None), ('head', 2), ('deprel', 'obl'), ('deps', None), ('misc', None)]), children=[TreeNode(data=OrderedDict([('id', 3), ('form', 'in'), ('lemma', 'in'), ('upostag', 'ADP'), ('xpostag', 'APPR'), ('feats', None), ('head', 5), ('deprel', 'case'), ('deps', None), ('misc', None)]), children=[]), TreeNode(data=OrderedDict([('id', 4), ('form', 'der'), ('lemma', 'der'), ('upostag', 'DET'), ('xpostag', 'ART'), ('feats', None), ('head', 5), ('deprel', 'det'), ('deps', None), ('misc', None)]), children=[])]), TreeNode(data=OrderedDict([('id', 6), ('form', 'auf'), ('lemma', 'auf'), ('upostag', 'ADP'), ('xpostag', 'PTKVZ'), ('feats', None), ('head', 2), ('deprel', 'compound:prt'), ('deps', None), ('misc', None)]), children=[]), TreeNode(data=OrderedDict([('id', 13), ('form', 't\xc3\xa4tig'), ('lemma', 't\xc3\xa4tig'), ('upostag', 'ADJ'), ('xpostag', 'ADJD'), ('feats', None), ('head', 2), ('deprel', 'conj'), ('deps', None), ('misc', None)]), children=[TreeNode(data=OrderedDict([('id', 7), ('form', 'und'), ('lemma', 'und'), ('upostag', 'CCONJ'), ('xpostag', 'KON'), ('feats', None), ('head', 13), ('deprel', 'cc'), ('deps', None), ('misc', None)]), children=[]), TreeNode(data=OrderedDict([('id', 8), ('form', 'war'), ('lemma', 'sein'), ('upostag', 'VERB'), ('xpostag', 'VAFIN'), ('feats', None), ('head', 13), ('deprel', 'cop'), ('deps', None), ('misc', None)]), children=[]), TreeNode(data=OrderedDict([('id', 9), ('form', 'dort'), ('lemma', 'dort'), ('upostag', 'ADV'), ('xpostag', 'ADV'), ('feats', None), ('head', 13), ('deprel', 'advmod'), ('deps', None), ('misc', None)]), children=[]), TreeNode(data=OrderedDict([('id', 11), ('form', 'Physikerin'), ('lemma', 'Physikerin'), ('upostag', 'NOUN'), ('xpostag', 'NN'), ('feats', None), ('head', 13), ('deprel', 'nmod'), ('deps', None), ('misc', None)]), children=[TreeNode(data=OrderedDict([('id', 10), ('form', 'als'), ('lemma', 'als'), ('upostag', 'ADP'), ('xpostag', 'KOKOM'), ('feats', None), ('head', 11), ('deprel', 'case'), ('deps', None), ('misc', None)]), children=[])]), TreeNode(data=OrderedDict([('id', 12), ('form', 'wissenschaftlich'), ('lemma', 'wissenschaftlich'), ('upostag', 'ADJ'), ('xpostag', 'ADJD'), ('feats', None), ('head', 13), ('deprel', 'advmod'), ('deps', None), ('misc', None)]), children=[])]), TreeNode(data=OrderedDict([('id', 14), ('form', '.'), ('lemma', '.'), ('upostag', 'PUNCT'), ('xpostag', '$.'), ('feats', None), ('head', 2), ('deprel', 'punct'), ('deps', None), ('misc', None)]), children=[])])]
    

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
