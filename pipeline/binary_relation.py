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
from itertools import chain

# Custom
import helper_functions as hf


class BinaryRelation():

    def __init__(self, config):
        self.config = config
        self.home = self.config.get('General', 'home')

        
    # Extract binary relations by combining output of the dependency parser and entity linker
    def extract_binary_relations(self):
        print('process: Extract binary relations')
        common_entities = self.config.get('NEL','common_entities')
        entfilepath = self.config.get('Agdistis', 'out_dir')
        dpindir = self.config.get('UnstableParser','post_proc_out_dir')
        dpfiles = glob.glob(self.home+'/'+dpindir+'/*')
        for df in dpfiles:
            # Read dependency parse
            dtree = hf.dependency_parse_to_graph(df)
            # Read entities
            filenamestem = df.split('/')[-1].split('.')[0]
            ef = entfilepath+'/'+filenamestem+'.json'
            ne = hf.read_json(ef)
            print "-------------------------------------"
            if common_entities == 'spotlight':
                # Read common entities
                commonfilepath = self.config.get('Spotlight', 'out_dir')
                cf = commonfilepath+'/'+filenamestem+'.json'
                cn = hf.read_json(cf)
                merged = self.merge_entities(cn, ne)
                entities = self.calculate_token_spans_entities(dtree, merged)
                print common_entities
            else:
                entities = self.calculate_token_spans_entities(dtree, ne)
            print "------"
            print entities
            print "--------------"
            # Extract binary relations
            relations = self.extract(dtree, entities)
            # Write to file
            self.write_to_file(relations)


    # Merge entities already identitified by AGDISTIS with those from Spotlight output
    def merge_entities(self, spot, agdis):
        a = {}
        # Read AGDISTIS entities
        for sents in agdis['sentences']:
            for ent in agdis['sentences'][sents]['entities']:
                e = agdis['sentences'][sents]['entities'][ent]
                print e
                k = str(sents) + '_' + str(e['start']) + '_' + str(e['offset'])
                a[k] = e['namedEntity']
        # Merge in the Spotlight entities
        for sents in spot['sentences']:
            for ent in spot['sentences'][sents]['entities']:
                e = spot['sentences'][sents]['entities'][ent]
                print e
                k = str(sents) + '_'+ str(e['start']) + '_' + str(e['offset'])
                if k not in a: # New entity
                    if sents in agdis['sentences']:
                        ent_num = sorted(agdis['sentences'][sents]['entities'].keys())[-1]
                        agdis['sentences'][sents]['entities'][ent_num] = e
                    else:
                        agdis['sentences'][sents] = {'entities':{0:e}}
        return agdis
    
                        
    # Convert character offset to token offset
    def convert_offsets(self,sentence):
        conv = {}
#        sent = sentence.replace('<entity>','').replace('</entity>','')
        counter = 1
        for x in range(0,len(sentence)):
            conv[x] = counter
            if sentence[x] == ' ':
                counter += 1
        return conv
    

    # Calculate the token spans from character offsets
    def calculate_token_spans_entities(self, dt, ent):
        # Find start and end tokens for entities from character start and offset
        for sent in ent['sentences']:
            dpsenttree = dt[int(sent)]
            sentstring = self.get_sentence(dpsenttree)
            char_to_tok = self.convert_offsets(sentstring)
            for entity in ent['sentences'][sent]['entities']:
                e = ent['sentences'][sent]['entities'][entity]
                start = e['start']
                offset = e['offset']
                starttok = char_to_tok[start]
                endtok = char_to_tok[start+offset-1]
                ent['sentences'][sent]['entities'][entity]['starttok'] = starttok
                ent['sentences'][sent]['entities'][entity]['endtok'] = endtok
                if isinstance(e['namedEntity'], (int,long)):
                    string_value = str(e['namedEntity'])
                    ent['sentences'][sent]['entities'][entity]['namedEntity'] = string_value
        return ent


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
    

    # Find the binary relations
    def get_relations(self, dt, ent):
        print dt
        print('...ENTITY SPANS...')
        # Identify entity spans (just get the heads)
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
        # Traverse the tree and extract information
        res = self.traverse_parse_tree(dt, ent_span_heads, 0, [], {})
        rel_deps = res[0]
        preds = res[1]
        print(rel_deps)
        print(preds)
        # Build relations
        r = []
        for rd in rel_deps:
            entity_number = ent_span_heads[rd[0]]
            entity_string = ent[entity_number]['namedEntity'].replace(' ','_')
            pred = dt.nodes[rd[1]]['word'] # Replace with lemma? if pred == None then it was the root???
            if pred and rd[1] in preds:
                for element in preds[rd[1]]['compound']:
                    pred += '_'+dt.nodes[element]['word'] # Change order and use lemma so that wuchs_auf -> aufwachsen?
                if preds[rd[1]]['case']:
                    case = dt.nodes[preds[rd[1]]['case']]['word']
                    pred += ':' + case
            print(entity_string, pred, rd[2])
            r.append((entity_number, pred))
        print('------')
        formatted = self.format_relations(r, ent)
        return formatted


    # Format the binary relations ready for printing
    def format_relations(self, rels, ents):
        result = []
        d = {}
        for r in rels:
            if r[1] in d and r[0] not in d[r[1]]:
                d[r[1]].append(r[0])
            else:
                d[r[1]] = [r[0]]
        for pred in d:
            if pred != 'none' and len(d[pred]) == 2: # Binary relation
                # Sort the arguments of the predicates
                args = []
                for arg in d[pred]:
                    args.append((arg,ents[arg]['starttok']))
                l = [y[0] for y in sorted(args, key=lambda x: x[1])]
                # Format the predicate string
                p = pred.replace(':','.')
                # Construct the relation string to match the format from the English pipeline
                s = '('+p+'.1,'+p+'.2)'
                s += '#none' if ents[l[0]]['FIGERType'] == 'none' else '#'+ents[l[0]]['FIGERType'].split('/')[1]
                s += '#none' if ents[l[1]]['FIGERType'] == 'none' else '#'+ents[l[1]]['FIGERType'].split('/')[1]
                s += '::'+ents[l[0]]['namedEntity']
                s += '::'+ents[l[1]]['namedEntity']
                result.append(s)
        return result
        

    # Traverse the parse tree
    def traverse_parse_tree(self, dt, e, node_index, rels, preds):
        children = sorted(chain.from_iterable(dt.nodes[node_index]['deps'].values()))
        for child_index in children:
            child_node = dt.nodes[child_index]
            res = self.get_rels_and_preds(rels, preds, e, child_index, child_node)
            rels = res[0]
            preds = res[1]
            self.traverse_parse_tree(dt, e, child_index, rels, preds)
        return (rels, preds)


    # Extract information on relations and predicates, to be used in constructing binary relations
    def get_rels_and_preds(self, rels, preds, e, child_index, child_node):
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


    # Write the binary relations to file
    def write_to_file(self, r):
        outdir = self.config.get('Output','out_dir')
        filename = self.home + '/' + outdir + '/binary_relations.txt'
        sent_list = sorted(r.keys())
        with codecs.open(filename, 'a', 'utf8') as f:
            for sent_no in sent_list:
                s = 'line: ' + r[sent_no]['sentence'] + '\n'
                for rel in r[sent_no]['relations']:
                    s += rel + '\n'
                s += '\n'
                f.write(s)


if __name__ == "__main__":
    # Execute only if run as a script
    
    configfile = 'config.ini'
    cfg = ConfigParser.ConfigParser()
    cfg.read(configfile)
    bin_rel = BinaryRelation(cfg)
    
    dtrees = hf.dependency_parse_to_graph('test.conllu')
    
    test_entities = {"file": "none", "sentences": {0: {"entities": {0: {"start": 20, "disambiguatedURL": "http://de.dbpedia.org/resource/Deutsche_Demokratische_Republik", "namedEntity": "DDR", "FIGERType": "/location/country", "offset": 3}, 1: {"start": 0, "disambiguatedURL": "http://de.dbpedia.org/resource/Angela_Merkel", "namedEntity": "Merkel", "FIGERType": "/person/politician", "offset": 6}}, "sentenceStr": "<entity>Merkel</entity> wuchs in der <entity>DDR</entity> auf und war dort als Physikerin wissenschaftlich tätig ."}, 1: {"entities": {0: {"start": 0, "disambiguatedURL": "http://de.dbpedia.org/resource/David_Bowie", "namedEntity": "David Bowie", "FIGERType": "/person", "offset": 11}, 1: {"start": 20, "disambiguatedURL": "null", "namedEntity": "britischer", "FIGERType": "none", "offset": 10}}, "sentenceStr": "<entity>David Bowie</entity> war ein <entity>britischer</entity> Musiker , Sänger , Produzent und Schauspieler ."}}}

    bin_rel.extract(dtrees, test_entities)
