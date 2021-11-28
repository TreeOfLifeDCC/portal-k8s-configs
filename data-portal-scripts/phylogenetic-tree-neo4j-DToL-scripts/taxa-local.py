import requests
import subprocess
import json
import ast
from lxml import etree
from elasticsearch import Elasticsearch
from neo4j import GraphDatabase
from neo4jConnection import Neo4jConnection

taxonomiesList = list()
conn = Neo4jConnection(uri="bolt://45.86.170.227:31552", 
                       user="neo4j",              
                       pwd="DtolNeo4jAdminUser@123")

neo4jQuery = "UNWIND $taxaArray AS taxonomies \
CREATE (t:Taxonomies) \
SET t=taxonomies \
WITH t, taxonomies.parentId as parentId \
MATCH (parent:Taxonomies {id:parentId}) \
CREATE (parent)-[:CHILD]->(t)"

with open('taxonomies.json', 'r') as f:
    taxonomiesList = f.read()

taxaListMap = ast.literal_eval(taxonomiesList)

conn.query(neo4jQuery, parameters = {'taxaArray':taxaListMap})