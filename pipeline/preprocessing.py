#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Standard
import sys
import codecs
#import glob
import logging
import nltk.data
from datetime import datetime

# Custom
import udpipe_model as udp


class Preprocessor():

    def __init__(self, config):
        self.config = config
        # Get home directory
        self.home = self.config.get('General','home')

        
    # Split sentences using NLTKs PunktTokenizer
    def split_sentences(self, files):
        file_list = []
        indir = self.config.get('Input','raw_input')
        outdir = self.config.get('Preprocessor','out_dir')
        model = self.config.get('Preprocessor','seg_model')
        splitter = nltk.data.load(model)
#        files = glob.glob(self.home+'/'+indir+'/*.txt')
        for f in files:
            infile = indir + '/' + f
            # Read text
            with open(infile) as i:
                text = ''.join(i.readlines())
            # Sentence split text
            segs = splitter.tokenize(text.decode('utf-8'))
            if len(segs) >= 10:
                file_list.append(f)
#            outfilename = infile.split('/')[-1]
            outfile = self.home+'/'+outdir+'/'+f#outfilename
            with codecs.open(outfile, 'w', 'utf-8') as o:
                for seg in segs:
                    o.write(seg+'\n')
        return file_list
                    
            
    # UDPipe pre-processing
    def udpipe(self, files):
        # Get UDPipe configurations
        outformat = self.config.get('UDPipe','out_format')
        outdir = self.config.get('UDPipe','out_dir')
        modelfile = self.config.get('UDPipe','model')
        # Load the model
        logging.info('Loading model: ')  
        try:
            model = udp.UDPipeModel(modelfile)
        except Exception:
            message = "ERROR: Cannot load model from file '%s'\n" % modelfile
            logging.error(message+'  Exited at: '+str(datetime.now())+'\n\n')
            sys.stderr.write(message)
            sys.exit(1)
        logging.info('...complete')
        # Process input files
        logging.info('Processing input files:')
        indir = self.config.get('Preprocessor','out_dir')
#        files = glob.glob(self.home+'/'+indir+'/*.txt') 
        for f in files:
            infile = indir + '/' + f
            logging.info('  '+infile)
            # Read text
            with open(infile) as i:
                text = ''.join(i.readlines())
            # Tokenise, tag, and parse
            sentences = model.tokenize(text)
            for s in sentences:
                model.tag(s)
                model.parse(s)
            # Output to file
            conllu = model.write(sentences, outformat)
#            outfilename = infile.split('/')[-1].split('.')[0]#+'.conllu'
            outfile = self.home+'/'+outdir+'/'+f#outfilename
            with codecs.open(outfile, 'w', 'utf-8') as o:
                o.write(conllu)
