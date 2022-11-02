from typing import List
import requests
import subprocess
from lxml import etree
from elasticsearch import Elasticsearch
from elasticsearch import RequestsHttpConnection

es = Elasticsearch('http://elasticcron:9200', connection_class=RequestsHttpConnection,
                   use_ssl=False, verify_certs=False, timeout=10000)
data_portal = es.search(index='data_portal', size=10000)
headers = {'content-type': 'application/json'}
organismList = list()

for org in data_portal['hits']['hits']:
    aggregationsResp = dict()
    orgGeoList = list()
    specGeoList = list()
    organism_id = org["_id"]
    organism_id = organism_id.replace('/','_')
    organism = org['_source']
    query = '{"query": {"bool": {"must": [{"term": {"organism.text.keyword":"'+ org["_id"] +'"}}]}}}'
    aggregationsResp = requests.post("http://elasticcron:9200/organisms_test/_search?pretty",data=query, headers=headers, verify=False).json()
    for relOrg in aggregationsResp["hits"]["hits"]:
        specList = list()
        relOrg = relOrg["_source"]
        relOrgObj = dict()
        lat = relOrg["geographicLocationLatitude"]["text"]
        lng = relOrg["geographicLocationLongitude"]["text"]
        if (lat != None and lat != "not collected" and lat != "not provided"):
            relOrgObj['organism'] = organism_id
            relOrgObj['accession'] = relOrg["accession"]
            relOrgObj['commonName'] = relOrg["commonName"]
            relOrgObj['sex'] = relOrg["sex"]
            relOrgObj['organismPart'] = relOrg["organismPart"]
            relOrgObj['lat'] = relOrg["geographicLocationLatitude"]["text"]
            relOrgObj['lng'] = relOrg["geographicLocationLongitude"]["text"]
            relOrgObj['locality'] = relOrg["geographicLocationRegionAndLocality"]
            orgGeoList.append(relOrgObj)
            
        if 'specimens' in relOrg and relOrg["specimens"]:
            specList = relOrg["specimens"]
            
        for spec in specList:
            specAccession = spec["accession"]
            specQuery = '{"query": {"bool": {"must": [{"term": {"accession":"'+ specAccession +'"}}]}}}'
            specResp = requests.get("http://elasticcron:9200/specimens_test/_doc/"+specAccession+"?pretty",headers=headers).json()
            specOrg = specResp["_source"]
            specOrgObj = dict()
            lat = specOrg["geographicLocationLatitude"]["text"]
            lng = specOrg["geographicLocationLongitude"]["text"]
            if (lat != None and lat != "not collected" and lat != "not provided"):
                specOrgObj['organism'] = organism_id
                specOrgObj['accession'] = specOrg["accession"]
                specOrgObj['commonName'] = specOrg["commonName"]
                specOrgObj['sex'] = specOrg["sex"]
                specOrgObj['organismPart'] = specOrg["organismPart"]
                specOrgObj['lat'] = specOrg["geographicLocationLatitude"]["text"]
                specOrgObj['lng'] = specOrg["geographicLocationLongitude"]["text"]
                specOrgObj['locality'] = specOrg["geographicLocationRegionAndLocality"]
                specGeoList.append(specOrgObj)        
    organism["orgGeoList"] = orgGeoList
    organism["specGeoList"] = specGeoList
    organismList.append(organism)
    es.index('data_portal', organism, id=organism_id)


# gisListJsonString = json.dumps(organismList)
# with open('organisms-geolocation.json', 'w') as f:
#     f.write(str(gisListJsonString))