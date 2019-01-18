import os
from tempfile import mkstemp
from shutil import move
from os import fdopen, remove
import re

if __name__ == "__main__":
    for filename in os.listdir("/disk/scratch/sweber/german-pipeline/datasets/news-crawl-deduplicated/segmentsOfCrawlbatched_de"):
        print("Processing batch file "+filename)
        #mofidy input and output files in config.ini
        fh, abs_path = mkstemp()
        setJsonfile=False
        with fdopen(fh,'w') as new_file:
            with open('config.ini') as old_file:
                for line in old_file:
                    if "json_file = " in line and not setJsonfile:
                        print("found first place to change")
                        replacement="json_file = "+filename+"\\n"
                        new_file.write(re.sub("json_file = *", replacement , line))
                        print("Wrote: ",re.sub("json_file = *", replacement, line))
                        setJsonfile=True
                    elif "human_readable_file = binary_relations_" in line:
                        print("found second place to change")
                        replacement2="human_readable_file = binary_relations_"+filename+".txt\\n"
                        new_file.write(re.sub("human_readable_file = binary_relations_*",replacement2 , line))
                        print("Wrote: ",re.sub("human_readable_file = binary_relations_*", replacement2, line))
                    else:
                        new_file.write(line)
        remove('config.ini')
        move(abs_path, 'config.ini')
        #run "python main.py config.ini"
        os.system("python main.py config.ini")  
        