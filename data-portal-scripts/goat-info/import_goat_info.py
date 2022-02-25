from typing import List
import requests
import subprocess
from lxml import etree
from elasticsearch import Elasticsearch
import json

es = Elasticsearch(hosts=["45.88.81.118:80/elasticsearch"])
data_portal = es.search(index='data_portal', size=10000)
count = 0
for org in data_portal['hits']['hits']:
    goatObj = dict()
    attrList = list()
    attrObj = {}
    organism_id = org["_id"]
    organism = org['_source']
    tax_id = organism['tax_id']
    goatAPIResponse = requests.get("https://goat.genomehubs.org/api/v0.0.1/record?recordId="+tax_id+"&result=taxon&taxonomy=ncbi").json()
    if(goatAPIResponse['records']):
        temp = goatAPIResponse['records'][0]['record']['attributes']
        if('genome_size' in temp):
            attrObj['name'] = 'genome_size'
            attrObj['value'] = temp['genome_size']['value']
            attrObj['count'] = temp['genome_size']['count']
            attrObj['aggregation_method'] = temp['genome_size']['aggregation_method']
            attrObj['aggregation_source'] = temp['genome_size']['aggregation_source']
            attrList.append(attrObj)
            attrObj = {}
        
        if('busco_completeness' in temp):
            attrObj['name'] = 'busco_completeness'
            attrObj['value'] = temp['busco_completeness']['value']
            attrObj['count'] = temp['busco_completeness']['count']
            attrObj['aggregation_method'] = temp['busco_completeness']['aggregation_method']
            attrObj['aggregation_source'] = temp['busco_completeness']['aggregation_source']
            attrList.append(attrObj)
            attrObj = {}
        
        goatObj["url"] = "https://goat.genomehubs.org/records?record_id="+tax_id+"&result=taxon&taxonomy=ncbi#"+organism_id
        goatObj["attributes"] = attrList
    
    organism['goat_info'] = goatObj
    print(organism_id)
    es.index('data_portal', organism, id=organism_id)