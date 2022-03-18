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

headers = {'content-type': 'application/json'}
neo4jQuery = "UNWIND $taxaArray AS taxonomies \
CREATE (t:Taxonomies) \
SET t=taxonomies \
WITH t, taxonomies.parentId as parentId \
MATCH (parent:Taxonomies {id:parentId}) \
CREATE (parent)-[:CHILD]->(t)"

neo4jDeleteQuery = "MATCH (n) DETACH DELETE n"
conn.query(neo4jDeleteQuery)

with open('taxonomies.json', 'r') as f:
    taxonomiesList = f.read()
    taxonomiesList = ast.literal_eval(taxonomiesList)


conn.query(neo4jQuery, parameters = {'taxaArray':taxonomiesList})