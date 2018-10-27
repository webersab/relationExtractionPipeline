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


def get_pipeline_steps(config):
    """
    Determine whether the full pipeline / a section of it is to be run
    Return a list of parallel steps to run, and boolean variables
    denoting whether the serial steps (batching, relation extraction)
    should be run.
    """
    steps = []
    partial_execution = config.getboolean('General','partial_execution')
    if partial_execution:
        start_step = config.getint('General','start_step')
        end_step = config.getint('General','end_step')
    else:
        start_step = 1
        end_step = 6
    # Run batching and relation extraction steps?
    batching = True if start_step == 1 else False
    rel_extraction = True if end_step == 6 else False
    # Parallel pipeline steps, removed parsing.UnstParser(configmap) from list
    parallel_step_list = [pre.Preprocessor(configmap), ner.Ner(configmap), nel.Nel(configmap)]
    parallel_steps = parallel_step_list[max(0,start_step-2):end_step-1]
    return parallel_steps, batching, rel_extraction


if __name__ == "__main__":
    """
    Calls each of the pipeline steps in sequence, or a partial set of
    steps if this is specified in the config file
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
    # Get pipeline steps for full / partial execution as specified in config
    steps = get_pipeline_steps(configmap)
    parallel_steps = steps[0]
    batching = steps[1]
    rel_extraction = steps[2]
    # Determine number of cores to use (based on config setting and availability)
    cores = compute_cores(configmap)
    # Batching and sentence segmentation
    homedir = configmap.get('General','home')
    batchgroupsfile = homedir + '/' + configmap.get('General','batch_groups_file') 
    logging.info('started batching: '+str(datetime.now()))
    if batching:
        preprocessor = pre.Preprocessor(configmap)
        preprocessor.batch_and_segment()
        # Split batches into groups according to number of cores available for paralellisation
        batchnamesfile = homedir + '/' + configmap.get('General','batches_file')
        batch_groups_list = hf.group_batches_for_parallel_processing(batchnamesfile, batchgroupsfile, cores)
    else:
        # Read batch groups from file
        batch_groups_list = hf.read_group_batches(batchgroupsfile)
    # Implement pipeline steps for which parallelisation makes sense
    for step in parallel_steps:
        # Set up a pool of workers
        pool = mp.Pool(processes=cores)
        process_batch_group_with_instance=partial(process_batch_group, instance_to_create=step)
        pool.map(process_batch_group_with_instance, batch_groups_list)
        pool.close()
        pool.join()
    # Extract binary relations in series (I/O bound, will not benefit from parallelisation)
    if rel_extraction:
        batch_list = list(chain(*batch_groups_list))
        bin_rel = binary_relation.BinaryRelation(configmap)
        bin_rel.process(batch_list)
    # Exit
    logging.info('Finished at: '+str(datetime.now())+'\n\n')
