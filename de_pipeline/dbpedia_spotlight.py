import spotlight

class DBPediaSpotlight():

    def __init__(self, url):
        self.url = url 

    def disambiguate(self, text, confidence=0, support=0):
        annotations = spotlight.annotate(self.url,
                                         text,
                                         confidence=confidence,
                                         support=support)
        return annotations
        
if __name__ == "__main__":
    url = 'http://scribe.inf.ed.ac.uk:2222/rest/annotate'
    string = 'Die Familie lebt in Brixton.'
    spot = DBPediaSpotlight(url)
    annotations = spot.disambiguate(string, confidence=0, support=0)
    print annotations
