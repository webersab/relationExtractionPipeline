BINARY RELATION EXTRACTION PIPELINE FOR GERMAN


REQUIREMENTS

Python modules (tested-version):
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
5) Load data into 00-json-input (or use test file [recommended])
5) Start the pipeline, run command: python main.py config.ini
7) Check for output in 10-binary-relations
