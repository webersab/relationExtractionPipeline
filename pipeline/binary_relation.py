#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Standard
import io
import sys
import codecs
import csv
import ConfigParser
import logging
import networkx
import json
from itertools import chain
from itertools import product
from collections import OrderedDict

# Custom
import helper_functions as hf


class BinaryRelation():

    def __init__(self, config):
        self.config = config
        self.home = self.config.get('General', 'home')

        
    # Extract binary relations by combining output of the dependency parser and entity linker
    def extract_binary_relations(self, files):
        dicttypes = {}
        print('process: Extract binary relations')
        common_entities = self.config.get('NEL','common_entities')
        entfilepath = self.config.get('Agdistis', 'out_dir')
        dpindir = self.config.get('UnstableParser','post_proc_out_dir')
        for f in files:
            df = dpindir + '/' + f
            # Read dependency parse
            dtree = hf.dependency_parse_to_graph(df)
            # Read entities
            filenamestem = df.split('/')[-1]#.split('.')[0]
            ef = entfilepath+'/'+filenamestem#+'.json'
            entities = hf.read_json(ef)
            #entities = self.calculate_token_spans_entities(dtree, ne)
            # Extract binary relations
            res = self.extract(dtree, entities, f)
            relations = res[0]
            jsonlist = res[1]
            dicttypes = self.update_dict_types(dicttypes, res[2])
            # Write to human readable file
            self.write_to_human_readable_file(relations)
            # Write to json format file
            self.output_to_json(jsonlist)
        # Write type list to file
        self.output_type_list(dicttypes)


    # Write list of types to file:
    def output_type_list(self, d):
        outdir = self.config.get('Output', 'out_dir')
        filename = self.config.get('Output','types_list')
        listtypes = d.keys()
        with open(outdir + '/' + filename, 'w') as f:
            for t in listtypes:
                f.write(t + '\n')


    # Maintain a dictionary of types
    def update_dict_types(self, d, types):
        for t in types:
            if not t in d:
                d[t] = 1
        return d
        

    # Output sentence relations to json
    def output_to_json(self, l):
        outdir = self.config.get('Output', 'out_dir')
        outfile = self.config.get('Output', 'json_file')
        json_str = '\n'.join([json.dumps(d, ensure_ascii=False).encode('utf8') for d in l])
        with open(outdir + '/' + outfile, 'a') as f:
            f.write(json_str + '\n')


    # Format relations for JSON file
    def format_json_relations(self, rels):
        listr = []
        listt = []
        for r in rels:
            ent1type = 'E' if r[0]['entityType'] == 'ner' else 'G'
            ent2type = 'E' if r[1]['entityType'] == 'ner' else 'G'
            if 'notInWiki' in r[0]['disambiguatedURL']:
                ent1string = r[0]['namedEntity'].replace(' ', '_')
            else:
                ent1string = r[0]['disambiguatedURL'].split('/')[-1]
            if 'notInWiki' in r[1]['disambiguatedURL']:
                ent2string = r[1]['namedEntity'].replace(' ', '_')
            else:
                ent2string = r[1]['disambiguatedURL'].split('/')[-1]
            ent1figer = '#thing' if r[0]['FIGERType'] == 'none' else '#'+r[0]['FIGERType'].split('/')[1]
            ent2figer = '#thing' if r[1]['FIGERType'] == 'none' else '#'+r[1]['FIGERType'].split('/')[1]
            neg = 'NEG__' if r[3] else ''
            predicate = r[2].split('.')[0] + '.1,' + r[2] + '.2'
            s = u'({}({})::{}::{}::{}::{}::{}{}::{}::{})'.format(neg, predicate, ent1string, ent2string,
                                                          ent1figer, ent2figer, ent1type, ent2type, '0', str(r[5]))
            listr.append({'r': s})
            listt.append(ent1figer)
            listt.append(ent2figer)
        return (listr, listt)
            
            
    # Perform the extraction
    def extract(self, dt, ent, f):
        rels = {}
        listsentrels = []
        listtypes = []
        sentlist = ent['sentences'].keys()
        sentlist.sort()
        for sent in sentlist:
            dictsentrels = OrderedDict()
            dpsenttree = dt[int(sent)]
            sentstring = self.get_sentence(dpsenttree)
#            print sentstring
            entities = ent['sentences'][sent]['entities']
            # Get relations
            r = self.get_relations(dpsenttree, entities)
            # JSON format information
            res = self.format_json_relations(r)
            dictsentrels['s'] = sentstring
            dictsentrels['date'] = 'Jan 1, 1980 12:00:00 AM'
            dictsentrels['articleId'] = f
            dictsentrels['lineId'] = str(sent)
            dictsentrels['rels'] = res[0]
            listtypes += res[1]
            listsentrels.append(dictsentrels)
            rels[sent] = {'sentence': sentstring, 'relations': r}
#        print(rels)
        return (rels, listsentrels, listtypes)


    # Extract the sentence text from the dependency tree
    def get_sentence(self, dt):
        t = []
        for node_index in dt.nodes:
            word = dt.nodes[node_index]['word']
            if word:
                t.append(word)
        s = ' '.join(t)
        return s


    def get_negation(self, dt, i, neg):
        if 'advmod' in dt.nodes[i]['deps']:
            # Check for negations at sub-level
            l = dt.nodes[i]['deps']['advmod']
            for n in l:
                if dt.nodes[n]['tag'] == 'PTKNEG':
                    neg = True
            for n in l:
                neg = self.get_negation(dt, n, neg)
        return neg

    
    # Identify the binary relations
    def get_relations(self, dt, ent):
        rels = []
        ent_list = ent.keys()
#        for e in ent_list:
#            print ent[e]['namedEntity'], ent[e]['entityType']
        # For every pair of entities:
        for pair in product(ent_list, repeat=2):
            ent1 = ent[pair[0]]
            ent2 = ent[pair[1]]
            if ent1['entityType'] == 'com' and ent2['entityType'] == 'com':
                valid_combination = False
            else:
                valid_combination = True
#            ent1start = ent1['starttok']
#            ent2start = ent2['starttok']
#            if pair[0] != pair[1] and ent1start < ent2start and valid_combination:
            if pair[0] != pair[1] and valid_combination:
                pred = self.get_predicate(dt, ent1, ent2)
                pred_string = pred[0]
                pred_index = pred[1]
                negation = self.get_negation(dt, pred_index, False)
                passive = False
                string = self.format_relation_string(ent1,ent2,pred_string,negation,passive)
                rels.append((ent1,ent2,pred_string,negation,string,pred_index))
        return rels


    def get_predicate(self, dt, ent1, ent2):
        pred_string = ''
        pred_index = -1
        temp = [u'Künast', u'Job']
        if ent1['namedEntity'] in temp and ent2['namedEntity'] in temp:
            print dt
            print ent1
            print ent2
        ent1rel = dt.nodes[ent1['starttok']]['rel']
        ent2rel = dt.nodes[ent2['starttok']]['rel']
        if ent1rel == 'nsubj' and ent2rel in ['obj', 'obl']:
            ent1head = dt.nodes[ent1['starttok']]['head']
            ent2head = dt.nodes[ent2['starttok']]['head']
            print ent1head, ent2head
            if ent1head == ent2head:
                pred_string = dt.nodes[ent1head]['lemma']
                pred_index = ent1head
                # Check if predicate is a particle verb
                if 'compound:prt' in dt.nodes[ent1head]['deps']:
                    for prt in dt.nodes[ent1head]['deps']['compound:prt']:
                        pred_string += '_' + dt.nodes[prt]['lemma']
            print 'pred: ' + pred_string
            print '------'
        return (pred_string, pred_index)


    def format_relation_string(self, ent1, ent2, pred, neg, passive):
        if 'notInWiki' in ent1['disambiguatedURL']:
            ent1string = ent1['namedEntity'].replace(' ', '_')
        else:
            ent1string = ent1['disambiguatedURL'].split('/')[-1]
        if 'notInWiki' in ent2['disambiguatedURL']:
            ent2string = ent2['namedEntity'].replace(' ', '_')
        else:
            ent2string = ent2['disambiguatedURL'].split('/')[-1]
        ent1figer = '#thing' if ent1['FIGERType'] == 'none' else '#'+ent1['FIGERType'].split('/')[1]
        ent2figer = '#thing' if ent2['FIGERType'] == 'none' else '#'+ent2['FIGERType'].split('/')[1]
        negation = 'NEG__' if neg else ''
        predicate = pred + '.1,' + pred + '.2'
        s = u'{}({}){}{}::{}::{}|||(passive: {})'.format(negation, predicate, ent1figer, ent2figer,
                                                         ent1string, ent2string, str(passive))
        return s


    # Write the binary relations to file
    def write_to_human_readable_file(self, r):
        outdir = self.config.get('Output','out_dir')
        outfile = self.config.get('Output','human_readable_file')
        filename = self.home + '/' + outdir + '/' + outfile
        sent_list = sorted(r.keys())
        with codecs.open(filename, 'a', 'utf8') as f:
            for sent_no in sent_list:
                s = 'line: ' + r[sent_no]['sentence'] + '\n'
                for rel in r[sent_no]['relations']:
                    s += rel[4] + '\n'
                s += '\n'
                f.write(s)
