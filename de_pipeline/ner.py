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
import sner
#from nltk.tag import StanfordNERTagger
#from nltk.internals import config_java
from itertools import izip
from datetime import datetime


class Ner():

    """
    Perform named entity recognition using Stanford NER
    Input: (word) tokenised sentences
    Output: named entity tagged sentences
    """
    
    def __init__(self, config):
        self.config = config
        self.home = self.config.get('General', 'home')
#        Increase memory allocation to Stanford NER if run via nlty
#        config_java(options='-xmx2G')

        
    def process(self, files):
        """
        Main method
        Includes a call to GermaNER which could be used as an alternative to Stanford NER
        """
        print('process: NER')
        # Format file with one token per line (take tokenisation from UDPipe)
        self.pre_process_ner(files)
        # Apply NER using GermaNER - not currently used but could be an alternative
        # GermaNER(configmap)
        # Apply NER using Stanford NER - currently in use
        self.StanfordNER(files)
        

    def pre_process_ner(self, files):
        """
        Read UDPipe files and output one token per line, save as a text file
        """
        # Get output directory
        outdir = self.config.get('NER','pre_proc_out_dir')
        # Get UDPipe-processed files
        indir = self.config.get('UDPipe','out_dir')
        for f in files:
            infile = self.home + '/' + indir + '/' + f
            sentences = self.extract_sentences(infile)
            outfilename = self.home + '/' + outdir + '/' + f
            with open(outfilename, 'w') as outfile:
                for sent in sentences:
                    for tok in sent:
                        outfile.write(tok+'\n')
                    outfile.write('\n')


    def extract_sentences(self, filename):
        """
        Extract (word tokenised) sentences from UDPipe output
        """
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
            return sentences
    
                        
#    def GermaNER(self, files):
#        """
#        Perform NER using GermaNER
#        """
#        # Get jar file path
#        jar_file = self.config.get('GermaNER','jar_file')
#        # Get input and output directories, and input files
#        indir = self.config.get('NER','pre_proc_out_dir')
#        outdir = self.config.get('NER','out_dir')
#        for f in files:
#            outfile = self.home + '/' + outdir + '/' + f.split('/')[-1]
#            # Perform NER
#            subprocess.call(['java', '-jar', jar_file, '-t', f, '-o', outfile])


    def StanfordNER(self, files):
        """
        Perform NER using Stanford NER 
        """
        # Get NER server hostname
        ner_host = self.config.get('StanfordNER','host_name')
        # Get input and output directories, and input files
        indir = self.config.get('NER','pre_proc_out_dir')
        outdir = self.config.get('NER','out_dir')
        # Initialise NER server
        st = sner.Ner(host=ner_host,port=9199)
        for f in files:
            fpath = self.home + '/' + indir + '/' + f
            raw_sentences = []
            tagged_sentences = []
            # Read tokenised raw sentences
            with open(fpath, 'r') as infile:
                tokens = []
                for line in infile:
                    if line == '\n':
                        raw_sentences.append(tokens)
                        tokens = []
                    else:
                        tokens.append(line.rstrip('\n'))
            # Tag sentences
            for sent in raw_sentences:
                s = ' '.join(sent)
                tagged_sent = st.tag(s.decode('utf8'))
                tagged_sentences.append(tagged_sent)
            # Write tagged sentences to file
            outfilename = self.home + '/' + outdir + '/' + f
            with codecs.open(outfilename, 'w', 'utf-8') as outfile:
                for sent in tagged_sentences:
                    for tok in sent:
                        outfile.write(tok[0].lstrip('\n')+'\t'+tok[1]+'\n')
                    outfile.write('\n')
