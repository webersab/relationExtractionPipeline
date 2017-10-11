#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Standard
import sys
import codecs
import glob
import logging
from datetime import datetime

# Custom
import udpipe_model as udp


class Preprocessor():

    def __init__(self, config):
        self.config = config


    # UDPipe pre-processing
    def udpipe(self):
        # Get home directory
        home = self.config.get('General','home')
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
        indir = self.config.get('Input','data')
        files = glob.glob(home+'/'+indir+'/*.txt') 
        for infile in files:
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
            outfilename = infile.split('/')[-1].split('.')[0]+'.conllu'
            outfile = home+'/'+outdir+'/'+outfilename
            with codecs.open(outfile, 'w', 'utf-8') as o:
                o.write(conllu)
