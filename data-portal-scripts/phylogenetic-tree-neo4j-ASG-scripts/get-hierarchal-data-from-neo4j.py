import requests
import subprocess
import json
from lxml import etree
from elasticsearch import Elasticsearch
from neo4j import GraphDatabase
from neo4jConnection import Neo4jConnection

conn = Neo4jConnection(uri="bolt://45.88.81.49/bolt", 
                       user="neo4j",              
                       pwd="AsgNeo4jAdminUser@123")

mainQuery ="MATCH (parent:Taxonomies {parentId: 0})-[:CHILD]->(child:Taxonomies) \
WITH child \
MATCH childPath=(child)-[:CHILD*0..]->(subChild) \
with childPath  \
,CASE WHEN subChild:Taxonomies THEN subChild.id END as orderField order by orderField \
with collect(childPath) as paths \
CALL apoc.convert.toTree(paths) yield value \
RETURN value"

response = str(conn.query(mainQuery))
response = response.replace("<Record value=","")
response = response.replace(">","")
response = response.replace("'","\"")
response = response.replace("child","children")
response = '{"id":1, "commonName": "eucaryotes", "parentId": 0, "name": "Eukaryota", "children":'+response+"}"

with open('tree-data.json', 'w') as f:
    f.write(str(response))