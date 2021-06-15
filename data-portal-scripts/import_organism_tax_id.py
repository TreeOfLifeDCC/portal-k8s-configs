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
    if(organism_id != "Asterina gibbosa (Pennant, 1777)" and organism_id != "Inachis io"):
        response = requests.get("https://www.ebi.ac.uk/ena/taxonomy/rest/scientific-name/"+organism_id).json()
        organism['tax_id'] = response[0]['taxId']
        es.index('data_portal_index', organism, id=organism_id)
    else:
        if(organism_id == "Asterina gibbosa (Pennant, 1777)"):
            response = requests.get("https://www.ebi.ac.uk/ena/taxonomy/rest/scientific-name/Asterina%20gibbosa").json()
            organism['tax_id'] = response[0]['taxId']
            es.index('data_portal_index', organism, id=organism_id)    