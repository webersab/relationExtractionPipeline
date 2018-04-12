#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Standard
import io
import sys
import codecs
import csv
import ConfigParser
import logging
import json
from itertools import chain
from itertools import product
from collections import OrderedDict

# Custom
import helper_functions as hf


class BinaryRelation():

    """
    Perform binary relation extraction
    Input: dependency parse, common and named entities, entity linking information
    Output: binary relations in text and JSON format, list of types (text file)
    """
    
    def __init__(self, config):
        self.config = config
        self.home = self.config.get('General', 'home')

        
    def extract_binary_relations(self, files):
        """
        Extract binary relations by combining output of the dependency parser and entity linker
        """
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


    def output_type_list(self, d):
        """
        Write list of types to file
        types file is passed to Javad Hosseini's pipeline for entailment graph generation 
        """
        outdir = self.config.get('Output', 'out_dir')
        filename = self.config.get('Output','types_list')
        listtypes = d.keys()
        with open(outdir + '/' + filename, 'w') as f:
            for t in listtypes:
                f.write(t + '\n')


    def update_dict_types(self, d, types):
        """
        Maintain a dictionary of types 
        """
        for t in types:
            if not t in d:
                d[t] = 1
        return d
        

    def output_to_json(self, l):
        """
        Output sentence relations to JSON
        For the JSON format binary relations output file
        """
        outdir = self.config.get('Output', 'out_dir')
        outfile = self.config.get('Output', 'json_file')
        json_str = '\n'.join([json.dumps(d, ensure_ascii=False).encode('utf8') for d in l])
        with open(outdir + '/' + outfile, 'a') as f:
            f.write(json_str + '\n')


    def format_json_relations(self, rels):
        """
        Format relations for JSON file
        JSON file is passed to Javad Hosseini's pipeline for entailment graph generation
        """
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
            
            
    def extract(self, dt, ent, f):
        """
        Perform the extraction 
        """
        rels = {}
        listsentrels = []
        listtypes = []
        sentlist = ent['sentences'].keys()
        sentlist.sort()
        for sent in sentlist:
            dictsentrels = OrderedDict()
            dpsenttree = dt[int(sent)]
            sentstring = self.get_sentence(dpsenttree)
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
        return (rels, listsentrels, listtypes)


    def get_sentence(self, dt):
        """
        Extract the sentence text from the dependency tree
        """
        t = []
        for node_index in dt.nodes:
            word = dt.nodes[node_index]['word']
            if word:
                t.append(word)
        s = ' '.join(t)
        return s


    def get_negation(self, dt, i, neg):
        """
        Check to see if the predicate is negated
        Look for the POS-tag "PTKNEG" and dependency "advmod"
        """
        if 'advmod' in dt.nodes[i]['deps']:
            # Check for negations at sub-level
            l = dt.nodes[i]['deps']['advmod']
            for n in l:
                if dt.nodes[n]['tag'] == 'PTKNEG':
                    neg = True
            for n in l:
                neg = self.get_negation(dt, n, neg)
        return neg


    def get_modifiers_to_verb(self, dt, i, mods):
        """
        Get modifiers of the verb (i.e. the predicate)
        Look for the "advmod" dependency
        """
        if 'advmod' in dt.nodes[i]['deps']:
            l = dt.nodes[i]['deps']['advmod']
            for n in l:
                if dt.nodes[n]['tag'] != 'PTKNEG':
                    mods.append(n)
                    mods = self.get_modifiers_to_verb(dt, n, mods)
        return mods

    
    def get_relations(self, dt, ent):
        """
        Identify the binary relations
        """
        rels = []
        ent_list = ent.keys()
        # For every pair of entities:
        for pair in product(ent_list, repeat=2):
            ent1 = ent[pair[0]]
            ent2 = ent[pair[1]]
            if ent1['entityType'] == 'com' and ent2['entityType'] == 'com':
                valid_combination = False
            else:
                valid_combination = True
            if pair[0] != pair[1] and valid_combination:
                pred = self.get_predicate(dt, ent1, ent2)
                pred_string = pred[0]
                pred_index = pred[1]
                negation = self.get_negation(dt, pred_index, False)
                passive = pred[2]
                if passive: # Swap entities
                    ent1 = ent[pair[1]]
                    ent2 = ent[pair[0]]
                string = self.format_relation_string(ent1,ent2,pred_string,negation,passive)
                if pred_string != '':
                    rels.append((ent1,ent2,pred_string,negation,string,pred_index))
        return rels


    def get_predicate(self, dt, ent1, ent2):
        """
        Get the predicate that links the two entities
        """
        pred_string = ''
        pred_index = -1
        passive = False
        ent1rel = dt.nodes[ent1['starttok']]['rel']
        ent2rel = dt.nodes[ent2['starttok']]['rel']
        if ent1rel in ['nsubj', 'nsubj:pass'] and ent2rel in ['obj', 'obl']:
            if ent1rel == 'nsubj:pass':
                passive = True
            ent1head = dt.nodes[ent1['starttok']]['head']
            ent2head = dt.nodes[ent2['starttok']]['head']
            if ent1head == ent2head:
                pred_string = dt.nodes[ent1head]['lemma']
                pred_index = ent1head
                # Check if predicate is a particle verb
                if 'compound:prt' in dt.nodes[ent1head]['deps']:
                    for prt in dt.nodes[ent1head]['deps']['compound:prt']:
                        pred_string += '_' + dt.nodes[prt]['lemma']
                # Add modifiers to verbs
                mods = self.get_modifiers_to_verb(dt, pred_index, [])
                for mod in mods:
                    pred_string += '.' + dt.nodes[mod]['lemma']
                # Add prepositions
                if 'case' in dt.nodes[ent2['starttok']]['deps']:
                    for prep in dt.nodes[ent2['starttok']]['deps']['case']:
                        pred_string += '.' + dt.nodes[prep]['lemma']
        return (pred_string, pred_index, passive)


    def format_relation_string(self, ent1, ent2, pred, neg, passive):
        """
        Format the relation as a string
        For output in the human-readable binary relations file
        """
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


    def write_to_human_readable_file(self, r):
        """
        Write the binary relations to file
        """
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
