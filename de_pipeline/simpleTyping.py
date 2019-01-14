#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Standard
import io
import gzip
import sys
import codecs
import csv
import ConfigParser
import logging
import subprocess
import simplejson as json
from itertools import izip
import pprint

# Custom
import helper_functions as hf
from agdistis import Agdistis
from datetime import datetime

class SimpleTyping():
    
    """
    Perform simple typing using NER tags and GermaNet
    Input: common and named entities
    Output: entities with NER tags or types derived from GermaNet
    """
    
    def __init__(self, config):
        self.config = config
        self.home = self.config.get('General', 'home')
    
    
    def process(self, files):
        """
        Main method
        """
        print('Simple entity typing')
        logging.info('started simple entity typing: '+str(datetime.now()))
        # Extract nouns
        self.detect_nouns(files)
        # Extract needed information from NER and entity files
        self.simple_type(files)
        print(str(files))
        logging.info('ended simple entity typing: '+str(datetime.now()))
     
        
    def detect_nouns(self, files):
        """
        Extract noun spans from dependecy parser output
        """
        # Get input and output directories, and input files
        indir = self.config.get('UnstableParser','post_proc_out_dir')
        outdir = self.config.get('Entities','out_dir')
        for f in files:
            print("getting nouns from "+str(f))
            infile = self.home + '/' + indir + '/' + f
            dtrees = hf.dependency_parse_to_graph(infile)
            tagged_sents = hf.extract_entities_from_dependency_parse(dtrees, 'NOUN')
            outfilename = self.home + '/' + outdir + '/' + f
            with open(outfilename, 'w') as f:
                for sent in tagged_sents:
                    for token in sent:
                        f.write(token[0].encode('utf-8')+'\t'+token[1]+'\n')
                    f.write('\n')
     
                    
    def simple_type(self,files):
        """
        Simple entity typing using NER tags and GermaNet
        """
        nerindir = self.config.get('NER','out_dir')
        entindir = self.config.get('Entities','out_dir')
        outdir = self.config.get('SimpleType','out_dir')
        nerfiles = sorted([self.home+'/'+nerindir+'/'+f for f in files])
        entfiles = sorted([self.home+'/'+entindir+'/'+f for f in files])
        for x in range(0,len(nerfiles)):
            nf = nerfiles[x]
            ef = entfiles[x]
            # Read file and format sentences
            temp = self.format_nel_sentences(nf, ef)
            formatted = temp[0]
            ent_map = temp[1]
            #print("-----------------------------Formatted--------------------")
            #print(formatted)
            #print("-----------------------ent map----------------------------")
            #pp = pprint.PrettyPrinter(indent=4)
            #pp.pprint(ent_map)
            #typing information needs to be added to this map before we can print it
            outfilename = self.home + '/' + outdir + '/' + nf.split('/')[-1]
            with io.open(outfilename, 'w', encoding='utf8') as outfile:
                data = json.dumps(ent_map, ensure_ascii=False)
                outfile.write(unicode(data))

    
    def format_nel_sentences(self, nerfile, entfile):
        """
        Merge named entities with common entities if they overlap. 
        """
        sentences = []
        ent_map = {}
        ner_sents = self.get_entities_from_file(nerfile, 'ner')
        ent_sents = self.get_entities_from_file(entfile, 'com')
        for x in range(0,len(ner_sents)):
            entity = 0 if (ner_sents[x][1] == 0 and ent_sents[x][1] == 0) else 1
            ner_tagged = ner_sents[x][2]
            ent_tagged = ent_sents[x][2]
            # Detect overlaps and merge NEs and common entities
            tagged = self.merge_entities(ner_tagged, ent_tagged)
            sentences.append((x,entity,tagged))
            # Create a mapping so that NEs and common entities can be identified later
            ent_map[x] = self.create_map_entities(tagged)
        return (sentences, ent_map)
    
        
    def get_entities_from_file(self, filename, label):
        """
        Read files in which entities are marked and extract tagged lists
        """
        sentences = []
        tagged_sent = []
        entity = False
        ent_counter = 0
        sent_counter = 0
        prev_tag = 'O'
        with open(filename) as f:
            for line in f:
                if line == '\n':
                    sentences.append((sent_counter,int(entity),tagged_sent))
                    tagged_sent = []
                    entity = False
                    sent_counter += 1
                    ent_counter = 0
                    prev_tag = 'O'
                else:
                    toks = line.rstrip('\n').split('\t')
                    if toks[1] == 'O': # Not part of an entity
                        tagged_sent.append((toks[0],str(0)))
                    else: # Part of an entity
                        entity = True
                        if prev_tag == 'O' or toks[1][0] == 'B' or ('-' in prev_tag and '-' in toks[1] and prev_tag.split('-')[1] != toks[1].split('-')[1]): # Part of a NEW entity
                            ent_counter += 1
                        #tagged_sent.append((toks[0],label+str(ent_counter)))
                        tagged_sent.append((toks[0],toks[1]))
                    prev_tag = toks[1]
        return sentences


    def merge_entities(self, ner_tagged, ent_tagged):
        """
        Merge NEs and common entities, handling overlaps
        """
        overlaps = []
        # Detect overlaps: where the NER tool found a named entity and the parser found a noun
        for t in range(0,len(ner_tagged)):
            if ner_tagged[t][1] != '0' and ent_tagged[t][1] != '0':
                if ent_tagged[t][1] not in overlaps:
                    overlaps.append(ent_tagged[t][1])
        # Remove the overlaps
        tagged = []
        for t in range(0,len(ner_tagged)):
            if ner_tagged[t][1] != '0':
                tagged.append(ner_tagged[t])
            elif ent_tagged[t][1] != '0' and ent_tagged[t][1] not in overlaps:
                tagged.append(ent_tagged[t])
            else:
                tagged.append(ner_tagged[t])
        return tagged   

    def create_map_entities(self, tagged):
        """
        Create a mapping for NEs and common entities
        """
        m = {}
        prev_tag = '0'
        ent_list = []
        entpresent = False
        start = 0
        for t in range(0,len(tagged)):
            token = tagged[t][0]
            tag = tagged[t][1]
            if tag != prev_tag:
                if entpresent:
                    if tag != '0':
                        ent_string = ' '.join(ent_list)
                        m[start+1] = (ent_string, prev_tag)
                        ent_list = [token]
                        entpresent = True
                        start = t
                    else:
                        ent_string = ' '.join(ent_list)
                        m[start+1] = (ent_string, prev_tag)
                        ent_list = []
                        entpresent = False
                else:
                    ent_list = [token]
                    entpresent = True
                    start = t
            elif tag == prev_tag and entpresent:
                ent_list.append(token)
            prev_tag = tag
        if entpresent:
            ent_string = ' '.join(ent_list)
            m[start+1] = (ent_string, prev_tag)
        return m
        
        