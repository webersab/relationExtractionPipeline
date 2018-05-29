from __future__ import absolute_import 
from __future__ import division 
from __future__ import print_function 
 
import os 
import sys 
import codecs 


# Restore multi-token spans e.g. add back in "im" ("in dem") for German
def restore(original_file, input_file, output_dir):
    lines = []

    # Read the file parsed by the UnstableParser
    with codecs.open(input_file, encoding='utf-8') as f: 
        for line in f: 
            lines.append(line) 
 
    # Read the original file (output by UDPipe)
    with codecs.open(original_file, encoding='utf-8') as f:
        infilename = input_file.split('/')[-1]
        output_file = output_dir+'/'+infilename
        # Write to the output file (restored parser output)
        with codecs.open(output_file, 'w', encoding='utf-8') as fout: 
            i = 0 
            for line in f: 
                line = line.strip() 
                if len(line) == 0: 
                    fout.write(lines[i]) 
                    i += 1 
                    continue 
                if line[0] == '#': 
                    continue 
                line = line.split('\t') 
                if '.' in line[0]: 
                    continue 
                if '-' in line[0]: 
                    fout.write('%s\n' % ('\t'.join(line))) 
                    continue
                fout.write(lines[i])
                i += 1
