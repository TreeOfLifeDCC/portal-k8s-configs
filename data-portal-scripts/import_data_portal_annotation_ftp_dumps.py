import requests
import subprocess
from lxml import etree
from elasticsearch import Elasticsearch
import json

es = Elasticsearch(hosts=["45.86.170.227:31664"])
data_portal = es.search(index='data_portal_index', size=10000)
names = list()

for organism in data_portal['hits']['hits']:
    organism_id = organism['_id']
    organism = organism['_source']
    
    if 'annotation' in organism:
        for index, annotation in enumerate(organism['annotation']):
            organism['annotation'][index]['other_data']['ftp_dumps'] = organism['annotation'][index]['other_data']['FTP dumps']
                        
        es.index('data_portal_index', organism, id=organism_id)