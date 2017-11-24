#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Standard
import io
import gzip
import sys
import codecs
import glob
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
        

    def NEL(self):
        print('NER and parsing complete\nNamed Entity Linking')
        # Extract nouns
        self.detect_nouns()
        # Apply NEL using Agdistis
        self.agdistis()
        

    # Extract noun spans
    def detect_nouns(self):
        # Get input and output directories, and input files
        indir = self.config.get('UnstableParser','post_proc_out_dir')
        outdir = self.config.get('Entities','out_dir')
        files = glob.glob(self.home+'/'+indir+'/*.conllu')
        for f in files:
            dtrees = hf.dependency_parse_to_graph(f)
            tagged_sents = hf.extract_entities_from_dependency_parse(dtrees, 'NOUN')
            outfilename = self.home + '/' + outdir + '/' + f.split('/')[-1].split('.')[0]+'.tsv'
            with open(outfilename, 'w') as f:
                for sent in tagged_sents:
                    for token in sent:
                        f.write(token[0].encode('utf-8')+'\t'+token[1]+'\n')
                    f.write('\n')
            

#    # Clean up after multi-word-spanning entities
#    def clean_entity_sentence(self, s):
#        s = s.replace('</nentity> <nentity>',' ')
#        s = s.replace('</centity> <centity>',' ')
#        s = s.replace('<nentity>','<entity>')
#        s = s.replace('<centity>','<entity>')
#        s = s.replace('</nentity>','</entity>')
#        s = s.replace('</centity>','</entity>')
#        s = s.rstrip(' ')
#        return s


#    # Add <entity></entity> tags around each NE
#    def format_nel_sentences_old(self, nerfile, entfile):
#        sentences = []
#        sent = ''
#        entity = False
#        counter = 0
#        with open(nerfile) as n, open(entfile) as e:
#            for nline, eline in izip(n, e):
#                if nline == '\n':
#                    clean_sent = self.clean_entity_sentence(sent)
#                    sentences.append((counter,int(entity),clean_sent))
#                    sent = ''
#                    entity = False
#                    counter += 1
#                else:
#                    ntoks = nline.rstrip('\n').split('\t')
#                    etoks = eline.rstrip('\n').split('\t')
#                    if ntoks[1] == 'O' and etoks[1] == 'O': # Not an entity
#                        sent += ntoks[0] + ' '
#                    elif ntoks[1] != 'O': # Named entities take precedence
#                        entity = True
#                        sent += '<nentity>' + ntoks[0] + '</nentity> '
#                    elif etoks != 'O':
#                        entity = True
#                        sent += '<centity>' + etoks[0] + '</centity> '
#                    else:
#                        pass
#        return sentences


    # Add <entity></entity> tags around each NE
    def format_nel_sentences(self, nerfile, entfile):
        sentences = []
        ner_sents = self.get_entities_from_file(nerfile, 'ner')
        ent_sents = self.get_entities_from_file(entfile, 'ent')
        for x in range(0,len(ner_sents)):
            entity = 0 if (ner_sents[x][1] == 0 and ent_sents[x][1] == 0) else 1
            ner_tagged = ner_sents[x][2]
            ent_tagged = ent_sents[x][2]
            # Detect overlaps and merge NEs and common entities
            tagged = self.merge_entities(ner_tagged, ent_tagged)
            # Output a formatted sentence
            formatted_sent = self.add_entity_tags(tagged)
            sentences.append((x,entity,formatted_sent))
            # Create 
        return sentences


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

    
    # Named Entity linking using Agdistis
    def agdistis(self):
        nerindir = self.config.get('NER','out_dir')
        entindir = self.config.get('Entities','out_dir')
        outdir = self.config.get('Agdistis','out_dir')
        url = self.config.get('Agdistis','url')
        nerfiles = sorted(glob.glob(self.home+'/'+nerindir+'/*.tsv'))
        entfiles = sorted(glob.glob(self.home+'/'+entindir+'/*.tsv'))
        ag = Agdistis(url)
        # Get DBPedia to FIGER mapping
        type_map = self.get_dbpedia_to_figer_mapping()
        for x in range(0,len(nerfiles)):
            nf = nerfiles[x]
            ef = entfiles[x]
            # Read file and format sentences
            formatted = self.format_nel_sentences(nf, ef)
            nel = {"file": nf.split('/')[-1], "sentences": {}}
            for sent in formatted:
                if sent[1] == 1:
                    # Disambiguate using NEL
                    disambig = ag.disambiguate(sent[2])
                    # Map to Freebase, convert to dictionary 
                    converted = self.map_and_convert_nel(sent[2], disambig, type_map)
                    nel["sentences"][sent[0]] = converted
            # Write to file
            outfilename = self.home + '/' + outdir + '/' + nf.split('/')[-1].split('.')[0] + '.json'
            with io.open(outfilename, 'w', encoding='utf8') as outfile:
                data = json.dumps(nel, ensure_ascii=False)
                outfile.write(unicode(data))

                
#    # Disambiguate entities using DBPedia Spotlight
#    def dbpspotlight(self):
#        # Get UDPipe-processed files
#        indir = self.config.get('UDPipe','out_dir')
#        outdir = self.config.get('Spotlight','out_dir')
#        url = self.config.get('Spotlight','url')
#        confidence = self.config.get('Spotlight','confidence')
#        support = self.config.get('Spotlight','support')
#        spot = DBPediaSpotlight(url)
#        files = glob.glob(self.home+'/'+indir+'/*')
#        # Get DBPedia to FIGER mapping
#        type_map = self.get_dbpedia_to_figer_mapping()
#        for f in files:
#            nel = {"file": f, "sentences": {}}
#            sentences = self.extract_sentences(f)
#            for x in range(0,len(sentences)):
#                sentstring = ' '.join(sentences[x])
#                annotations = spot.disambiguate(sentstring, confidence=confidence, support=support)
#                renamed = self.rename_spotlight_keys(annotations)
#                converted = self.map_and_convert_nel(sentstring, renamed, type_map)
#                nel["sentences"][x] = converted
#            # Write to file
#            outfilename = self.home + '/' + outdir + '/' + f.split('/')[-1].split('.')[0] + '.json'
#            with io.open(outfilename, 'w', encoding='utf8') as outfile:
#                data = json.dumps(nel, ensure_ascii=False)
#                outfile.write(unicode(data))


#    # Rename keys from dbpedia spotlight to match those produced by Agdistis
#    def rename_spotlight_keys(self, anns):
#        renamed = []
#        for a in anns:
#            r = {}
#            offset = 0
#            for prop in a:
#                if prop == 'URI':
#                    r['disambiguatedURL'] = a[prop]
#                elif prop == 'offset':
#                    r['start'] = a[prop]
#                elif prop == 'surfaceForm':
#                    r['namedEntity'] = a[prop]
#                    if isinstance(a[prop], (int,long)):
#                        offset = len(str(a[prop]))
#                    else:
#                        offset = len(a[prop].encode('utf-8'))
#                else:
#                    r[prop] = a[prop]
#            r['offset'] = offset
#            renamed.append(r)
#        return renamed
        

    # Map the DBPedia urls to Freebase urls
    def map_and_convert_nel(self, sent_str, nel_output, m):
        conv_nel = {"sentenceStr": sent_str, "entities": {}}
        counter = 0
        for e in nel_output:
            dbpedia_url = e["disambiguatedURL"]
            figer_type = "none"
            if dbpedia_url in m and m[dbpedia_url] != '':
                figer_type = m[dbpedia_url]
            e["FIGERType"] = figer_type
            conv = hf.convert_unicode_to_str(e)
            conv_nel["entities"][counter] = conv
            counter += 1
        return conv_nel
