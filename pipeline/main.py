#!/usr/bin/env python
# -*- coding: utf-8 -*-

# HELPFUL starter code
# https://github.com/ufal/udpipe/blob/master/bindings/python/examples/run_udpipe.py
# https://github.com/ufal/udpipe/blob/master/bindings/python/examples/udpipe_model.py

# Standard
import sys
import logging
import ConfigParser
from datetime import datetime
from multiprocessing import Process


# Custom
import preprocessing as pre
import parsing
import ner
import nel
import binary_relation


# Extract config json from file
def get_config(configfile):
    cfg = ConfigParser.ConfigParser()
    cfg.read(configfile)
    return cfg


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(filename='pipeline.log',level=logging.DEBUG)
    logging.info('Started at: '+str(datetime.now()))
    # Get command line arguments
    configfile = sys.argv[1]
    # Get configuration settings
    configmap = get_config(configfile)
    # Sentence segmentation
    preprocessor = pre.Preprocessor(configmap)
    preprocessor.split_sentences()
    # Pre-process files with UDPipe
    preprocessor.udpipe()
    # Simultaneously parse and perform NER
    parser = parsing.Parser(configmap)
    parse_proc = Process(target=parser.parse)
#    parse_proc.start()
    ne_rec = ner.Ner(configmap)
    ner_proc = Process(target=ne_rec.NER)
#    ner_proc.start()
    # Named Entity Linking
#    n_link = nel.Nel(configmap)
#    n_link.NEL()
    # Extract binary relations
#    bin_rel = binary_relation.BinaryRelation(configmap)
#    bin_rel.extract_binary_relations()
    # Exit
    logging.info('Finished at: '+str(datetime.now())+'\n\n')
