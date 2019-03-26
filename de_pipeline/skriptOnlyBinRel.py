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
import binary_relation_withLight
import simpleTyping
import copy_reg
import types

def get_config(configfile):
    """
    Extract config json from file 
    """
    cfg = ConfigParser.ConfigParser()
    cfg.read(configfile)
    return cfg


if __name__ == "__main__":
    """
    Calls each of the pipeline steps in sequence, or a partial set of
    steps if this is specified in the config file
    """
    print("HUPHUP")
    # Set up logging
    logging.basicConfig(filename='pipeline.log',level=logging.DEBUG)
    logging.info('Started at: '+str(datetime.now()))
    # Get command line arguments
    configfile = sys.argv[1]
    # Get configuration settings
    #cfg = ConfigParser.ConfigParser()
    configmap = get_config(configfile)
    file = sys.argv[2]
    bin_rel = binary_relation_withLight.BinaryRelationWithLight(configmap)
    bin_rel.process(file)
    