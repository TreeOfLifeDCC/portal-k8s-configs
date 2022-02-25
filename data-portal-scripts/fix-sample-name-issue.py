import requests
import subprocess
from lxml import etree
from elasticsearch import Elasticsearch
import json
import urllib.parse


es = Elasticsearch(hosts=["45.88.81.118:80/elasticsearch"])
data_portal = es.search(index='data_portal', size=10000)
    
for element in data_portal['hits']['hits']:
    organism = element['_source']
    organism_id = element['_id']
    if('/' in organism_id):
        organism_id = organism_id.replace('/','_')
        organism_id = urllib.parse.quote(organism_id, safe='')
        es.index('data_portal', organism, id=organism_id)