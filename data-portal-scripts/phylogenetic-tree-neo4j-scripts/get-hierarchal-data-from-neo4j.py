import requests
import subprocess
import json
from lxml import etree
from elasticsearch import Elasticsearch
from neo4j import GraphDatabase
from neo4jConnection import Neo4jConnection

conn = Neo4jConnection(uri="bolt://45.86.170.227:31552", 
                       user="neo4j",              
                       pwd="DtolNeo4jAdminUser@123")

# query = "MATCH (n:Taxonomies) \
# WITH n, [(n)<-[:CHILD]-(x) | x][0] as parent,  [(x)<-[:CHILD]-(n) | x] as children \
# RETURN n, parent, children"

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
# print(response)

with open('neo4j-tree-data.json', 'w') as f:
    f.write(str(response))