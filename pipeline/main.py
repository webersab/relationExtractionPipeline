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
import ner_nel


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
    # Pre-process files with UDPipe
    preprocessor = pre.Preprocessor(configmap)
    preprocessor.udpipe()
    # Simultaneously parse and perform NER
    parser = parsing.Parser(configmap)
    parse_proc = Process(target=parser.parse)
#    parse_proc.start()
    ner = ner_nel.NerNel(configmap)
    ner_proc = Process(target=ner.NER)
    ner_proc.start()
    # Exit
    logging.info('Finished at: '+str(datetime.now())+'\n\n')
