#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Standard
import sys
import codecs
#import glob
import ConfigParser
import logging

# Custom
sys.path.insert(0,'/afs/inf.ed.ac.uk/user/l/lguillou/Tools/UnstableParser')
import unstable_parser as up
import unstable_parser_post_proc as postproc


class Parser():

    def __init__(self, config):
        self.config = config
        # Get home directory
        self.home = self.config.get('General','home')

    def parse(self, files):
        print('process: parse')
        # Dependency parse with the UnstableParser
        self.unstable_parser(files)
        # Post-process UnstableParser output
        self.post_process_parsed_output(files)


    # Parse with the UnstableParser
    def unstable_parser(self, files):
        # Parser path
        parserpath = self.config.get('UnstableParser','path')
#        # Get input directory (output of udpipe)
        indir = self.config.get('UDPipe','out_dir')
        # Get UnstableParser configurations
        parserconfig = self.config.get('UnstableParser','config_file')
        savedir = self.config.get('UnstableParser','save_dir')
        outdir = self.config.get('UnstableParser','out_dir')
#        files = glob.glob(self.home+'/'+indir+'/*')
        file_list = [self.home+'/'+indir+'/'+f for f in files]
#        print file_list
        # Initialise parser
        logging.info('Initialising the UnstableParser:')
        parser = up.UnstableParser(parserpath, savedir)
        # Parse each file
        outputdir = self.home + '/' + outdir
        logging.info('Parsing input files in: ' + indir)
        parser.parse(outputdir, file_list)
        

    # Post-process the UnstableParser output (German only)
    def post_process_parsed_output(self, files):
        # Get language
        language = self.config.get('General','language')
        # Step is required for German only
        if language == 'de':
            # Get original files directory (output of UDPipe)
            origdir = self.config.get('UDPipe','out_dir')
            # Get input files directory (output of UnstableParser)
            indir = self.config.get('UnstableParser','out_dir')
            outdir = self.config.get('UnstableParser','post_proc_out_dir')
#            files = glob.glob(self.home+'/'+indir+'/*')
            # Post-process each file
            logging.info('Post-processing input files:')
            for f in files:
                infile = indir + '/' + f
                logging.info('  '+infile)
                originalfile = self.home + '/' + origdir + '/' + infile.split('/')[-1]
                postproc.restore(originalfile, infile, outdir)
