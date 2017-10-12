import gzip

freebaselinkfile = 'freebase_links_de.ttl.gz'
freebasetypefile = 'entity2type_names.txt.gz'
figertypefile = 'types.map.gz'

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
        m[dbplink] = [freebase_url, freebase_type, figer_type]
    return m

res = dbpedia_url_to_freebase_url()
dbpedia_to_freebase = res[0]
freebaselinks = res[1]
res = freebase_url_to_type(freebaselinks)
freebase_url_to_type = res[0]
freebasetypes = res[1]
freebase_to_figer = freebase_type_to_figer_type(freebasetypes)
map_to_figer = dbpedia_to_figer(dbpedia_to_freebase,freebase_url_to_type,freebase_to_figer)
