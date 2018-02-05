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
            res = self.extract(dtree, entities)
            relations = res[0]
            jsonlist = res[1]
            # Write to human readable file
            self.write_to_human_readable_file(relations)
            # Write to json format file
            self.output_to_json(jsonlist)
            

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
        for r in rels:
            print "----"
            print r
            ent1type = 'E' if r[0]['entityType'] == 'ner' else 'G'
            ent2type = 'E' if r[1]['entityType'] == 'ner' else 'G'
            s = '('
            if r[3]: # negation
                s += 'NEG__'
            s += '(' + r[2].split('.')[0] + '.1,' + r[2] + '.2)' # predicate
            s += '::' + r[0]['namedEntity'] + '::' + r[1]['namedEntity'] # ent1, ent2 strings
            s += '::' + ent1type + ent2type # ent1, ent2 types
            s += '::0::0' # dummy information
            s += ')'
            listr.append({'r': s})                                                     
        return listr
            
            
    # Perform the extraction
    def extract(self, dt, ent):
        rels = {}
        listsentrels = []
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
            dictsentrels['s'] = sentstring
            dictsentrels['date'] = 'Feb 5, 2018 12:00:00 AM'
            dictsentrels['articleId'] = '0'
            dictsentrels['lineId'] = str(sent)
            dictsentrels['rels'] = self.format_json_relations(r)
            listsentrels.append(dictsentrels)
            rels[sent] = {'sentence': sentstring, 'relations': r}
#        print(rels)
        return (rels, listsentrels)


    # Extract the sentence text from the dependency tree
    def get_sentence(self, dt):
        t = []
        for node_index in dt.nodes:
            word = dt.nodes[node_index]['word']
            if word:
                t.append(word)
        s = ' '.join(t)
        return s
    

    # Identify the binary relations
    def get_relations(self, dt, ent):
        rels = []
        multidi = dt.nx_graph()
        g = multidi.to_undirected()
        print dt
        ent_list = ent.keys()
        # For every pair of entities:
        for pair in product(ent_list, repeat=2):
            ent1type = ent[pair[0]]['entityType']
            ent2type = ent[pair[1]]['entityType']
            if ent1type == 'com' and ent2type == 'com':
                valid_combination = False
            else:
                valid_combination = True
            ent1start = ent[pair[0]]['starttok']
            ent2start = ent[pair[1]]['starttok']
            if pair[0] != pair[1] and ent1start < ent2start and valid_combination:
                try:
                    shortest_path = networkx.shortest_path(g,source=ent1start,target=ent2start)
                    sorted_path = sorted(shortest_path)
                    if len(shortest_path) >= 3:
                        ent1end = ent[pair[0]]['endtok']
                        temp = self.get_predicate(dt, ent1start, ent1end, shortest_path)
                        pred = temp[0]
                        verb_only = temp[1]
                        negation = temp[2]
                        passive = temp[3]
                        tensed_verb_only = temp[4]
                        ent1 = ent[pair[0]]#['namedEntity']
                        ent2 = ent[pair[1]]#['namedEntity']
                        if verb_only and tensed_verb_only: ### Amend check for only one tensed verb between entities (in path)
                            string = self.format_relation_string(ent[pair[0]], ent[pair[1]], pred, verb_only, negation, passive, tensed_verb_only)
                            print string
                            rels.append((ent1,ent2,pred,negation,string,verb_only,tensed_verb_only))
                except networkx.NetworkXNoPath:
                    print "no path found"
#                print "-"
        print "----------------"
        return rels


    def get_predicate(self, dt, ent1start, ent1end, shortest_path):
        path_list = shortest_path[1:-1]
        pred_tok_list = []
        pred_coarse_pos_list = []
        pred_fine_pos_list = []
        # Traverse the nodes in the path and build a list of predicates
        for p in path_list:
            pred_coarse_pos_list.append(dt.nodes[p]['ctag'])
            pred_fine_pos_list.append(dt.nodes[p]['tag'])
            # Make a note of particle verbs
            if dt.nodes[p]['ctag'] == 'VERB' and 'compound:prt' in dt.nodes[p]['deps']:
                particle_verb_node_list = dt.nodes[p]['deps']['compound:prt']
                particle_verb_list = []
                for pv in particle_verb_node_list:
                    particle_verb_list.append(dt.nodes[pv]['lemma'])
                particle_verb = '_'.join(particle_verb_list)
                main_verb = dt.nodes[p]['lemma']
                pred_tok_list.append(main_verb+'_'+particle_verb)
            else:
                pred_tok_list.append(dt.nodes[p]['lemma'])
        # Get preposition ("case" relation attached to second entity)
        if 'case' in dt.nodes[shortest_path[-1]]['deps']:
            n = dt.nodes[shortest_path[-1]]['deps']['case'][0]
            case = dt.nodes[n]['lemma']
            pred_tok_list.append(case)
        # Check for negations amongst the advmod relations attached to the predicate 
        negation = False
        for pred_tok in path_list:
            if dt.nodes[pred_tok]['ctag'] == 'VERB' and 'advmod' in dt.nodes[pred_tok]['deps']:
                for advmod_tok in dt.nodes[pred_tok]['deps']['advmod']:
                    if dt.nodes[advmod_tok]['tag'] == 'PTKNEG':
                        negation = True
        # Check for passives
        passive = False
        for pred_tok in path_list:
            if 'aux:pass' in dt.nodes[pred_tok]['deps']:
                passive = True
        # Construct the predicate string
        pred = '.'.join(pred_tok_list)
        # Does the path contain verbs only?
        verb_only = True if list(set(pred_coarse_pos_list)) == ['VERB'] else False ### Amend to check for tensed verbs only
        # Does the path contain only one tensed verb?
        tensed_verb_only = False
        counter = 0
        for pos_tag in pred_fine_pos_list:
            if pos_tag in ['VVFIN', 'VVIMP', 'VVPP']:
                counter += 1
        if counter == 0: # Check for auxiliary verbs
            for pos_tag in pred_fine_pos_list:
                if pos_tag in ['VAFIN', 'VAIMP', 'VAPP']:
                    counter += 1
        if counter == 1:
            tensed_verb_only = True
        return (pred, verb_only, negation, passive, tensed_verb_only)
        

    def format_relation_string(self, ent1, ent2, pred, verb_only, neg, passive, tensed_verb_only):
        s = ''
        if neg:
            s += 'NEG__'
        s += '(' + pred.split('.')[0] + '.1,' + pred + '.2)'
        s += '#none' if ent1['FIGERType'] == 'none' else '#'+ent1['FIGERType'].split('/')[1]
        s += '#none' if ent2['FIGERType'] == 'none' else '#'+ent2['FIGERType'].split('/')[1]
        s += '::' + ent1['namedEntity']
        s += '::' + ent2['namedEntity']
#        s += '|||' + '(verb only: '+ str(verb_only)
#        s += '; passive: ' + str(passive)
#        s += '; tensed verb only: ' + str(tensed_verb_only) + ')' 
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
