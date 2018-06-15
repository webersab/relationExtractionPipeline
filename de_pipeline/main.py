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
import glob
import logging
import ConfigParser
import traceback
import multiprocessing as mp
from datetime import datetime
from functools import partial
from itertools import chain

# Custom
import preprocessing as pre
import helper_functions as hf
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


def compute_cores(config):
    """
    Compute number of available cores
    The maximum number of cores is specified in the config file.
    If the server does not have this number of cores available,
    use the number of available cores instead.
    """
    cores = config.getint('General','cores')
    if cores > mp.cpu_count():
        cores = mp.cpu_count()
    return cores


def process_batch_group(batch_name_list, instance_to_create):
    """
    Create an instance of the relevant pipeline step object
    and call its main method (called "process" for each step)
    """
    try:
        proc_inst = instance_to_create
        proc_inst.process(batch_name_list)
    except Exception, ex:
        print traceback.format_exc()
        raise ex


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
    # Batching and sentence segmentation
    preprocessor = pre.Preprocessor(configmap)
    preprocessor.batch_and_segment()
    # Split batches into groups according to number of cores available for paralellisation
    cores = compute_cores(configmap)
    homedir = configmap.get('General','home')
    batchnamesfile = homedir + '/' + configmap.get('General','batches_file')
    batchgroupsfile = homedir + '/' + configmap.get('General','batch_groups_file')
    batch_groups_list = hf.group_batches_for_parallel_processing(batchnamesfile, batchgroupsfile, cores)
    # Implement pipeline steps for which parallelisation makes sense
    pipeline = [pre.Preprocessor(configmap), ner.Ner(configmap), parsing.UnstParser(configmap), nel.Nel(configmap)]
    for step in pipeline:
        # Set up a pool of workers
        pool = mp.Pool(processes=cores)
        process_batch_group_with_instance=partial(process_batch_group, instance_to_create=step)
        pool.map(process_batch_group_with_instance, batch_groups_list)
        pool.close()
        pool.join()
    # Extract binary relations in series (I/O bound, will not benefit from parallelisation)
    batch_list = list(chain(*batch_groups_list))
    bin_rel = binary_relation.BinaryRelation(configmap)
    bin_rel.process(batch_list)
    # Exit
    logging.info('Finished at: '+str(datetime.now())+'\n\n')
