import requests
import subprocess
import json
import ast
from lxml import etree
from elasticsearch import Elasticsearch
from neo4j import GraphDatabase
from neo4jConnection import Neo4jConnection

conn = Neo4jConnection(uri="bolt://45.88.80.141:30087", 
                       user="neo4j",              
                       pwd="DtolNeo4jAdminUser@123")
es = Elasticsearch(hosts=["45.88.81.118:80/elasticsearch"])
taxaOrderObj = {}
taxonomiesList = list()
taxonomiesListMap = []
aggregationsResp = dict()
indexCounter = 2
taxonomiesOmitted = []
aggregationsQuery = dict()
parentRankIndex = 0

taxonomiesList.append({"id":1, "name":"Eukaryota", "rank":"superkingdom", "size":3682, "parentId":0, "commonName": "eucaryotes"})
taxaOrderObj["Eukaryota"] = 1

taxaRankArray = ["kingdom","phylum","class","order","family","genus","species"]
taxaTempRankArray = ["superkingdom","kingdom","phylum","class","order","family","genus","species"]
headers = {'content-type': 'application/json'}
neo4jRankQuery = "UNWIND $phylogeny AS phylogeny \
CREATE (p:Phylogeny) \
SET p=phylogeny \
WITH p, phylogeny.parentId as parentId \
MATCH (parent:Phylogeny {id:parentId}) \
CREATE (parent)-[:CHILDREN]->(p)"
neo4jDeleteQuery = "MATCH (n:Phylogeny) DETACH DELETE n"

with open('taxa-aggs-query.txt', 'r') as file_content:
    aggregationsQuery = json.load(file_content)
    aggregationsQuery = json.dumps(aggregationsQuery)

aggregationsResp = requests.post("http://45.88.81.118/elasticsearch/data_portal/_search?pretty",data=aggregationsQuery, headers=headers).json()
for index,rank in enumerate(taxaRankArray):
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
                    parentTaxon = root.find('taxon')
                    if(parentTaxon):
                        commonName = parentTaxon.get('commonName')
                        lineageRankIndex = 0
                        elementRankIndex = taxaTempRankArray.index(taxRankName)
                        for taxon in root.find('taxon').find('lineage').findall('taxon'):
                            ranx = taxon.get('rank')
                            if ranx:
                                tObject = dict()
                                if(ranx in taxaTempRankArray):
                                    lineageRankIndex = taxaTempRankArray.index(ranx)
                                    if(elementRankIndex > lineageRankIndex):
                                        rankDifference = elementRankIndex-lineageRankIndex
                                        tObject["name"] = taxon.get('scientificName')
                                        tObject["rank"] = ranx
                                        tObject["rankDifference"]=rankDifference
                                        if list(filter(lambda x:x["name"]==tObject["name"],taxonomiesList)):
                                            taxonomiesListMap.append(tObject)
                        taxaObject["id"] = indexCounter
                        taxaObject["name"] = scientificName
                        taxaObject["rank"] = taxRankName
                        taxaObject["size"] = element['doc_count']
                        parentobj = min(taxonomiesListMap, key=lambda x:x['rankDifference'])
                        obj = list(filter(lambda x:x["name"]==parentobj["name"],taxonomiesList))
                        taxaObject["parentId"] = obj[0]["id"]
                        if commonName:
                            taxaObject["commonName"] = commonName
                        else:
                            taxaObject["commonName"] = 'Other'
                        indexCounter = indexCounter + 1
                        taxonomiesList.append(taxaObject)
                        taxonomiesListMap = []
                except etree.XMLSyntaxError:
                    print('**************Skipping invalid XML from URL {}'.format(scientificName + ': https://www.ebi.ac.uk/ena/browser/api/xml/'+taxId))
                    taxonomiesOmitted.append(scientificName)
                    continue 
            else:
                taxonomiesOmitted.append(scientificName)

taxonomiesListJsonString = json.dumps(taxonomiesList)
taxonomiesListJsonObj = json.loads(taxonomiesListJsonString)

conn.query(neo4jDeleteQuery)
conn.query(neo4jRankQuery, parameters = {'phylogeny':taxonomiesListJsonObj})

with open('taxonomies-ranks.json', 'w') as f:
    f.write(taxonomiesListJsonString)
                          
with open('taxonomies-omited-ranks.json', 'w') as f:
    f.write(str(taxonomiesOmitted))