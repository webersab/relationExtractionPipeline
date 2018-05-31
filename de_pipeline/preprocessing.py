#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Standard
import sys
import codecs
import logging
import json
import nltk.data
from datetime import datetime

# Custom
import udpipe_model as udp


class Preprocessor():

    """
    Perform preprocessing:
        * segment sentences
        * word tokenise sentences
        * process with UDPipe - produces CoNLL format required by the UnstableParser
    Input: raw text
    Output: sentence segmented, word tokenised, CoNLL format text
    """
    
    def __init__(self, config):
        self.config = config
        # Get home directory
        self.home = self.config.get('General','home')
    
    
    def batch_and_segment(self):
        """
        Read the JSON format corpus files, batch articles according to batch_size
        specified in config and output (per batch):
            * a file containing the lines from all articles in the bacth
            * a mapping file that lists the article ID corresponding to each line
        """
        filenames = []
        indir = self.config.get('Input','json_dir')
        infile = self.config.get('Input', 'json_file')
        outdir = self.config.get('Preprocessor','out_dir')
        batchsize = self.config.getint('General', 'batch_size')
        outfilepath = self.home+'/'+outdir
        batchcounter = 0
        batchtextlist = []
        batchmaplist = []
        with open(self.home+'/'+indir+'/'+infile, 'r') as ifile:
            for line in ifile:
                batchcounter += 1
                # Extract JSON object
                data = json.loads(line)
                articleid = data['articleId']
                textlist = data['text'].split('\n')
                # Segment text
                segtextlist = self.split_sentences(textlist)
                # Add text and article IDs to lists (to be written in batches)
                batchtextlist += segtextlist
                articlelinecount = len(segtextlist)
                batchmaplist += [articleid]*articlelinecount
                # Write batches
                if batchcounter == batchsize:
                    fname = self.write_batch_files(outfilepath, batchsize, batchtextlist, batchmaplist)
                    batchcounter = 0
                    batchtextlist = []
                    batchmaplist = []
                    filenames.append(fname)
        # Write final batch (remainder of articles)
        if batchtextlist != []:
            fname = self.write_batch_files(outfilepath, batchsize, batchtextlist, batchmaplist)
            filenames.append(fname)
        return filenames


    def write_batch_files(self, outpath, batchsize, batchtextlist, batchmaplist):
        """
        Write the batched files: article text and article line mapping file
        Return the name of the batched article text file (will be added to a list for later use)
        """
        batchtextfilename = 'batch_size'+str(batchsize)+'_'+str(batchmaplist[0])+'_'+str(batchmaplist[-1])
        batchmapfilename = batchtextfilename+'.lines'
        # Write batch text file
        with codecs.open(outpath+'/'+batchtextfilename, 'w', 'utf-8') as ofile:
            ofile.write('\n'.join(batchtextlist)+'\n')
        # Write batch mapping file
        with open(outpath+'/'+batchmapfilename, 'w') as ofile:
            ofile.write('\n'.join(batchmaplist)+'\n')
        return batchtextfilename

        
    def split_sentences(self, textlist):
        """
        Split sentences using NLTKs PunktTokenizer
        Use segmentation model specifed in config.ini as "seg_model"
        """
        segs = []
        model = self.config.get('Preprocessor','seg_model')
        splitter = nltk.data.load(model)
        for text in textlist:
            if text != '':
                segs += splitter.tokenize(text)
        return segs
                    
            
    def udpipe(self, files):
        """
        Preprocess with UDPipe to get CoNLL format files
        """
        # Get UDPipe configurations
        indir = self.config.get('Preprocessor','out_dir')
        outformat = self.config.get('UDPipe','out_format')
        outdir = self.config.get('UDPipe','out_dir')
        modelfile = self.config.get('UDPipe','model')
        # Load the model
        logging.info('Loading model: ')  
        try:
            model = udp.UDPipeModel(modelfile)
        except Exception:
            message = "ERROR: Cannot load model from file '%s'\n" % modelfile
            logging.error(message+'  Exited at: '+str(datetime.now())+'\n\n')
            sys.stderr.write(message)
            sys.exit(1)
        logging.info('...complete')
        # Process input files
        logging.info('Processing input files:')
        for f in files:
            infile = self.home + '/' + indir + '/' + f
            logging.info('  '+infile)
            # Read text
            with open(infile) as i:
                text = ''.join(i.readlines())
            # Tokenise, tag, and parse
            sentences = model.tokenize(text)
            for s in sentences:
                model.tag(s)
                model.parse(s)
            # Output to file
            conllu = model.write(sentences, outformat)
            outfile = self.home+'/'+outdir+'/'+f
            with codecs.open(outfile, 'w', 'utf-8') as o:
                o.write(conllu)
