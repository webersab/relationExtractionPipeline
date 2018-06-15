#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Standard
import sys
import codecs
import ConfigParser
import logging

# Custom
import unstable_parser as up
import unstable_parser_post_proc as postproc


class UnstParser():

    """
    Perform dependency parsing using the UnstableParser
    Input: CoNLL format files (containing segmented, word tokenised sentences)
    Output: CoNLL format files with dependencies and POS-tags
    """
    
    def __init__(self, config):
        self.config = config
        # Get home directory
        self.home = self.config.get('General','home')

        
    def process(self, files):
        """
        Main method
        """
        print('process: parse')
        # Dependency parse with the UnstableParser
        self.unstable_parser(files)
        # Post-process UnstableParser output
        self.post_process_parsed_output(files)


    def unstable_parser(self, files):
        """
        Parse with the UnstableParser
        """
        # Parser path
        parserpath = self.config.get('UnstableParser','path')
        # Get input directory (output of udpipe)
        indir = self.config.get('UDPipe','out_dir')
        # Get UnstableParser configurations
#        parserconfig = self.config.get('UnstableParser','config_file')
        savedir = self.config.get('UnstableParser','save_dir')
        outdir = self.config.get('UnstableParser','out_dir')
        file_list = [self.home+'/'+indir+'/'+f for f in files]
        # Initialise parser
        logging.info('Initialising the UnstableParser:')
        uparser = up.UnstableParser(parserpath, savedir)
        # Parse each file
        outputdir = self.home + '/' + outdir
        logging.info('Parsing input files in: ' + indir)
        uparser.parse(outputdir, file_list)
        

    def post_process_parsed_output(self, files):
        """
        Post-process the UnstableParser output (German only)
        """
        # Get language
        language = self.config.get('General','language')
        # Step is required for German only
        if language == 'de':
            # Get original files directory (output of UDPipe)
            origdir = self.config.get('UDPipe','out_dir')
            # Get input files directory (output of UnstableParser)
            indir = self.config.get('UnstableParser','out_dir')
            outdir = self.config.get('UnstableParser','post_proc_out_dir')
            outdirpath = self.home + '/' + outdir
            # Post-process each file
            logging.info('Post-processing input files:')
            for f in files:
                infile = self.home + '/' + indir + '/' + f
                logging.info('  '+infile)
                originalfile = self.home + '/' + origdir + '/' + infile.split('/')[-1]
                postproc.restore(originalfile, infile, outdirpath)
