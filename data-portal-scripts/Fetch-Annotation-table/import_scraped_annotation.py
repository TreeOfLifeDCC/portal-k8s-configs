import requests
import subprocess
from lxml import etree
from elasticsearch import Elasticsearch
import json

class ImportAnnotations():
    es = Elasticsearch(hosts=["45.86.170.227:31664"])
    data_portal = es.search(index='data_portal_index', size=10000)
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
                self.es.index('data_portal_index', organism, id=organism_id)
    
if __name__ == "__main__":
    importAnnotations = ImportAnnotations()
    importAnnotations.import_annotations()