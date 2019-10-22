#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Standard
import io
import sys
import codecs
import csv
import ConfigParser
import logging
import json
from itertools import chain
from itertools import product
from collections import OrderedDict
import pprint
import pickle
import ConfigParser
from datetime import datetime
from pygermanet.germanet import load_germanet
import copy_reg
import types

# Custom
import helper_functions as hf


class BinaryRelationWithLight():
    
    def _pickle_method(method):
        func_name = method.im_func.__name__
        obj = method.im_self
        cls = method.im_class
        return _unpickle_method, (func_name, obj, cls)
        
    def _unpickle_method(func_name, obj, cls):
        for cls in cls.mro():
            try:
                func = cls.__dict__[func_name]
            except KeyError:
                pass
            else:
                break
            return func.__get__(obj, cls)
    

    #copy_reg.pickle(types.MethodType, _pickle_method, _unpickle_method)

    """
    Perform binary relation extraction
    Input: dependency parse, common and named entities, entity linking information
    Output: binary relations in text and JSON format, list of types (text file)
    """
    
    def __init__(self, config):
        self.config = config
        self.home = self.config.get('General', 'home')
        with open(self.home+"/verbMap.dat", "rb") as f:
        #with open("/group/project/s1782911/verbMap.dat", "rb") as f:
            verbMap=pickle.load(f)
        self.verbMap=verbMap
        self.gn = load_germanet()

        
    def process(self, files):
        """
        Main method
        Extract binary relations by combining output of the dependency parser and entity linker
        """
        dicttypes = {}
        print('process: Extract binary relations, Im here')
        #print("files ",f)
        #common_entities = self.config.get('NEL','common_entities')
        entfilepath = self.config.get('SimpleType', 'out_dir')
        dpindir = self.config.get('UnstableParser','post_proc_out_dir')
        # Construct output file names:
        outdir = self.config.get('Output','out_dir')
        humanoutfile = self.config.get('Output','human_readable_file')
        humanoutfilename = self.home + '/' + outdir + '/' + humanoutfile
        print(humanoutfilename)
        jsonoutfile = self.config.get('Output', 'json_file')
        jsonoutfilename = self.home + '/' + outdir + '/' + jsonoutfile
        # Create empty output files (to which data will be appended):
        hf.create_files([humanoutfilename,jsonoutfilename], 'utf8')
        for f in files:
            df = self.home + '/' + dpindir + '/' + f
            #df="/group/project/s1782911/batch_size70_17933456_17933538Parse"
            # Read dependency parse
            dtree = hf.dependency_parse_to_graph(df)
            # Read entities
            filenamestem = df.split('/')[-1]#.split('.')[0]
            ef = self.home+'/'+entfilepath+'/'+filenamestem#+'.json'
            #ef="/group/project/s1782911/batch_size70_17933456_17933538Entities"
            entities = hf.read_json(ef)
            # Extract binary relations
            res = self.extract(dtree, entities, 1)
            relations = res[0]
            jsonlist = res[1]
            dicttypes = self.update_dict_types(dicttypes, res[2])
            # Write to human readable file
            self.write_to_human_readable_file(relations, humanoutfilename)
            # Write to json format file
            self.output_to_json(jsonlist, jsonoutfilename)
        # Write type list to file
        self.output_type_list(dicttypes)


    def output_type_list(self, d):
        """
        Write list of types to file
        types file is passed to Javad Hosseini's pipeline for entailment graph generation 
        """
        outdir = self.config.get('Output', 'out_dir')
        filename = self.config.get('Output','types_list')
        listtypes = d.keys()
        with open(self.home + '/' + outdir + '/' + filename, 'w') as f:
            for t in listtypes:
                f.write(t + '\n')

    def update_dict_types(self, d, types):
        """
        Maintain a dictionary of types 
        """
        for t in types:
            if not t in d:
                d[t] = 1
        return d
        

    def output_to_json(self, l, outfilename):
        """
        Output sentence relations to JSON
        For the JSON format binary relations output file
        """
        json_str = '\n'.join([json.dumps(d, ensure_ascii=False) for d in l])
        with codecs.open(outfilename, 'a', 'utf8') as f:
            f.write(json_str + '\n')


    def format_json_relations(self, rels):
        """
        Format relations for JSON file
        JSON file is passed to Javad Hosseini's pipeline for entailment graph generation
        """
        listr = []
        listt = []
        for r in rels:
            ent1type = 'E' if r[0]['entityType'] == 'ner' else 'G'
            ent2type = 'E' if r[1]['entityType'] == 'ner' else 'G'
            if 'notInWiki' in r[0]['disambiguatedURL']:
                ent1string = r[0]['namedEntity'].replace(' ', '_')
            else:
                ent1string = r[0]['disambiguatedURL'].split('/')[-1]
            if 'notInWiki' in r[1]['disambiguatedURL']:
                ent2string = r[1]['namedEntity'].replace(' ', '_')
            else:
                ent2string = r[1]['disambiguatedURL'].split('/')[-1]
            #ent1figer = '#thing' if r[0]['FIGERType'] == 'none' else '#'+r[0]['FIGERType'].split('/')[1]
            ent1figer = r[0]['FIGERType']
            #ent2figer = '#thing' if r[1]['FIGERType'] == 'none' else '#'+r[1]['FIGERType'].split('/')[1]
            ent2figer = r[1]['FIGERType']
            neg = 'NEG__' if r[3] else ''
            predicate = r[2].split('.')[0] + '.1,' + r[2] + '.2'
            s = u'({}({})::{}::{}::{}::{}::{}{}::{}::{})'.format(neg, predicate, ent1string, ent2string,
                                                          ent1figer, ent2figer, ent1type, ent2type, '0', str(r[5]))
            listr.append({'r': s})
            listt.append(ent1figer)
            listt.append(ent2figer)
        return (listr, listt)
            
            
    def extract(self, dt, ent, f):
        """
        Perform the extraction 
        """
        rels = {}
        listsentrels = []
        listtypes = []
        sentlist = ent.keys()
        sentlist.sort()
        for sent in sentlist:
            dictsentrels = OrderedDict()
            dpsenttree = dt[int(sent)]
            sentstring = self.get_sentence(dpsenttree)
            entities = ent[sent]
            entities = self.fill_entities(entities)
            # Get relations
            r = self.get_relations(dpsenttree, entities)
            # JSON format information
            res = self.format_json_relations(r)
            dictsentrels['s'] = sentstring
            dictsentrels['date'] = 'Jan 1, 1980 12:00:00 AM'
            dictsentrels['articleId'] = f
            dictsentrels['lineId'] = str(sent)
            dictsentrels['rels'] = res[0]
            listtypes += res[1]
            listsentrels.append(dictsentrels)
            rels[sent] = {'sentence': sentstring, 'relations': r}
        return (rels, listsentrels, listtypes)
    
    def fill_entities(self,entities):
        entitiesMap={}
        counter=0
        for k, v in entities.iteritems():
            starttok=k 
            namedEntity=v[0]
            FIGERType=v[1]
            entityType=self.get_entity_type(FIGERType)
            disambiguatedURL=namedEntity
            internalMap={"starttok":starttok,
                         "namedEntity":namedEntity,
                         "FIGERType":FIGERType,
                         "entityType":entityType,
                         "disambiguatedURL":disambiguatedURL}
            entitiesMap[counter]=internalMap
            counter+=1
        return entitiesMap
    
    def get_entity_type(self,typ):
        if typ == 'NOUN':
            return 'com'
        else:
            return 'ner'

    def get_sentence(self, dt):
        """
        Extract the sentence text from the dependency tree
        """
        t = []
        for node_index in dt.nodes:
            word = dt.nodes[node_index]['word']
            if word:
                t.append(word)
        s = ' '.join(t)
        return s


    def get_negation(self, dt, i, neg):
        """
        Check to see if the predicate is negated
        Look for the POS-tag "PTKNEG" and dependency "advmod"
        """
        if 'advmod' in dt.nodes[i]['deps']:
            # Check for negations at sub-level
            l = dt.nodes[i]['deps']['advmod']
            for n in l:
                if dt.nodes[n]['tag'] == 'PTKNEG':
                    neg = True
            for n in l:
                neg = self.get_negation(dt, n, neg)
        return neg


    def get_modifiers_to_verb(self, dt, i, mods):
        """
        Get open clausal components of the verb (i.e. the predicate)
        Look for the "xcomp" dependency
        """
        if 'xcomp' in dt.nodes[i]['deps']:
            l = dt.nodes[i]['deps']['xcomp']
            for n in l:
                #if dt.nodes[n]['tag'] != 'PTKNEG':
                if dt.nodes[n]['tag'] == 'VVINF':
                    mods.append(n)
                    mods = self.get_modifiers_to_verb(dt, n, mods)
        return mods
    
    def typeEntity(self,entity,gn):  
        lemmatized= gn.lemmatise(entity)[0]+'.n.1'
        try:
            synset=gn.synset(lemmatized).hypernym_paths
        except:
            if entity in ["ich","du","er","sie","Sie","es", "wir", "ihr","Ihr","Sie|sie"]:
                return "PERSON"
            else:
                return "MISC"

        if "Mensch" in str(synset):
            return "PERSON"
        elif ("Ereignis"in str(synset)) or ("Geschehnis"in str(synset)) or ("Vorfall" in str(synset)):
            return "EVENT"
        elif ("Organisation"in str(synset)) or ("Gruppe"in str(synset)) or ("Institution" in str(synset)):
            return "ORGANIZATION"
        elif ("Gegend"in str(synset)) or ("Ortschaft"in str(synset)) or ("Siedlung"in str(synset)) or ("Stelle" in str(synset)):
            return "LOCATION"
        else:
            return "MISC"
    
    def get_relations(self, dt, ent):
        """
        Identify the binary relations
        """
        rels = []
        ent_list = ent.keys()
        # For every pair of entities:
        for pair in product(ent_list, repeat=2):
            ent1 = ent[pair[0]]
            ent2 = ent[pair[1]]
            if ent1['entityType'] == 'com' and ent2['entityType'] == 'com':
                valid_combination = False
            else:
                #GermaNet typing goes here. Figer type gets substituted with Germanet type.
                if ent1['entityType'] == 'com':
                    newType=self.typeEntity(ent1["namedEntity"], self.gn)
                    ent1["FIGERType"]=newType
                elif ent2['entityType'] == 'com':
                    newType=self.typeEntity(ent2["namedEntity"], self.gn)
                    ent2["FIGERType"]=newType
                valid_combination = True
            if pair[0] != pair[1] and valid_combination:
                #("ent1, ent2 before get predicate: ",ent1,ent2)
                pred = self.get_predicate(dt, ent1, ent2)
                pred_string = pred[0]
                pred_index = pred[1]
                negation = self.get_negation(dt, pred_index, False)
                nounNegated=self.get_noun_negation(dt,ent2)
                negation = negation or nounNegated
                passive = pred[2]
                if passive: # Swap entities
                    ent1 = ent[pair[1]]
                    ent2 = ent[pair[0]]
                string = self.format_relation_string(ent1,ent2,pred_string,negation,passive)
                if pred_string != '':
                    rels.append((ent1,ent2,pred_string,negation,string,pred_index))
        return rels

    def get_noun_negation(self,dt,ent2):
        ent2deps = dt.nodes[int(ent2['starttok'])]['deps'].keys()
        if 'advmod' in ent2deps:
            advmods=dt.nodes[int(ent2['starttok'])]['deps']['advmod']
            for m in advmods:
                if dt.nodes[m]['tag']=='PIAT':
                    return True
        return False
    
    def checkOtherWordsInNamedEntity1(self,ent,dt):
        if len(ent['namedEntity'].split())>1:
            for i in range(len(ent['namedEntity'].split())):
                if dt.nodes[int(ent['starttok'])+i]['rel'] in ['nsubj', 'nsubj:pass','dep']:
                    ent['starttok']= int(ent['starttok'])+i
                    return dt.nodes[int(ent['starttok'])]['rel'], ent
        return ""
    
    def checkOtherWordsInNamedEntity2(self,ent,dt):
        if len(ent['namedEntity'].split())>1:
            for i in range(len(ent['namedEntity'].split())):
                if dt.nodes[int(ent['starttok'])+i]['rel'] in ['obj', 'obl','dep']:
                    ent['starttok']= int(ent['starttok'])+i
                    return dt.nodes[int(ent['starttok'])]['rel'], ent
        return ""

    def get_predicate(self, dt, ent1, ent2):
        """
        Get the predicate that links the two entities
        """
        pred_string = ''
        pred_index = -1
        passive = False
        new1=""
        new2=""
        ent1rel = dt.nodes[int(ent1['starttok'])]['rel']
        if ent1rel not in ['nsubj', 'nsubj:pass','dep']:
            new1=self.checkOtherWordsInNamedEntity1(ent1,dt)
        if new1 != "":
            ent1rel, ent1=new1
        ent2rel = dt.nodes[int(ent2['starttok'])]['rel']
        if ent2rel not in ['obj', 'obl','dep']:
            new2=self.checkOtherWordsInNamedEntity1(ent2,dt)
        if new2 != "":
            ent2rel, ent2=new2
        #print(ent1['namedEntity'],ent1rel, ent2['namedEntity'], ent2rel)
        if ent1rel in ['nsubj', 'nsubj:pass','dep'] and ent2rel in ['obj', 'obl','dep']:
            if ent1rel == 'nsubj:pass':
                passive = True
            ent1head = dt.nodes[int(ent1['starttok'])]['head']
            ent2head = dt.nodes[int(ent2['starttok'])]['head']
            ent2headhead = dt.nodes.get(ent2head)['head']
            ent2headrel= dt.nodes.get(ent2head)['rel']
            if ent1head == ent2head or (ent2headhead == ent1head and ent2headrel == 'xcomp'):
                pred_string = dt.nodes[ent1head]['lemma']
                #print("pred str is head ",pred_string)
                pred_index = ent1head
                # Check if predicate is a particle verb
                if 'compound:prt' in dt.nodes[ent1head]['deps']:
                    for prt in dt.nodes[ent1head]['deps']['compound:prt']:
                        pred_string += '_' + dt.nodes[prt]['lemma']
                #checking for light verb constructions in verb map goes here
                if pred_string in self.verbMap.keys():
                    thesePPandN=[]
                    predDependencies=dt.nodes[pred_index]['deps'].values()
                    predDependencies = [y for x in predDependencies for y in x]
                    for node in dt.nodes:
                        if node in predDependencies and dt.nodes[node]['ctag']=='NOUN' and ('case' in dt.nodes[node]['deps'].keys()):
                            prepLoc=int(dt.nodes[node]['deps']['case'][0])
                            prep=dt.nodes[prepLoc]['lemma']
                            noun=dt.nodes[node]['lemma']
                            PPandN=prep+" "+noun
                            thesePPandN.append(PPandN.encode('utf-8'))
                    #print(thesePPandN)
                    #print(self.verbMap[pred_string])
                    lst = [value for value in thesePPandN if value in self.verbMap[pred_string]] 
                    if len(lst)>0:
                       ppn=lst[0]
                       ppn=ppn.replace(" ","_")
                       pred_string+="_"+ppn.decode('utf-8')
                # Add modifiers to verbs
                mods = self.get_modifiers_to_verb(dt, pred_index, [])
                for mod in mods:
                    pred_string += '.' + dt.nodes[mod]['lemma']
                # Add prepositions
                if 'case' in dt.nodes[ent2['starttok']]['deps']:
                    for prep in dt.nodes[ent2['starttok']]['deps']['case']:
                        pred_string += '.' + dt.nodes[prep]['lemma']
        #this is where I check for object attachment
        elif (ent1rel in ['nsubj', 'nsubj:pass','dep']) and (ent2rel in ['nmod']):
            if pred_string=="":
                pred_string, pred_index = self.checkForHabenPlusObject(dt, ent1, ent2)
            if pred_string=="":
                pred_string, pred_index = self.checkForSeinPlusObject(dt, ent1, ent2)
        return (pred_string, pred_index, passive)
    
    def checkForSeinPlusObject(self, dt, ent1, ent2):
        pred_string=""
        pred_index=dt.nodes[int(ent1['starttok'])]['head']
        if ("cop" in dt.nodes[pred_index]['deps'].keys()) and ("nmod" in dt.nodes[pred_index]['deps'].keys() or "advmod" in dt.nodes[pred_index]['deps'].keys()):
            copulaWordIndex=dt.nodes[pred_index]['deps']['cop']
            if "nmod" in dt.nodes[pred_index]['deps'].keys():
                nmodWordIndex=dt.nodes[pred_index]['deps']['nmod']
            elif "advmod" in dt.nodes[pred_index]['deps'].keys():
                nmodWordIndex=dt.nodes[pred_index]['deps']['advmod']
            if dt.nodes[copulaWordIndex[0]]["lemma"]== "sein":
                for i in nmodWordIndex:
                    if int(i)==int(ent2['starttok']):
                        caseAttachment=self.get_case_attachment(dt, ent2)
                        pred_string=dt.nodes[pred_index]['lemma']+"_sein"+caseAttachment
        return pred_string, pred_index
    
    def get_case_attachment(self,dt,ent2):
        print("in case attach")
        print(dt.nodes[int(ent2['starttok'])]['deps'].keys())
        if "case" in dt.nodes[int(ent2['starttok'])]['deps'].keys():
            for i in dt.nodes[int(ent2['starttok'])]['deps']['case']:
                return dt.nodes[i]["lemma"]
        return""
    
    def checkForHabenPlusObject(self, dt, ent1, ent2):
        pred_string=""
        pred_index=dt.nodes[int(ent1['starttok'])]['head']
        if "obj" in dt.nodes[pred_index]['deps'].keys():
            predDependencies=dt.nodes[pred_index]['deps']['obj']
            for node in dt.nodes:
                if (node in predDependencies) and dt.nodes[node]['ctag']=='NOUN' and ('nmod' in dt.nodes[node]['deps'].keys()):
                    nounDependencies=dt.nodes[node]['deps']['nmod']
                    pred_string = dt.nodes[pred_index]['lemma']
                    ent2Dependencies=dt.nodes[int(ent2['starttok'])]['deps']
                    if (int(ent2['starttok']) in nounDependencies) and pred_string=="haben" and ('case' in ent2Dependencies):
                        pred_string+="_"+dt.nodes[node]['lemma']
        return pred_string, pred_index


    def format_relation_string(self, ent1, ent2, pred, neg, passive):
        """
        Format the relation as a string
        For output in the human-readable binary relations file
        """
        if 'notInWiki' in ent1['disambiguatedURL']:
            ent1string = ent1['namedEntity'].replace(' ', '_')
        else:
            ent1string = ent1['disambiguatedURL'].split('/')[-1]
        if 'notInWiki' in ent2['disambiguatedURL']:
            ent2string = ent2['namedEntity'].replace(' ', '_')
        else:
            ent2string = ent2['disambiguatedURL'].split('/')[-1]
        #ent1figer = '#thing' if ent1['FIGERType'] == 'none' else '#'+ent1['FIGERType'].split('/')[1]
        ent1figer='#'+ent1['FIGERType']
        #ent2figer = '#thing' if ent2['FIGERType'] == 'none' else '#'+ent2['FIGERType'].split('/')[1]
        ent2figer='#'+ent2['FIGERType']
        negation = 'NEG__' if neg else ''
        predicate = pred + '.1,' + pred + '.2'
        s = u'{}({}){}{}::{}::{}|||(passive: {})'.format(negation, predicate, ent1figer, ent2figer,
                                                         ent1string, ent2string, str(passive))
        return s


    def write_to_human_readable_file(self, r, outfilename):
        """
        Write the binary relations to file
        """
        sent_list = sorted(r.keys())
        with codecs.open(outfilename, 'a', 'utf8') as f:
            for sent_no in sent_list:
                s = 'line: ' + r[sent_no]['sentence'] + '\n'
                for rel in r[sent_no]['relations']:
                    s += rel[4] + '\n'
                s += '\n'
                f.write(s)
    
    
if __name__ == "__main__":
    print("HUPHUP")
    print('Started at: '+str(datetime.now()))
    cfg = ConfigParser.ConfigParser()
    cfg.read("config.ini")
    f="batch_size70_52042173_52042214"

    b=BinaryRelationWithLight(cfg)
    b.process([f])
