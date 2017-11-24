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
from nltk.tag import StanfordNERTagger
from itertools import izip


class Ner():

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
        

    # Read UDPipe files and output one token per line, save as a text file
    def pre_process_ner(self):
        # Get output directory
        outdir = self.config.get('NER','pre_proc_out_dir')
        # Get UDPipe-processed files
        indir = self.config.get('UDPipe','out_dir')
        files = glob.glob(self.home+'/'+indir+'/*')
        for f in files:
            sentences = self.extract_sentences(f)
            outfilename = self.home + '/' + outdir + '/' + f.split('/')[-1].split('.')[0] + '.tsv'
            with open(outfilename, 'w') as outfile:
                for sent in sentences:
                    for tok in sent:
                        outfile.write(tok+'\n')
                    outfile.write('\n')


    # Extract sentences from UDPipe output
    def extract_sentences(self, filename):
        with open(filename,'r') as f:
            tokens = []
            skip_toks = []
            sentences = []
            with open(filename, 'r') as f:
                for line in f:
                    if line[0] != '#':
                        if line == '\n':
                            if tokens != []: # In case of multiple empty lines
                                sentences.append(tokens)
                            tokens = []
                        else:
                            elements = line.split('\t')
                            if '-' not in elements[0]:
                                tokens.append(elements[1])
#                            if '-' in elements[0]:
#                                skip_toks = elements[0].split('-')
#                                tokens.append(elements[1])
#                            else:
#                                if elements[0] not in skip_toks:
#                                    tokens.append(elements[1])
            return sentences
    
                        
    # Perform NER using GermaNER
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


    # Perform NER using Stanford NER
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
