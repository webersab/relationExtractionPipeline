import requests
import copy

class Agdistis(object):
    #agdistisApi = 'http://139.18.2.164:8080/AGDISTIS_DE'
    #defaultAgdistisParams = {
    #    'text': 'Die Stadt <entity>Dresden</entity> liegt in <entity>Sachsen</entity>',
    #    'type': 'agdistis'
    #    }

    def __init__(self, url):
        self.agdistisApi = url #'http://139.18.2.164:8080/AGDISTIS_DE'
        self.defaultAgdistisParams = {
            'text': 'Die Stadt <entity>Dresden</entity> liegt in <entity>Sachsen</entity>',
            'type': 'agdistis'
            } # Change type to 'candidates' to get multiple results with scores (for amiguous entities)

    def disambiguate(self, text):
        """
            Input: text (any arbitrary string with annotated entities -- <entity>Austria</entity>)
            Output: entities as a list [{'start': 0, 'offset': 7, 'disambiguatedURL': 'http://dbpedia.org/resource/Austria', 'namedEntity': 'Austria'}]
        """
        payload = copy.copy(self.defaultAgdistisParams)
        payload['text'] = text
        r = requests.post(self.agdistisApi, data=payload)
        entities = []
        try:
            entities = r.json()
        except ValueError as e:
            #server failed
            entities = [{'start': 0, 'offset': 0, 'disambiguatedURL': '', 'namedEntity': ''}]
        return entities

    def disambiguateEntity(self, entity):
        """
            Support method to wrap entity into <entity/> tag
        """
        return self.disambiguate("<entity>%s</entity>"%(entity,))

if __name__ == "__main__":
    agdistis = Agdistis('http://139.18.2.164:8080/AGDISTIS_DE')
    entities = agdistis.disambiguate('<entity>Austria</entity>')
    entities = agdistis.disambiguateEntity('Austria')
    print(entities)
