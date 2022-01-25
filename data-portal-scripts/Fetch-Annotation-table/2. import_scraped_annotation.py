import requests
import subprocess
from lxml import etree
from elasticsearch import Elasticsearch
import json

class ImportAnnotations():
    es = Elasticsearch(hosts=["45.88.81.118:80/elasticsearch"])
    data_portal = es.search(index='data_portal', size=10000)
    annotationsArray = list()
    organisms = list()

    def read_file(self, filename):
        with open(filename, 'r') as file_content:
            annotations = json.load(file_content)
        return annotations
    
    def import_annotations(self):
        self.annotationsArray = self.read_file('annotations.json')
        for organism in self.data_portal['hits']['hits']:
            organism_id = organism['_id']
            organism = organism['_source']
            annotationsDict = list()
            for annot in self.annotationsArray:
                if annot['species'] == organism_id:
                    annotationsDict.append(annot)
            if(len(annotationsDict)> 0):
                organism['annotation'] = annotationsDict
                organism['annotation_complete'] = 'Done'
                organism['trackingSystem'][5] = {'name': 'annotation_complete', 'status': 'Done', 'rank': 6}
                self.es.index('data_portal', organism, id=organism_id)
    
if __name__ == "__main__":
    importAnnotations = ImportAnnotations()
    importAnnotations.import_annotations()