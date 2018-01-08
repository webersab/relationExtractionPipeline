#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Standard
import io
import gzip
import sys
import codecs
#import glob
import csv
import ConfigParser
import logging
import subprocess
import simplejson as json
from itertools import izip


# Custom
import helper_functions as hf
from agdistis import Agdistis
from dbpedia_spotlight import DBPediaSpotlight


class Nel():

    def __init__(self, config):
        self.config = config
        self.home = self.config.get('General', 'home')
        

    def NEL(self, files):
        print('NER and parsing complete\nNamed Entity Linking')
        # Extract nouns
        self.detect_nouns(files)
        # Apply NEL using Agdistis
        self.agdistis(files)
        

    # Extract noun spans
    def detect_nouns(self, files):
        # Get input and output directories, and input files
        indir = self.config.get('UnstableParser','post_proc_out_dir')
        outdir = self.config.get('Entities','out_dir')
#        files = glob.glob(self.home+'/'+indir+'/*.conllu')
        for f in files:
            infile = indir + '/' + f
            dtrees = hf.dependency_parse_to_graph(infile)
            tagged_sents = hf.extract_entities_from_dependency_parse(dtrees, 'NOUN')
            outfilename = self.home + '/' + outdir + '/' + f#.split('/')[-1].split('.')[0]+'.tsv'
            with open(outfilename, 'w') as f:
                for sent in tagged_sents:
                    for token in sent:
                        f.write(token[0].encode('utf-8')+'\t'+token[1]+'\n')
                    f.write('\n')
            

    # Add <entity></entity> tags around each entity
    def format_nel_sentences(self, nerfile, entfile):
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


    # Create a mapping for NEs and common entities
    def create_map_entities(self, tagged):
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
        return m
    
    
    # Merge NEs and common entities, handling overlaps
    def merge_entities(self, ner_tagged, ent_tagged):
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
    

    # Format the tagged sentences
    def add_entity_tags(self, tagged):
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
        formatted_sent = formatted_sent.replace(' </e', '</e').rstrip()
        return formatted_sent
    

    # Read files in which entities are marked and extract tagged lists
    def get_entities_from_file(self, filename, label):
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
                        if prev_tag == 'O' or toks[1][0] == 'B': # Part of a NEW entity
                            ent_counter += 1
                        tagged_sent.append((toks[0],label+str(ent_counter)))
                    prev_tag = toks[1]
        return sentences


    # Get DBPedia to FIGER mapping
    def get_dbpedia_to_figer_mapping(self):
        mapfile = self.config.get('TypeMapping','map_file')
        with gzip.open(mapfile, 'r') as mfile:
            m = json.load(mfile)
        return m

    
    # Convert character offset to token offset
    def convert_offsets(self,sentence):
        conv = {}
        counter = 1
        for x in range(0,len(sentence)):
            if sentence[x] == ' ':
                counter += 1
            else:
                conv[x] = counter
        return conv


    # Named Entity linking using Agdistis
    def agdistis(self, files):
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
            disambig = ag.disambiguate(text)
            # Determine which sentence each disambiguated entity belongs to (using the start offset)
            clean_text = text.replace('<entity>','').replace('</entity>','')
            char_to_sent_map = self.char_to_sent_number(clean_text)
            # Split disambiguated entities by sentence
            disambig_map = self.disambiguated_entities_to_sent_number(disambig, char_to_sent_map)
            sent_start = 0
            for sent in range(0,len(formatted_sents)):
                # For each sentence, map entities to Freebase, convert to dictionary
                if sent in disambig_map:
                    converted = self.map_and_convert_nel(sent, sent_start, formatted[sent][2], disambig_map[sent], type_map, ent_map[sent])
                    nel["sentences"][sent] = converted
                sent_start += len(formatted[sent][2].replace('<entity>','').replace('</entity>','').decode('utf-8')) +1# +1 is for the line break at the end of each sentence
            # Write to file
            outfilename = self.home + '/' + outdir + '/' + nf.split('/')[-1]#.split('.')[0] + '.json'
            with io.open(outfilename, 'w', encoding='utf8') as outfile:
                data = json.dumps(nel, ensure_ascii=False)
                outfile.write(unicode(data))

                
    # Map each disambiguated entity to its sentence
    def disambiguated_entities_to_sent_number(self, disambig, char_map):
        d = {}
        for ent in disambig:
            sent = char_map[ent["start"]]
            if sent in d:
                d[sent].append(ent)
            else:
                d[sent] = [ent]
        return d
    
                
    # For each character in a text, find the sentence number
    def char_to_sent_number(self, text):
        d = {}
        counter = 0
        for x in range(0,len(text)):
            d[x] = counter
            if text[x] == '\n':
                counter += 1
        return d

#    # Named Entity linking using Agdistis
#    def agdistis(self, files):
#        nerindir = self.config.get('NER','out_dir')
#        entindir = self.config.get('Entities','out_dir')
#        outdir = self.config.get('Agdistis','out_dir')
#        url = self.config.get('Agdistis','url')
#        nerfiles = sorted([self.home+'/'+nerindir+'/'+f for f in files])
#        entfiles = sorted([self.home+'/'+entindir+'/'+f for f in files])
#        ag = Agdistis(url)
#        # Get DBPedia to FIGER mapping
#        type_map = self.get_dbpedia_to_figer_mapping()
#        for x in range(0,len(nerfiles)):
#            nf = nerfiles[x]
#            ef = entfiles[x]
#            # Read file and format sentences
#            temp = self.format_nel_sentences(nf, ef)
#            formatted = temp[0]
#            ent_map = temp[1]
#            nel = {"file": nf.split('/')[-1], "sentences": {}}
#            counter = 0
#            for sent in formatted:
#                if sent[1] == 1:
#                    # Disambiguate using NEL
#                    disambig = ag.disambiguate(sent[2])
#                    # Map to Freebase, convert to dictionary 
#                    converted = self.map_and_convert_nel(sent[2], disambig, type_map, ent_map[counter])
#                    nel["sentences"][sent[0]] = converted
#                counter += 1
#            # Write to file
#            outfilename = self.home + '/' + outdir + '/' + nf.split('/')[-1]#.split('.')[0] + '.json'
#            with io.open(outfilename, 'w', encoding='utf8') as outfile:
#                data = json.dumps(nel, ensure_ascii=False)
#                outfile.write(unicode(data))

                
    # Map the DBPedia urls to Freebase urls
    def map_and_convert_nel(self, sent_num, sent_start, sent_str, nel_output, tm, em):
        conv_nel = {"sentenceStr": sent_str, "entities": {}}
        clean_sent = sent_str.replace('<entity>','').replace('</entity>','')
        char_to_tok = self.convert_offsets(clean_sent.decode('utf-8'))
        counter = 0
        for e in nel_output:
            # Convert char to word indices
            #start = e['start']
            start = e['start'] - sent_start
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
            #conv = hf.convert_unicode_to_str(e)
            conv_nel["entities"][counter] = e
            counter += 1
        return conv_nel
