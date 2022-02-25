from typing import List
import requests
import subprocess
from lxml import etree
from elasticsearch import Elasticsearch
import json
import urllib.parse

es = Elasticsearch(hosts=["45.88.81.118:80/elasticsearch"])
data_portal = es.search(index='data_portal', size=10000)
headers = {'content-type': 'application/json'}
aggregationsResp = dict()

for org in data_portal['hits']['hits']:
    specList = list()
    organism_id = org["_id"]
    if('/' in organism_id):
        organism_id = organism_id.replace('/','_')
        organism_id = urllib.parse.quote(organism_id, safe='')
    organism = org['_source']
    query = '{"query": {"bool": {"must": [{"term": {"organism.text.keyword":"'+ organism_id +'"}}]}}}'
    aggregationsResp = requests.post("http://45.88.81.118/elasticsearch/organisms_test/_search?pretty",data=query, headers=headers).json()
    for relOrg in aggregationsResp["hits"]["hits"]:
        relOrg = relOrg["_source"]
        listObj = list()
        if 'specimens' in relOrg and relOrg["specimens"]:
            listObj = relOrg["specimens"]
        specList = specList + listObj
    organism['specimens'] = specList
    
    es.index('data_portal', organism, id=organism_id)
