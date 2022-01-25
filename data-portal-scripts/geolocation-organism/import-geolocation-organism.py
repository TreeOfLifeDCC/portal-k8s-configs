import requests
import subprocess
from lxml import etree
from elasticsearch import Elasticsearch
import json

es = Elasticsearch(hosts=["45.88.81.118:80/elasticsearch"])
data_portal = es.search(index='organisms_test', size=10000)
names = list()
organismObj = dict()
for organism in data_portal['hits']['hits']:
    organism_id = organism['_id']
    organismObj['organism_id'] = organism_id
    organismObj['geographicLocationLatitude'] = organism['_source']['geographicLocationLatitude']
    organismObj['geographicLocationLongitude'] = organism['_source']['geographicLocationLongitude']
    organismObj['geographicLocationRegionAndLocality'] = organism['_source']['geographicLocationRegionAndLocality']
    organismObj['organismText'] = organism['_source']['organism']['text']
    print(organismObj)
    es.index('geolocation_organism', organismObj, id=organism_id)
