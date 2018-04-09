# Script to produce a mapping from DBPedia links output by the
# named entity linker (AGDISTIS) to FIGER types (via Freebase)

import gzip
import simplejson as json

# Set paths for output file and freebase external links file (to be downloaded from DBPedia dump)
outputfile = '<path>/dbpedia_figer_map.json.gz'
freebaselinkfile = '<path>/freebase_links_de.ttl.gz'
freebasetypefile = 'data/entity2type_names.txt.gz'
figertypefile = 'data/types.map.gz'

def dbpedia_url_to_freebase_url():
    d_to_f = {}
    flinks = {}
    with gzip.open(freebaselinkfile, 'r') as f:
        for line in f:
            if line[0] != '#':
                elements = line.split(' ')
                dbpedia_url = elements[0].lstrip('<').rstrip('>')
                freebase_url = elements[2].lstrip('<').rstrip('>')
                d_to_f[dbpedia_url] = freebase_url
                flinks[freebase_url] = ''
    return d_to_f, flinks

def freebase_url_to_type(u_to_t):
    ftypes = {}
    with gzip.open(freebasetypefile, 'r') as f:
        for line in f:
            line = line.rstrip('\n')
            elements = line.split('\t')
            mid = elements[0].replace('/','.').lstrip('.')
            freebase_url = 'http://rdf.freebase.com/ns/' + mid
            freebase_types = elements[3].replace('  ',' ').split(' ') 
            if freebase_url in u_to_t:
                u_to_t[freebase_url] = freebase_types
            for t in freebase_types:
                if t not in ftypes:
                    ftypes[t] = ''
    return u_to_t, ftypes

def freebase_type_to_figer_type(f_to_f):
    with gzip.open(figertypefile, 'r') as f:
        for line in f:
            line = line.rstrip('\n')
            elements = line.split('\t')
            if elements[0] in f_to_f:
                f_to_f[elements[0]] = elements[1]
    return f_to_f

def dbpedia_to_figer(dbpedia,freebase,figer):
    m = {}
    for dbplink in dbpedia:
        freebase_type = []
        figer_type = []
        freebase_url = dbpedia[dbplink]
        if freebase_url in freebase:
            freebase_type = freebase[freebase_url]
        for ft in freebase_type:
            if ft in figer and figer[ft] != '':
                figer_type.append(figer[ft])
            else:
                figer_type.append('')
#        m[dbplink] = {"freebase_url": freebase_url,
#                      "freebase_type": freebase_type,
#                      "figer_type": figer_type}
        m[dbplink] = get_first_non_empty_figer(figer_type)
    return m

def get_first_non_empty_figer(l):
    for t in l:
        if t != '':
            return t
    return ''


#def dbpedia_to_figer(dbpedia,freebase,figer):
#    m = {}
#    for dbplink in dbpedia:
#        freebase_type = []
#        figer_type = []
#        freebase_url = dbpedia[dbplink]
#        if freebase_url in freebase:
#            freebase_type = freebase[freebase_url]
#        for ft in freebase_type:
#            if ft in figer and figer[ft] != '':
#                figer_type.append(figer[ft])
#        m[dbplink] = [freebase_url, freebase_type, figer_type]
#        return m

#def write_map_to_file(m):
#    with gzip.open(outputfile, 'w') as o:
#        for dbpedia in m:
#            entry = dbpedia # DBPedia url
#            entry += '\t' + m[dbpedia][0] # Freebase url
#            entry += '\t' + ' '.join(m[dbpedia][1]) # Freebase type
#            entry += '\t' + ' '.join(m[dbpedia][2]) # FIGER type
#            o.write(entry+'\n')

# Get DBPedia url -> Freebase url links (from DBPedia Freebase links)
res = dbpedia_url_to_freebase_url()
dbpedia_to_freebase = res[0]
freebaselinks = res[1]
# Get Freebase type(s) from Freebase (using mapping file from Javad)
res = freebase_url_to_type(freebaselinks)
freebase_url_to_type = res[0]
freebasetypes = res[1]
# Get FIGER type from Freebase type
# Using mapping from: https://github.com/xiaoling/figer
freebase_to_figer = freebase_type_to_figer_type(freebasetypes)
map_to_figer = dbpedia_to_figer(dbpedia_to_freebase,freebase_url_to_type,freebase_to_figer)
# Output mapping to file
with gzip.open(outputfile, 'w') as o:
    json.dump(map_to_figer, o)
#write_map_to_file(map_to_figer)

