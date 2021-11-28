import requests
import subprocess
import json
import ast
from lxml import etree
from elasticsearch import Elasticsearch
from neo4j import GraphDatabase
from neo4jConnection import Neo4jConnection

conn = Neo4jConnection(uri="bolt://45.88.80.221:30087", 
                       user="neo4j",              
                       pwd="DtolNeo4jAdminUser@123")
es = Elasticsearch(hosts=["45.88.81.97:80/elasticsearch"])
taxaOrderObj = {}
taxonomiesList = list()
aggregationsResp = dict()
indexCounter = 2
taxonomiesOmitted = []
aggregationsQuery = dict()

taxonomiesList.append({"id":1, "name":"Eukaryota", "rank":"superkingdom", "size":102, "parentId":0, "commonName": "eucaryotes"})
taxaOrderObj["Eukaryota"] = 1
kingdomRanks = ['Metazoa','Viridiplantae','Fungi']
taxaRankArray = ["kingdom","subkingdom","superphylum","phylum","subphylum","superclass","class","infraclass","cohort","subcohort","superorder","order","parvorder","suborder","infraorder","section","subsection","superfamily","family","subfamily","tribe","subtribe","genus","series","subgenus","species_group","species_subgroup","species","subspecies","varietas","forma"]
headers = {'content-type': 'application/json'}
neo4jQuery = "UNWIND $taxaArray AS taxonomies \
CREATE (t:Taxonomies) \
SET t=taxonomies \
WITH t, taxonomies.parentId as parentId \
MATCH (parent:Taxonomies {id:parentId}) \
CREATE (parent)-[:CHILD]->(t)"

with open('taxa-aggs-query.txt', 'r') as file_content:
    aggregationsQuery = json.load(file_content)
    aggregationsQuery = json.dumps(aggregationsQuery)

aggregationsResp = requests.post("http://45.88.81.97/elasticsearch/data_portal_index/_search?pretty",data=aggregationsQuery, headers=headers).json()
for rank in taxaRankArray:
    taxRankName = rank
    taxonomies = aggregationsResp['aggregations'][rank]['scientificName']['buckets']
    for element in taxonomies:
        taxaObject = {}
        scientificName = element['key']
        if(scientificName != 'Other'):
            if(len(element['taxId']['buckets']) > 0):
                taxId = element['taxId']['buckets'][0]['key']
                results = subprocess.run('curl -k https://www.ebi.ac.uk/ena/browser/api/xml/'+taxId, shell=True, capture_output=True)
                try:
                    root = etree.fromstring(results.stdout)
                    counter = 0
                    parentTaxon = root.find('taxon')
                    commonName = parentTaxon.get('commonName')
                    for taxon in root.find('taxon').find('lineage').findall('taxon'):
                        if(counter >0):
                            if len(taxaObject) != 0:
                                taxonomiesList.append(taxaObject)
                            break
                        else:
                            ranx = taxon.get('rank')
                            if ranx:
                                if ranx == 'species group':
                                    ranx = 'species_group'
                                elif ranx == 'species subgroup':
                                    ranx = 'species_subgroup'
                                if(taxon.get('scientificName') in taxaOrderObj):
                                    counter = counter + 1
                                    taxaOrderObj[scientificName] = indexCounter
                                    taxaObject["id"] = indexCounter
                                    taxaObject["name"] = scientificName
                                    taxaObject["rank"] = taxRankName
                                    taxaObject["size"] = element['doc_count']
                                    taxaObject["parentId"] = taxaOrderObj[taxon.get('scientificName')]
                                    if commonName:
                                        taxaObject["commonName"] = commonName
                                    else:
                                        taxaObject["commonName"] = 'Other'
                                    indexCounter = indexCounter + 1
                                else:
                                    taxonomiesOmitted.append(scientificName)
                except etree.XMLSyntaxError:
                    print('**************Skipping invalid XML from URL {}'.format(scientificName + ': https://www.ebi.ac.uk/ena/browser/api/xml/'+taxId))
                    taxonomiesOmitted.append(scientificName)
                    continue 
            else:
                taxonomiesOmitted.append(scientificName)

conn.query(neo4jQuery, parameters = {'taxaArray':taxonomiesList})
with open('taxonomies.json', 'w') as f:
    f.write(str(taxonomiesList))
                          
with open('taxonomies-omited.txt', 'w') as f:
    f.write(str(taxonomiesOmitted))