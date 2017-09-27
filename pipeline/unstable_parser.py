#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import re
import os
import sys
import codecs
from argparse import ArgumentParser

from parser import Configurable
from parser import Network

class UnstableParser:
    def __init__(self, parserpath, savedir):
        self.savedir = savedir
        self.parserpath = parserpath
        self.kwargs = {}
        configfilepath = self.parserpath + '/' + self.savedir + '/config.cfg'
        self.kwargs['config_file'] = configfilepath
        self.kwargs['default'] = {'save_dir': self.parserpath + '/' + self.savedir}
        self.kwargs['is_evaluation'] = True
        self.network = Network(**self.kwargs)


#    def parse(self, outputdir, outputfile, files):
    def parse(self, outputdir, files):
#        if len(files) > 1 and outputfile is not None:
#            raise ValueError('Cannot provide a value for --output_file when parsing multiple files')
        self.network.parse(files, output_dir=outputdir)
#        self.network.parse(files, output_file=outputfile, output_dir=outputdir)
