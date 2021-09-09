import requests
import subprocess
import json
import ast
from lxml import etree
from elasticsearch import Elasticsearch
from neo4j import GraphDatabase
from neo4jConnection import Neo4jConnection

conn = Neo4jConnection(uri="bolt://45.86.170.227:31552", 
                       user="neo4j",              
                       pwd="DtolNeo4jAdminUser@123")
es = Elasticsearch(hosts=["45.86.170.227:80/elasticsearch"])
taxaOrderObj = {}
taxonomiesList = list()
aggregationsResp = dict()
indexCounter = 2
taxonomiesOmitted = []

# taxonomiesList.append({"id":1, "name":"Eukaryota", "rank":"superkingdom", "size":1562, "parentId":0, "commonName": "eucaryotes"})
taxaOrderObj["Eukaryota"] = 1
kingdomRanks = ['Metazoa','Viridiplantae','Fungi']
taxaRankArray = ["kingdom","subkingdom","superphylum","phylum","subphylum","superclass","class","subclass","infraclass","cohort","subcohort","superorder","order","parvorder","suborder","infraorder","section","subsection","superfamily","family","subfamily","tribe","subtribe","genus","series","subgenus","species_group","species_subgroup","species","subspecies","varietas","forma"]
headers = {'content-type': 'application/json'}
neo4jQuery = "UNWIND $taxaArray AS taxonomies \
CREATE (t:Taxonomies) \
SET t=taxonomies \
WITH t, taxonomies.parentId as parentId \
MATCH (parent:Taxonomies {id:parentId}) \
CREATE (parent)-[:CHILD]->(t)"

aggregationsResp = requests.post("http://45.86.170.227/elasticsearch/data_portal_index/_search?pretty",data=aggregationsQuery, headers=headers).json()
for rank in taxaRankArray:
    taxRankName = rank
    taxonomies = aggregationsResp['aggregations'][rank]['scientificName']['buckets']
    for element in taxonomies:
        taxaObject = {}
        scientificName = element['key']
        if(scientificName != 'Other'):
            taxonomyLineage = requests.get("https://www.ebi.ac.uk/ena/taxonomy/rest/scientific-name/"+scientificName)
            if taxonomyLineage.text != 'No results.':
                taxonomyLineage = taxonomyLineage.json()
                taxId = taxonomyLineage[0]['taxId']
                results = subprocess.run('curl -k https://www.ebi.ac.uk/ena/browser/api/xml/'+taxId, shell=True, capture_output=True)
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
                        rank = taxon.get('rank')
                        if rank:
                            counter = counter + 1
                            taxaOrderObj[scientificName] = indexCounter
                            if rank == 'species group':
                                rank = 'species_group'
                            elif rank == 'species subgroup':
                                rank = 'species_subgroup'
                            if(taxon.get('scientificName') in taxaOrderObj):
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
# taxaListMap = ast.literal_eval(taxonomiesList)
print(conn.query(neo4jQuery, parameters = {'taxaArray':taxonomiesList}))

with open('taxonomies.json', 'w') as f:
    f.write(str(taxonomiesList))
                          
with open('taxonomies-omited.txt', 'w') as f:
    f.write(str(taxonomiesOmitted))