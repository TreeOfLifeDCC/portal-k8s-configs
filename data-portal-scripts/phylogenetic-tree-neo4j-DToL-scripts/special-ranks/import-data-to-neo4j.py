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

neo4jRankQuery = "UNWIND $phylogeny AS phylogeny \
CREATE (p:Phylogeny) \
SET p=phylogeny \
WITH p, phylogeny.parentId as parentId \
MATCH (parent:Phylogeny {id:parentId}) \
CREATE (parent)-[:CHILDREN]->(p)"

neo4jDeleteQuery = "MATCH (n:Phylogeny) DETACH DELETE n"

conn.query(neo4jDeleteQuery)

with open('taxonomies-ranks.json', 'r') as f:
    phylogenyList = json.load(f)
conn.query(neo4jRankQuery, parameters = {'phylogeny':phylogenyList})