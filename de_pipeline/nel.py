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

# Custom
import helper_functions as hf
from agdistis import Agdistis
from datetime import datetime

class Nel():

    """
    Perform entity linking using AGDISTIS
    Input: common and named entities
    Output: entities linked to DBPedia, and through Freebase to FIGER types
    """
    
    def __init__(self, config):
        self.config = config
        self.home = self.config.get('General', 'home')
        

    def process(self, files):
        """
        Main method
        """
        print('NER and parsing complete\nNamed Entity Linking')
        logging.info('started NEL: '+str(datetime.now()))
        # Extract nouns
        self.detect_nouns(files)
        # Apply NEL using Agdistis
        self.agdistis(files)
        logging.info('ended NEL: '+str(datetime.now()))
        

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
            

    def format_nel_sentences(self, nerfile, entfile):
        """
        Format sentence string for input to AGDISTIS
        Add <entity></entity> tags around each entity
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
            # Output a formatted sentence
            formatted_sent = self.add_entity_tags(tagged)
            sentences.append((x,entity,formatted_sent))
            # Create a mapping so that NEs and common entities can be identified later
            ent_map[x] = self.create_map_entities(tagged)
        return (sentences, ent_map)


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
    

    def add_entity_tags(self, tagged):
        """
        Format the tagged sentences - add <entity></entity> tags
        """
        formatted_sent = ''
        prev_tag = '0'
        entpresent = False
        for t in range(0,len(tagged)):
            if tagged[t][1] != prev_tag:
                if entpresent:
                    if tagged[t][1] != '0':
                        formatted_sent += '</entity> <entity>' + tagged[t][0] + ' '
                        entpresent = True
                    else:
                        formatted_sent += '</entity> ' +tagged[t][0] + ' '
                        entpresent = False
                else:
                    formatted_sent += '<entity>' + tagged[t][0] + ' '
                    entpresent = True
            elif tagged[t][1] == prev_tag or tagged[t][1] == '0':
                formatted_sent += tagged[t][0] + ' '
            prev_tag = tagged[t][1]
        if entpresent: # Final token is the entity
            formatted_sent += '</entity>'
        formatted_sent = formatted_sent.replace(' </e', '</e').rstrip()
        return formatted_sent
    

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
                        tagged_sent.append((toks[0],label+str(ent_counter)))
                    prev_tag = toks[1]
        return sentences


    def get_dbpedia_to_figer_mapping(self):
        """
        Get DBPedia to FIGER mapping
        Use the mapping file that maps DBPedia->Freebase->FIGER
        """
        mapfile = self.config.get('TypeMapping','map_file')
        with gzip.open(mapfile, 'r') as mfile:
            m = json.load(mfile)
        return m

    
    def convert_offsets(self,sentence):
        """
        Convert character offset to token offset
        """
        conv = {}
        counter = 1
        for x in range(0,len(sentence)):
            if sentence[x] == ' ':
                counter += 1
            else:
                conv[x] = counter
        return conv


    def agdistis(self, files):
        """
        Named Entity linking using AGDISTIS
        """
        nerindir = self.config.get('NER','out_dir')
        entindir = self.config.get('Entities','out_dir')
        outdir = self.config.get('Agdistis','out_dir')
        url = self.config.get('Agdistis','url')
        nerfiles = sorted([self.home+'/'+nerindir+'/'+f for f in files])
        entfiles = sorted([self.home+'/'+entindir+'/'+f for f in files])
        ag = Agdistis(url)
        # Get DBPedia to FIGER mapping
        type_map = self.get_dbpedia_to_figer_mapping()
        for x in range(0,len(nerfiles)):
            nf = nerfiles[x]
            ef = entfiles[x]
            # Read file and format sentences
            temp = self.format_nel_sentences(nf, ef)
            formatted = temp[0]
            ent_map = temp[1]
            nel = {"file": nf.split('/')[-1], "sentences": {}}
            formatted_sents = [sent[2] for sent in formatted]
            text = '\n'.join(formatted_sents).decode('utf-8')
            for sent in range(0,len(formatted_sents)):
                if '<entity>' in formatted_sents[sent]:
                    disambig = ag.disambiguate(formatted_sents[sent])
                # For each sentence, map entities to Freebase, convert to dictionary
                    converted = self.map_and_convert_nel(sent, formatted_sents[sent], disambig, type_map, ent_map[sent])
                    nel["sentences"][sent] = converted
            # Write to file
            outfilename = self.home + '/' + outdir + '/' + nf.split('/')[-1]
            with io.open(outfilename, 'w', encoding='utf8') as outfile:
                data = json.dumps(nel, ensure_ascii=False)
                outfile.write(unicode(data))

                
    def disambiguated_entities_to_sent_number(self, disambig, char_map):
        """
        Map each disambiguated entity to its sentence
        """
        d = {}
        for ent in disambig:
            sent = char_map[ent["start"]]
            if sent in d:
                d[sent].append(ent)
            else:
                d[sent] = [ent]
        return d
    
                
    def map_and_convert_nel(self, sent_num, sent_str, nel_output, tm, em):
        """
        Map the DBPedia urls to Freebase urls
        """
        conv_nel = {"sentenceStr": sent_str, "entities": {}}
        clean_sent = sent_str.replace('<entity>','').replace('</entity>','')
        char_to_tok = self.convert_offsets(clean_sent.decode('utf-8'))
        counter = 0
        for e in nel_output:
            # Convert char to word indices
            start = e['start']
            offset = e['offset']
            starttok = char_to_tok[start]
            e["starttok"] = starttok
            e["endtok"] = char_to_tok[start+offset-1]
            # Map to FIGER
            dbpedia_url = e["disambiguatedURL"]
            figer_type = "none"
            if dbpedia_url in tm and tm[dbpedia_url] != '':
                figer_type = tm[dbpedia_url]
            e["FIGERType"] = figer_type
            # Add indicator of common entity or named entity
            e["entityType"] = em[starttok][1][0:3]
            # Convert numbers to strings
            if isinstance(e['namedEntity'], (int,long)):
                string_value = str(e['namedEntity'])
                e["namedEntity"] = string_value
            conv_nel["entities"][counter] = e
            counter += 1
        return conv_nel
