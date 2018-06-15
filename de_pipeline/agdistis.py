"""
Adapted code from the AGDISTIS project:
http://aksw.org/Projects/AGDISTIS.html

Handles communication with the AGDISTIS server
"""

# Standard
import requests
import copy
from sys import platform


class Agdistis(object):
    """
    gdistisApi = 'http://akswnc9.informatik.uni-leipzig.de:8113/AGDISTIS'
    defaultAgdistisParams = {
        'text': 'Die Stadt <entity>Dresden</entity> liegt in <entity>Sachsen</entity>',
        'type': 'agdistis'
        }
    """
    
    def __init__(self, url):
        self.agdistisApi = url
        self.defaultAgdistisParams = {
            'text': 'Die Stadt <entity>Dresden</entity> liegt in <entity>Sachsen</entity>',
            'type': 'agdistis'
            } # Change type to 'candidates' to get multiple results with scores (for amiguous entities)
        # Solution for mac OSX problem whereby requests hang with multiprocessing
        # https://stackoverflow.com/questions/30453152/python-multiprocessing-and-requests
        if platform == 'darwin': # OSX
            self.session = requests.Session()
            self.session.trust_env = False

    def disambiguate(self, text):
        """
            Input: text (any arbitrary string with annotated entities -- <entity>Austria</entity>)
            Output: entities as a list [{'start': 0, 'offset': 7, 'disambiguatedURL': 'http://dbpedia.org/resource/Austria', 'namedEntity': 'Austria'}]
        """
        payload = copy.copy(self.defaultAgdistisParams)
        payload['text'] = text
        if platform == 'darwin':
            r = self.session.post(self.agdistisApi, data=payload)
        else:
            r = requests.post(self.agdistisApi, data=payload)
        entities = []
        try:
            entities = r.json()
        except ValueError as e:            #server failed
            entities = [{'start': 0, 'offset': 0, 'disambiguatedURL': '', 'namedEntity': ''}]
        return entities

    def disambiguateEntity(self, entity):
        """
            Support method to wrap entity into <entity/> tag
        """
        return self.disambiguate("<entity>%s</entity>"%(entity,))

if __name__ == "__main__":
    """
    For testing against the German endpoint at Leipzig
    """
    agdistis = Agdistis('http://akswnc9.informatik.uni-leipzig.de:8113/AGDISTIS')
    entities = agdistis.disambiguate('<entity>Austria</entity>')
    entities = agdistis.disambiguateEntity('Austria')
    print(entities)
