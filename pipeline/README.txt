BINARY RELATION EXTRACTION PIPELINE FOR GERMAN

This repository contains a pipeline for the extraction of binary relations from German text. It takes as input a JSON formatted corpus file (see section "INPUT DATA FORMAT") and produces two output files (binary_realtions.json and types.txt). The binary_relations.json file contains those relations that were automatically extracted from the input corpus and types.txt contains a list of FIGER types for those entities participating in the binary relations. These output files may be used independently or as the interface to the language-independent section of Javad Hosseini's pipeline, to construct entailment graphs. Both output files are described in the section "OUTPUT FORMAT".

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

The installation/configuration of the external components (UDPipe, UnstableParser, Stanford NER, AGDISTIS) is described in the "REQUIRMENTS" section below.

AGDISITS returns DBpedia urls for those entities that it is able to link. These are mapped to FIGER types (via Freebase) so that both the English and German pipelines use the same type system. This is necessary to align English and German relations and entailment graphs for downstream multilingual tasks such as question answering. The DBpedia to FIGER mapping file is provided as a component of the pipeline, and is described in the "REQUIREMENTS" sectionb below.


REQUIREMENTS

Python 2.7 with the following modules (tested-version):
    backports.lzma==0.0.8
    matplotlib==2.0.2
    nltk==3.2.5
    numpy==1.13.1
    python-dateutil==2.6.1
    requests==2.18.4
    scipy==0.19.1
    simplejson==3.11.1
    sner==0.2.3
    subprocess32==3.2.7
    tensorflow==1.3.0
    ufal.udpipe==1.1.0.1
To install the required modules run the command: pip install -r python-requirements.txt

UnstableParser: https://github.com/tdozat/UnstableParser
Train a German parser model using the Universal Dependencies version 2.0 treebank from the CoNLL 2017 shared task: http://universaldependencies.org/conll17/

AGDISTIS: https://github.com/dice-group/AGDISTIS
Install and configure AGDISTIS to use the German index:
* > git clone https://github.com/AKSW/AGDISTIS.git
* > cd AGDISTIS
* > wget http://hobbitdata.informatik.uni-leipzig.de/agdistis/dbpedia_index_2016-04/de/indexdbpedia_de_2016.zip
* Unzip the index file
* Ensure that the nodeType, edgeType, baseURI, and endpoint properties in the AGDISTIS/src/main/resources/config/agdistis.properties file are set to point to http://de.dbpedia.org, that the index points the german index directory, and that commonEntities is set to true
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

DBPedia-to-FIGER types mapping file: <<<Complete this section>>>
Download the following file from the DBPedia dumps (to keep this in line with the AGDISIS index we recommend using the 2016-04 version:
freebase_links_de.ttl.gz
Ensure that you have a copy of the following files: <<<Ask Javad who to attribute this to>>>
data/entity2type_names.txt.gz
data/types.map.gz
Run command: python scripts/DBPedia_to_FIGER.py (constructs the types.map.gz file referenced in config.ini)


INSTRUCTIONS

1) Ensure that the required python modules have been installed, and that the dependecies (a trained UnstableParser model, AGDISTIS, NER model, UDPipe model, DBPedia-to-figer map) are available
2) Start the AGDISTIS and NER servers
3) Clone the german pipeline repository using the command: git clone https://<username>@bitbucket.org/lianeg/question-answering.git
4) Set up the directory structure, run command: sh scripts/setup_dir.sh
5) Amend config.ini as necessary
6) Load JSON formatted data into 00-json-input. This data should take the format described in the "INPUT DATA FORMAT" section below
7) Start the pipeline, run command: python main.py config.ini
8) Check for output in 10-binary-relations


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

The pipeline outputs two files:
* binary_relations.json: JSON format file, contains details of the binary relations extracted from raw text, with one JSON object per line of text (i.e. sentence). 
* types.txt: text file, contains a list of FIGER types present for the entities in binary_relations.json. This file is needed for the construction of entailment graphs using the pipeline developed in [0].

Each JSON object in the binary_relations.json file (representing the relations found in the line of text) has the following format:
* s: line of text (e.g. sentence)
* date: date and time of the article
* articleId: unique identifier of the article (matches articleId in input data file)
* lineId: line number within article (numbering starts at zero)
* rels: list of dictionaries, each representing a relation (r) extracted from the sentence. The format of the relations is a string separated with the symbol '::' and the following elements:
  	* (optional) negation marker of the format: "NEG__"
  	* predicate (of the format: "(predicate.1, predicate.2)")
	* the canonical form of entity 1 (e.g. "Donald J Trump" and "Donald Trump" are both represented as "Donald_Trump")
	* the canonical form of entity 2
	* the FIGER type of entity 1 prepended with a # (e.g. "#person") 
	* the FIGER type of entity 2 prepended with a #
	* an indicator of whether each entity is a named entity (E) or a common/general entity (G)
	* ??? <<<Ask Javad>>>
	* token offset of the predicate (token numbers start at 'one')



REFERENCES

[0] <<<Add citation to Javad's TACL paper upon acceptance>>>

[1] Zhang, C. and Weld, D. S. (2013). Harvesting parallel news streams to generate paraphrases of event relations. In Proceedings of the Conference on Empirical Methods in Natural Language Processing (EMNLP).
