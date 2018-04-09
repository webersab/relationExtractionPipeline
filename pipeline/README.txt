BINARY RELATION EXTRACTION PIPELINE FOR GERMAN

This repository contains a pipeline for the extraction of binary relations from German text. It takes as input a JSON formatted corpus file (see section "INPUT DATA FORMAT") and produces two output files (binary_realtions.json and types.txt). The binary_relations.json file contains those relations that were automatically extracted from the input corpus and types.txt contains a list of FIGER types for those entities participating in the binary relations. These output files may be used independently or as the interface to the language-independent section of Javad Hosseini's pipeline, to construct entailment graphs. Both output files are described in the section "OUTPUT FORMAT".

The pipeline relies on the following external components:
* Word tokeniser / CoNLL formatter: UDPipe
* Universal dependency parser: UnstableParser
* Named entity recogniser: Stanford NER
* Named entity linker: AGDISTIS
* DBPedia url to FIGER types mapping file

The installation/configuration of these external components is described in the "REQUIRMENTS" section below.

As of 09/04/2018 the pipeline performs the following steps:
* Extract raw text from JSON format corpus and write each article to a separate file (main.py)
* Sentence segmentation with NLTK (preprocessing.py)
* Word tokenisation / CoNLL format preprocessing with UDPipe (preprocessing.py)
* Parsing with UnstableParser (parsing.py)
* Parser output pre-processing for German compounds using an auxialliary script for the UnstableParser (parasing.py)
* Named entity recognition with Stanford NER + german model (ner.py)
* Extraction of common entities (nouns in the parser output) (helper_functions.py / nel.py)
* Named entity linking with AGDISTIS (nel.py)
* Binary relation extraction (binary_relation.py)


REQUIREMENTS

Python 2.7 with the following modules (tested-version):
    networkx (2.0)
    nltk (3.2.5)
    numpy (1.13.1)
    python-dateutil (2.6.1)
    requests (2.18.4)
    simplejson (3.11.1)
    sner (0.2.3)
    subprocess32 (3.2.7)
    tensorflow (1.3.0)
    ufal.udpipe (1.1.0.1)

UnstableParser: https://github.com/tdozat/UnstableParser
Train a German parser model using the Universal Dependencies version 2.0 treebank from the CoNLL 2017 shared task: http://universaldependencies.org/conll17/

AGDISTIS: https://github.com/dice-group/AGDISTIS
Install and configure AGDISTIS to use the German index:
* > git clone https://github.com/AKSW/AGDISTIS.git
* > cd AGDISTIS
* > wget http://hobbitdata.informatik.uni-leipzig.de/agdistis/dbpedia_index_2016-04/de/indexdbpedia_de_2016.zip
* Unzip the index file
* Ensure that the nodeType, edgeType, baseURI, and endpoint properties in the AGDISTIS/src/main/resources/config/agdistis.properties file are set to point to http://de.dbpedia.org and that the index points the german index directory
* > mvn tomcat:run
* To test that the installation worked, try running the command:
     > curl --data-urlencode "text='<entity>Angela Merkel</entity>'" -d type='agdistis' http://<server_name>:8080/AGDISTIS

Standord NER model for German and NER server:
https://nlp.stanford.edu/software/CRF-NER.html
https://pypi.python.org/pypi/sner/0.2.3
Set up the NER server for German:
* > wget https://nlp.stanford.edu/software/stanford-ner-2018-02-27.zip
* Unzip the file stanford-ner-2018-02-27.zip
* > cd stanford-ner-2018-02-27
* > mkdir german-models-2018-02-27
* > cd german-models-2018-02-27
* > wget http://nlp.stanford.edu/software/stanford-german-corenlp-2018-02-27-models.jar
* > jar xf stanford-german-corenlp-2018-02-27-models.jar
* > cd ..
* > java -Djava.ext.dirs=./lib -cp stanford-ner.jar edu.stanford.nlp.ie.NERServer -port 9199 -loadClassifier german-models-2018-02-27/edu/stanford/nlp/models/ner/german.conll.germeval2014.hgc_175m_600.crf.ser.gz -tokenizerFactory edu.stanford.nlp.process.WhitespaceTokenizer -tokenizerOptions tokenizeNLs=false
* To test that the installation worked, try running the following:
     > python
     > import sner
     > st = sner.Ner(host='<server_name>',port=9199)
     > st.tag('Angela Merkel')

UDPipe model for German: http://ufal.mff.cuni.cz/udpipe
* > wget https://github.com/ufal/udpipe/releases/download/v1.1.0/udpipe-1.1.0-bin.zip
* Unzip udpipe-1.1.0-bin.zip
* > wget https://lindat.mff.cuni.cz/repository/xmlui/bitstream/handle/11234/1-1990/udpipe-ud-2.0-conll17-170315.tar
* > tar -xvf udpipe-ud-2.0-conll17-170315.tar

DBPedia-to-FIGER types mapping file:
Download the following file from the DBPedia dumps (to keep this in line with the AGDISIS index we recommend using the 2016-04 version:
freebase_links_de.ttl.gz
Download the following files:
freebasetypefile = 'entity2type_names.txt.gz'
figertypefile = 'types.map.gz'
Run scripts/DBPedia_to_FIGER.py


INSTRUCTIONS

1) Ensure that the required python modules have been installed, and that the dependecies (a trained UnstableParser model, AGDISTIS, NER model, UDPipe model, DBPedia-to-figer map) are available
2) Start the AGDISTIS and NER servers
3) Set up the directory structure, run command: sh scripts/setup_dir.sh
4) Amend config.ini as necessary
5) Load JSON formatted data into 00-json-input. This data should take the format described in the "INPUT DATA FORMAT" section below
5) Start the pipeline, run command: python main.py config.ini
7) Check for output in 10-binary-relations


INPUT DATA FORMAT

The pipeline expects data in JSON format, with one JSON object per article.

For the extraction of binary relations we have used a collection of German news articles crawled from the web by the Machine Tranlsation group at Edinburgh University, during the period 2008-2017. From this collection we have formatted a corpus following that used in the (English) Newsspike corpus [1]. This is the same format expected as input to the English pipeline developed by Javad Hosseini [0].

The JSON object for each article in the German news corpus contains the following fields:
* date - date and time that the article was crawled
* title - article title
* url - article source
* text - content of the article
* articleId - unique identifier for each article
* autoDetectLanguage - article language as identified by the python langdetect module

As of 09/04/2018 the pipeline requires that *at minimum* the title and articleId fields are available.


OUTPUT FORMAT

<<<Describe the format of binary_relations.json and types.txt>>>


REFERENCES

[0] <<<Add citation to Javad's paper upon acceptance>>>

[1] Zhang, C. and Weld, D. S. (2013). Harvesting parallel news streams to generate paraphrases of event relations. In Proceedings of the Conference on Empirical Methods in Natural Language Processing (EMNLP).
