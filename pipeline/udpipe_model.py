#!/usr/bin/env python
# -*- encoding: utf-8 -*-

# This file is adapted from a file of the same name which is part of
# UDPipe <http://github.com/ufal/udpipe/>.
#
# Copyright 2016 Institute of Formal and Applied Linguistics, Faculty of
# Mathematics and Physics, Charles University in Prague, Czech Republic.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from ufal.udpipe import Model, InputFormat, OutputFormat, ProcessingError, Sentence

class UDPipeModel:
    def __init__(self, path):
        """Load given model."""
        self.model = Model.load(path)
        if not self.model:
            raise Exception("Cannot load UDPipe model from file '%s'" % path)

    def tokenize(self, text):
        """Tokenize the text and return list of ufal.udpipe.Sentence-s."""
        tokenizer = self.model.newTokenizer(self.model.TOKENIZER_NORMALIZED_SPACES)
        if not tokenizer:
            raise Exception("The model does not have a tokenizer")
        return self._read(text, tokenizer)

#    def read(self, text, in_format):
#        """Load text in the given format (conllu|horizontal|vertical) and return list of ufal.udpipe.Sentence-s."""
#        input_format = InputFormat.newInputFormat(in_format)
#        if not input_format:
#            raise Exception("Cannot create input format '%s'" % in_format)
#        return self._read(text, input_format)

    def _read(self, text, input_format):
        input_format.setText(text)
        error = ProcessingError()
        sentences = []

        sentence = Sentence()
        while input_format.nextSentence(sentence, error):
            sentences.append(sentence)
            sentence = Sentence()
        if error.occurred():
            raise Exception(error.message)
        return sentences

    def tag(self, sentence):
        """Tag the given ufal.udpipe.Sentence (inplace)."""
        self.model.tag(sentence, self.model.DEFAULT)

    def parse(self, sentence):
        """Parse the given ufal.udpipe.Sentence (inplace)."""
        self.model.parse(sentence, self.model.DEFAULT)

    def write(self, sentences, out_format):
        """Write given ufal.udpipe.Sentence-s in the required format (conllu|horizontal|vertical)."""

        output_format = OutputFormat.newOutputFormat(out_format)
        output = ''
        for sentence in sentences:
            output += output_format.writeSentence(sentence)
        output += output_format.finishDocument()

        return output

# Can be used as
#modelfile = "/afs/inf.ed.ac.uk/user/l/lguillou/Tools/udpipe/models/udpipe-ud-2.0-conll17-170315/english-ud-2.0-conll17-170315.udpipe"
#model = UDPipeModel(modelfile)
#sentences = model.tokenize("Hi there.\n How are you?\n")
#for s in sentences:
#    model.tag(s)
#    model.parse(s)
#conllu = model.write(sentences, "conllu")
#print(conllu)
