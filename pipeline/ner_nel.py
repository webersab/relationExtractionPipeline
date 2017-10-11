#!/usr/bin/env python
# -*- coding: utf-8 -*-

# HELPFUL starter code
# https://github.com/ufal/udpipe/blob/master/bindings/python/examples/run_udpipe.py
# https://github.com/ufal/udpipe/blob/master/bindings/python/examples/udpipe_model.py

# Standard
import io
import gzip
import collections
import sys
import codecs
import glob
import csv
import ConfigParser
import logging
import subprocess
import simplejson as json
from nltk.tag import StanfordNERTagger


# Custom
from agdistis import Agdistis


class NerNel():

    def __init__(self, config):
        self.config = config
        self.home = self.config.get('General', 'home')


    def NER(self):
        print('process: NER')
        # Format file with one token per line (take tokenisation from UDPipe)
        self.pre_process_ner()
        # Apply NER using GermaNER
        # GermaNER(configmap)
        # Apply NER using Stanford NER
        self.StanfordNER()
        # Apply NEL using Agdistis
        freebase_map = self.get_freebase_mapping()
        self.agdistis(freebase_map)


    # Read UDPipe files and output one token per line, save as a text file
    def pre_process_ner(self):
        # Get output directory
        outdir = self.config.get('NER','pre_proc_out_dir')
        # Get UDPipe-processed files
        indir = self.config.get('UDPipe','out_dir')
        files = glob.glob(self.home+'/'+indir+'/*')
        for f in files:
            tokens = []
            skip_toks = []
            with open(f, 'r') as infile:
                for line in infile:
                    if line[0] != '#':
                        if line == '\n':
                            tokens.append('\n')
                            skip_toks = []
                        else:
                            elements = line.split('\t')
                            if '-' in elements[0]:
                                skip_toks = elements[0].split('-')
                                tokens.append(elements[1])
                            else:
                                if elements[0] not in skip_toks:
                                    tokens.append(elements[1])
            outfilename = self.home + '/' + outdir + '/' + f.split('/')[-1].split('.')[0] + '.tsv'
            with open(outfilename, 'w') as outfile:
                for tok in tokens:
                    if tok == '\n':
                        outfile.write(tok)
                    else:
                        outfile.write(tok+'\n')


    def GermaNER(self):
        # Get jar file path
        jar_file = self.config.get('GermaNER','jar_file')
        # Get input and output directories, and input files
        indir = self.config.get('NER','pre_proc_out_dir')
        outdir = self.config.get('NER','out_dir')
        files = glob.glob(self.home+'/'+indir+'/*.tsv')
        for f in files:
            outfile = self.home + '/' + outdir + '/' + f.split('/')[-1]
            # Perform NER
            subprocess.call(['java', '-jar', jar_file, '-t', f, '-o', outfile])


    def StanfordNER(self):
        # Get jar file path
        jar_file = self.config.get('StanfordNER','jar_file')
        model_file = self.config.get('StanfordNER','model_file')
        # Get input and output directories, and input files
        indir = self.config.get('NER','pre_proc_out_dir')
        outdir = self.config.get('NER','out_dir')
        files = glob.glob(self.home+'/'+indir+'/*.tsv')
        # Initialise NER tagger
        st = StanfordNERTagger(model_file, jar_file, encoding='utf-8')
        for f in files:
            raw_sentences = []
            tagged_sentences = []
            # Read tokenised raw sentences
            with open(f, 'r') as infile:
                tokens = []
                for line in infile:
                    if line == '\n':
                        raw_sentences.append(tokens)
                        tokens = []
                    else:
                        tokens.append(line.rstrip('\n'))
            # Tag sentences
            for sent in raw_sentences:
                tagged_sent = st.tag(sent)
                tagged_sentences.append(tagged_sent)
            # Write tagged sentences to file
            outfilename = self.home + '/' + outdir + '/' + f.split('/')[-1]
            with codecs.open(outfilename, 'w', 'utf-8') as outfile:
                for sent in tagged_sentences:
                    for tok in sent:
                        outfile.write(tok[0]+'\t'+tok[1]+'\n')
                    outfile.write('\n')


    # Clean up after multi-word-spanning entities
    def clean_entity_sentence(self, s):
        s = s.replace('</entity> <entity>',' ')
        s = s.rstrip(' ')
        return s


    # Add <entity></entity> tags around each NE
    def format_nel_sentences(self, filename):
        sentences = []
        sent = ''
        entity = False
        counter = 0
        with open(filename, 'r') as infile:
            nerreader = csv.reader(infile, delimiter='\t', quotechar='|')
            for row in nerreader:
                if row == []:
                    clean_sent = self.clean_entity_sentence(sent)
                    sentences.append((counter,int(entity),clean_sent))
                    sent = ''
                    entity = False
                    counter += 1
                else:
                    if row[1] == 'O': # Not an entity
                        sent += row[0] + ' '
                    else:
                        entity = True
                        sent += '<entity>' + row[0] + '</entity> '
        return sentences


    # Named Entity linking using Agdistis
    def agdistis(self, f_map):
        indir = self.config.get('NER','out_dir')
        outdir = self.config.get('Agdistis','out_dir')
        url = self.config.get('Agdistis','url')
        files = glob.glob(self.home+'/'+indir+'/*.tsv')
        ag = Agdistis(url)
        for f in files:
            # Read file and format sentences
            formatted = self.format_nel_sentences(f)
            nel = {"file": f, "sentences": {}}
            for sent in formatted:
                if sent[1] == 1:
                    # Disambiguate using NEL
                    disambig = ag.disambiguate(sent[2])
                    # Map to Freebase, convert to dictionary 
                    converted = self.map_and_convert_nel(sent[2], disambig, f_map)
                    nel["sentences"][sent[0]] = converted
            # Write to file
            outfilename = self.home + '/' + outdir + '/' + f.split('/')[-1].split('.')[0] + '.json'
            with io.open(outfilename, 'w', encoding='utf8') as outfile:
                data = json.dumps(nel, ensure_ascii=False)
                outfile.write(unicode(data))


    # Convert unicode to string
    # Taken from StackOverflow:
    # https://stackoverflow.com/questions/1254454/fastest-way-to-convert-a-dicts-keys-values-from-unicode-to-str
    def convert(self, data):
        if isinstance(data, basestring):
            return data.encode('utf-8')
        elif isinstance(data, collections.Mapping):
            return dict(map(self.convert, data.iteritems()))
        elif isinstance(data, collections.Iterable):
            return type(data)(map(self.convert, data))
        else:
            return data


    # Map the DBPedia urls to Freebase urls
    def map_and_convert_nel(self, sent_str, nel_output, f_map):
        conv_nel = {"sentenceStr": sent_str, "entities": {}}
        counter = 0
        for e in nel_output:
            dbpedia_url = e["disambiguatedURL"]
            # Map to Freebase
            if dbpedia_url in f_map:
                freebase_url = f_map[dbpedia_url]
            else:
                freebase_url = "no_freebase_link"
            e["freebaseURL"] = freebase_url
            conv = self.convert(e)
            conv_nel["entities"][counter] = conv
            counter += 1
        return conv_nel


    def get_freebase_mapping(self):
        m = {}
        freebasefile = self.config.get('Freebase','freebase_links_file')
        with gzip.open(freebasefile, 'r') as f:
            for line in f:
                if line[0] != '#':
                    elements = line.split(' ')
                    dbpedia_url = elements[0].lstrip('<').rstrip('>')
                    freebase_url = elements[2].lstrip('<').rstrip('>')
                    m[dbpedia_url] = freebase_url
        return m