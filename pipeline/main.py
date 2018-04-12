#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
German binary relation extraction pipeline

This pipeline performs the following steps:
    * Pre-processing (sentence segmentation, word tokenisation)
    * Dependency parsing
    * Named entity recognition
    * Named entity linking
    * Binary relation extraction
and outputs three files:
    * Binary relations text file (human readable)
    * Binary relations JSON file (for processing by Javad Hosseini's entailment graph construction pipeline)
    * Types text file (for processing by Javad Hosseini's entailment graph construction pipeline)

To run the pipeline, use the command: python main.py config.ini

Liane Guillou, The University of Edinburgh, April 2018
"""

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
import ner
import nel
import binary_relation


def get_config(configfile):
    """
    Extract config json from file 
    """
    cfg = ConfigParser.ConfigParser()
    cfg.read(configfile)
    return cfg


def read_json_input(config):
    """
    Read the JSON format corpus file and write the text of each article
    to a separate text file. This is hacky and requires a longer-term 
    solution.
    """
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


if __name__ == "__main__":
    """
    Calls each of the pipeline steps in sequence
    """
    # Set up logging
    logging.basicConfig(filename='pipeline.log',level=logging.DEBUG)
    logging.info('Started at: '+str(datetime.now()))
    # Get command line arguments
    configfile = sys.argv[1]
    # Get configuration settings
    configmap = get_config(configfile)
    # The untable parser uses the namespace "parser" which is the same
    # name as a standard python library. To get around this problem
    # add the unstable parser path to sys.path before importing the
    # "parsing.py" module
    unstableparserpath = configmap.get('UnstableParser','path')
    sys.path.insert(0,unstableparserpath)
    import parsing
    # Get list of files for processing
    file_list = read_json_input(configmap)
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
