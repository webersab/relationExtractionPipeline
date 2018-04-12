#!/usr/bin/env python
# -*- coding: utf-8 -*-

# HELPFUL starter code
# https://github.com/ufal/udpipe/blob/master/bindings/python/examples/run_udpipe.py
# https://github.com/ufal/udpipe/blob/master/bindings/python/examples/udpipe_model.py

# Standard
import sys
import json
import glob
import logging
import ConfigParser
from datetime import datetime
from multiprocessing import Process


# Custom
import preprocessing as pre
#import parsing
import ner
import nel
import binary_relation

# Extract config json from file
def get_config(configfile):
    cfg = ConfigParser.ConfigParser()
    cfg.read(configfile)
    return cfg

def read_json_input(config):
    filenames = []
    home = config.get('General','home')
    indir = config.get('Input','json_dir')
    infile = config.get('Input', 'json_file')
    outdir = config.get('Input', 'raw_input')
    with open(home+'/'+indir+'/'+infile, 'r') as ifile:
        for line in ifile:
            data = json.loads(line)
            outfilename = data['articleId']
            with open(home+'/'+outdir+'/'+outfilename, 'w') as ofile:
                ofile.write(data['text'].encode('utf8'))
            filenames.append(outfilename)
    return filenames

# Get a list of filenames
#def get_file_list(config):
#    l = []
#    home = config.get('General','home')
#    indir = config.get('Input','data')
#    files = glob.glob(home+'/'+indir+'/*')
#    for filepath in files:
#        filename = filepath.split('/')[-1]
#        l.append(filename)
#    return l


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(filename='pipeline.log',level=logging.DEBUG)
    logging.info('Started at: '+str(datetime.now()))
    # Get command line arguments
    configfile = sys.argv[1]
    # Get configuration settings
    configmap = get_config(configfile)
    unstableparserpath = configmap.get('UnstableParser','path')
    sys.path.insert(0,unstableparserpath)
    print sys.path
    import parsing
    # Get list of files for processing
    file_list = read_json_input(configmap)
    #file_list = file_list[0:10]
    #file_list = get_file_list(configmap)
    # Sentence segmentation
    preprocessor = pre.Preprocessor(configmap)
    file_list = preprocessor.split_sentences(file_list)
    # Pre-process files with UDPipe
    preprocessor.udpipe(file_list)
    # Simultaneously parse and perform NER
    uparser = parsing.UnstParser(configmap)
    parse_proc = Process(target=uparser.parse, args=(file_list,))
    parse_proc.start()
    ne_rec = ner.Ner(configmap)
    ner_proc = Process(target=ne_rec.NER, args=(file_list,))
    ner_proc.start()
    # Wait until both processes have completed before continuing
    parse_proc.join()
    ner_proc.join()
    # Named Entity Linking
    n_link = nel.Nel(configmap)
    n_link.NEL(file_list)
    # Extract binary relations
    bin_rel = binary_relation.BinaryRelation(configmap)
    bin_rel.extract_binary_relations(file_list)
    # Exit
    logging.info('Finished at: '+str(datetime.now())+'\n\n')
