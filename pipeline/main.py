#!/usr/bin/env python
# -*- coding: utf-8 -*-

# HELPFUL starter code
# https://github.com/ufal/udpipe/blob/master/bindings/python/examples/run_udpipe.py
# https://github.com/ufal/udpipe/blob/master/bindings/python/examples/udpipe_model.py

# Standard
import sys
import codecs
import locale
import glob
import ConfigParser
import logging
from datetime import datetime

# Custom
sys.path.insert(0,'/afs/inf.ed.ac.uk/user/l/lguillou/Tools/UnstableParser')
import udpipe_model as udp
import unstable_parser as up
import unstable_parser_post_proc as postproc


# Extract config json from file
def get_config(configfile):
    cfg = ConfigParser.ConfigParser()
    cfg.read(configfile)
    return cfg


# UDPipe pre-processing
def udpipe(config):
    # Get home directory
    home = config.get('General','home')
    # Get UDPipe configurations
    outformat = config.get('UDPipe','out_format')
    outdir = config.get('UDPipe','out_dir')
    modelfile = config.get('UDPipe','model')
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
    indir = config.get('Input','data')
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


# Parse with the UnstableParser
def unstable_parser(config):
    # Get parser path
    parserpath = config.get('UnstableParser','path')
    # Get home directory
    home = config.get('General','home')
    # Get input directory (output of udpipe)
    indir = config.get('UDPipe','out_dir')
    # Get UnstableParser configurations
    parserconfig = config.get('UnstableParser','config_file')
    savedir = config.get('UnstableParser','save_dir')
    outdir = config.get('UnstableParser','out_dir')
    files = glob.glob(home+'/'+indir+'/*')
    # Initialise parser
    logging.info('Initialising the UnstableParser:')
    parser = up.UnstableParser(parserpath, savedir)
    # Parse each file
    outputdir = home + '/' + outdir
    logging.info('Parsing input files in: ' + indir)
    parser.parse(outputdir, files)
#    for infile in files:
#        logging.info('  '+infile)
#        outputfile = infile.split('/')[-1].split('.')[0]+'-unstable.conllu'
#        parser.parse(outputdir, [infile])
#        parser.parse(outputdir, outputfile, [infile])
        

# Post-process the UnstableParser output (German only)
def post_process_parsed_output(config):
    # Get language
    language = config.get('General','language')
    # Step is required for German only
    if language == 'de':
        # Get home directory
        home = config.get('General','home')
        # Get original files directory (output of UDPipe)
        origdir = config.get('UDPipe','out_dir')
        # Get input files directory (output of UnstableParser)
        indir = config.get('UnstableParser','out_dir')
        outdir = config.get('UnstableParser','post_proc_out_dir')
        files = glob.glob(home+'/'+indir+'/*')
        # Post-process each file
        logging.info('Post-processing input files:')
        for infile in files:
            logging.info('  '+infile)
            originalfile = home + '/' + origdir + '/' + infile.split('/')[-1]
            postproc.restore(originalfile, infile, outdir)


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(filename='pipeline.log',level=logging.DEBUG)
    logging.info('Started at: '+str(datetime.now()))
    # Get command line arguments
    configfile = sys.argv[1]
    # Get configuration settings
    configmap = get_config(configfile)
    # Pre-process files with Udpipe
    udpipe(configmap)
    # Dependency parse with the UnstableParser
    unstable_parser(configmap)
    # Post-process UnstableParser output
    post_process_parsed_output(configmap)
    # Exit
    logging.info('Finished at: '+str(datetime.now())+'\n\n')
