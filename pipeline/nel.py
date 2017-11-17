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
        print('Named Entity Linking')
        # Extract nouns
        self.detect_nouns()
        # Apply NEL using Agdistis
        self.agdistis()
#        common_entities = self.config.get('NEL', 'common_entities')
#        if common_entities == 'spotlight':
#            # Apply entity disambiguation using DBPedia Spotlight
#            self.dbpspotlight()
        

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
            

    # Clean up after multi-word-spanning entities
    def clean_entity_sentence(self, s):
        s = s.replace('</nentity> <nentity>',' ')
        s = s.replace('</centity> <centity>',' ')
        s = s.replace('<nentity>','<entity>')
        s = s.replace('<centity>','<entity>')
        s = s.replace('</nentity>','</entity>')
        s = s.replace('</centity>','</entity>')
        s = s.rstrip(' ')
        return s


    # Add <entity></entity> tags around each NE
    def format_nel_sentences(self, nerfile, entfile):
        sentences = []
        sent = ''
        entity = False
        counter = 0
        with open(nerfile) as n, open(entfile) as e:
            for nline, eline in izip(n, e):
                if nline == '\n':
                    clean_sent = self.clean_entity_sentence(sent)
                    sentences.append((counter,int(entity),clean_sent))
                    sent = ''
                    entity = False
                    counter += 1
                else:
                    ntoks = nline.rstrip('\n').split('\t')
                    etoks = eline.rstrip('\n').split('\t')
                    if ntoks[1] == 'O' and etoks[1] == 'O': # Not an entity
                        sent += ntoks[0] + ' '
                    elif ntoks[1] != 'O': # Named entities take precedence
                        entity = True
                        sent += '<nentity>' + ntoks[0] + '</nentity> '
                    elif etoks != 'O':
                        entity = True
                        sent += '<centity>' + etoks[0] + '</centity> '
                    else:
                        pass
        return sentences


        # Add <entity></entity> tags around each NE
#        def format_nel_sentences(self, filename):
#            sentences = []
#            sent = ''
#            entity = False
#            counter = 0
#            with open(filename, 'r') as infile:
#                nerreader = csv.reader(infile, delimiter='\t', quotechar='|')
#                for row in nerreader:
#                    if row == []:
#                        clean_sent = self.clean_entity_sentence(sent)
#                        sentences.append((counter,int(entity),clean_sent))
#                        sent = ''
#                        entity = False
#                        counter += 1
#                    else:
#                        if row[1] == 'O': # Not an entity
#                            sent += row[0] + ' '
#                        else:
#                            entity = True
#                            sent += '<entity>' + row[0] + '</entity> '
#            return sentences

        
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

                
    # Disambiguate entities using DBPedia Spotlight
    def dbpspotlight(self):
        # Get UDPipe-processed files
        indir = self.config.get('UDPipe','out_dir')
        outdir = self.config.get('Spotlight','out_dir')
        url = self.config.get('Spotlight','url')
        confidence = self.config.get('Spotlight','confidence')
        support = self.config.get('Spotlight','support')
        spot = DBPediaSpotlight(url)
        files = glob.glob(self.home+'/'+indir+'/*')
        # Get DBPedia to FIGER mapping
        type_map = self.get_dbpedia_to_figer_mapping()
        for f in files:
            nel = {"file": f, "sentences": {}}
            sentences = self.extract_sentences(f)
            for x in range(0,len(sentences)):
                sentstring = ' '.join(sentences[x])
                annotations = spot.disambiguate(sentstring, confidence=confidence, support=support)
                renamed = self.rename_spotlight_keys(annotations)
                converted = self.map_and_convert_nel(sentstring, renamed, type_map)
                nel["sentences"][x] = converted
            # Write to file
            outfilename = self.home + '/' + outdir + '/' + f.split('/')[-1].split('.')[0] + '.json'
            with io.open(outfilename, 'w', encoding='utf8') as outfile:
                data = json.dumps(nel, ensure_ascii=False)
                outfile.write(unicode(data))


    # Rename keys from dbpedia spotlight to match those produced by Agdistis
    def rename_spotlight_keys(self, anns):
        renamed = []
        for a in anns:
            r = {}
            offset = 0
            for prop in a:
                if prop == 'URI':
                    r['disambiguatedURL'] = a[prop]
                elif prop == 'offset':
                    r['start'] = a[prop]
                elif prop == 'surfaceForm':
                    r['namedEntity'] = a[prop]
                    if isinstance(a[prop], (int,long)):
                        offset = len(str(a[prop]))
                    else:
                        offset = len(a[prop].encode('utf-8'))
                else:
                    r[prop] = a[prop]
            r['offset'] = offset
            renamed.append(r)
        return renamed
        

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
