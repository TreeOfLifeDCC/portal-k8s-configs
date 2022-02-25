import requests
import subprocess
from lxml import etree
from elasticsearch import Elasticsearch
import json
import urllib.parse


es = Elasticsearch(hosts=["45.88.81.118:80/elasticsearch"])
data_portal = es.search(index='data_portal', size=10000)

names = list()
orgDetailsErrorList = list()
for organism in data_portal['hits']['hits']:
    names.append(organism['_id'])
        
mappings = dict()
for index, organism in enumerate(names):
    response = requests.get("https://portal.darwintreeoflife.org/api/root_organisms/root?id="+organism)
    jsonResponse = response.json()
    if response.status_code == 200 and len(jsonResponse['organism']) >0:
        print(response.status_code, jsonResponse['organism'])
    else:
        orgDetailsErrorList.append(jsonResponse['organism'])

with open('errorList.json', 'w') as f:
    f.write(str(orgDetailsErrorList))