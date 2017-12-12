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
from itertools import chain
from itertools import product

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
#        dpfiles = glob.glob(self.home+'/'+dpindir+'/*')
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
            relations = self.extract(dtree, entities)
            # Write to file
            self.write_to_file(relations)


    # Perform the extraction
    def extract(self, dt, ent):
        rels = {}
        for sent in ent['sentences']:
            dpsenttree = dt[int(sent)]
            sentstring = self.get_sentence(dpsenttree)
            print sentstring
            entities = ent['sentences'][sent]['entities']
            # Get relations
            r = self.get_relations(dpsenttree, entities)
            rels[sent] = {'sentence': sentstring, 'relations': r}
        print(rels)
        return rels


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
#        print ent
#        print "---"
        print dt
#        print "---"
#        print g.nodes()
#        print g.edges()
        ent_list = ent.keys()
#        print(ent_list)
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
#                print "ent pair",  pair
#                print ent1start, ent2start
                try:
                    #print(networkx.has_path(g,source=ent1start,target=ent2start))
                    shortest_path = networkx.shortest_path(g,source=ent1start,target=ent2start)
                    sorted_path = sorted(shortest_path)
                    #print shortest_path
#                    print sorted_path
                    if len(shortest_path) >= 3:
#                        print shortest_path
                        ent1end = ent[pair[0]]['endtok']
                        temp = self.get_predicate(dt, ent1start, ent1end, shortest_path)
                        pred = temp[0]
                        verb_only = temp[1]
                        negation = temp[2]
                        ent1 = ent[pair[0]]['namedEntity']
                        ent2 = ent[pair[1]]['namedEntity']
                        if verb_only:
                            string = self.format_relation_string(ent[pair[0]], ent[pair[1]], pred, verb_only, negation)
                            print string
                            rels.append((ent1,ent2,pred,string,verb_only))
                except networkx.NetworkXNoPath:
                    print "no path found"
#                print "-"
        print "----------------"
        return rels


    def get_predicate(self, dt, ent1start, ent1end, shortest_path):
        #x = (ent1end-ent1start) + 1
        path_list = shortest_path[1:-1]
        print "path list", path_list
        pred_tok_list = []
        pred_pos_list = []
        # Traverse the nodes in the path and build a list of predicates
        for p in path_list:
            pred_pos_list.append(dt.nodes[p]['ctag'])
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
            print shortest_path
            print shortest_path[-1]
            print n
            case = dt.nodes[n]['lemma']
            pred_tok_list.append(case)
        # Check for negations amongst the advmod relations attached to the predicate 
        negation = False
        for pred_tok in path_list:
            if dt.nodes[pred_tok]['ctag'] == 'VERB' and 'advmod' in dt.nodes[pred_tok]['deps']:
                for advmod_tok in dt.nodes[pred_tok]['deps']['advmod']:
                    if dt.nodes[advmod_tok]['tag'] == 'PTKNEG':
                        negation = True
        # Construct the predicate string
        pred = '.'.join(pred_tok_list)
        # Does the path contain verbs only?
        if list(set(pred_pos_list)) == ['VERB']:
            verb_only = True
        else:
            verb_only = False
        print verb_only
        return (pred, verb_only, negation)
        

    def format_relation_string(self, ent1, ent2, pred, verb_only, neg):
        s = ''
        if neg:
            s += '__NEG'
        s += '(' + pred + '.1,' + pred + '.2)'
        s += '#none' if ent1['FIGERType'] == 'none' else '#'+ent1['FIGERType'].split('/')[1]
        s += '#none' if ent2['FIGERType'] == 'none' else '#'+ent2['FIGERType'].split('/')[1]
        s += '::' + ent1['namedEntity']
        s += '::' + ent2['namedEntity']
        s += '|||' + str(verb_only)
        return s
    
    
    # Write the binary relations to file
    def write_to_file(self, r):
        outdir = self.config.get('Output','out_dir')
        filename = self.home + '/' + outdir + '/binary_relations.txt'
        sent_list = sorted(r.keys())
        with codecs.open(filename, 'a', 'utf8') as f:
            for sent_no in sent_list:
                s = 'line: ' + r[sent_no]['sentence'] + '\n'
                for rel in r[sent_no]['relations']:
                    s += rel[3] + '\n'
                s += '\n'
                f.write(s)
