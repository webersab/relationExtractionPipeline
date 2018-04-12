#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This code is adapted from "main.py" in the UnstableParser git repository:
https://github.com/tdozat/Parser-v2/

Only the code that is required to run the parser (parse using a pre-trained model)
has been retained.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Standard
import re
import os
import sys
import codecs
from argparse import ArgumentParser

# Custom
from parser import Configurable
from parser import Network


class UnstableParser:

    """
    Perform parsing using the UnstableParser (universal dependency parser
    """
    
    def __init__(self, parserpath, savedir):
        self.savedir = savedir
        self.parserpath = parserpath
        self.kwargs = {}
        # Parser configuration file
        configfilepath = self.parserpath + '/' + self.savedir + '/config.cfg'
        self.kwargs['config_file'] = configfilepath
        # Pre-trained parser model
        self.kwargs['default'] = {'save_dir': self.parserpath + '/' + self.savedir}
        self.kwargs['is_evaluation'] = True
        self.network = Network(**self.kwargs)


    def parse(self, outputdir, files):
        """
        Parse the files using a pre-trained UnstableParser model
        """
        self.network.parse(files, output_dir=outputdir)
