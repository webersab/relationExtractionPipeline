import os
from tempfile import mkstemp
from shutil import move
from os import fdopen, remove

if __name__ == "__main__":
    for filename in os.listdir("/disk/scratch/sweber/german-pipeline/datasets/news-crawl-deduplicated/segmentsOfCrawlbatched_de"):
        #mofidy input and output files in config.ini
        fh, abs_path = mkstemp()
        setJsonfile=False
        with fdopen(fh,'w') as new_file:
            with open('config.ini') as old_file:
                for line in old_file:
                    if line.contains("json_file = ") and not setJsonfile:
                        new_file.write(line.replace("json_file = *", "json_file = "+filename))
                        setJsonfile=True
                    elif line.contains("human_readable_file = binary_relations_"):
                        new_file.write(line.replace("human_readable_file = binary_relations_*", "human_readable_file = binary_relations_"+filename+".txt"))
                    else:
                        new_file.write(line)
        remove(file_path)
        move(abs_path, file_path)
        #run "python main.py config.ini"
        os.system("python main.py config.ini")  
        