from elasticsearch import Elasticsearch
import json
es = Elasticsearch(['elasticsearch:9200'])
with open("new_index.json") as json_file:
    data = json.load(json_file)
for organism, record in data.items():
    es.index('new_index', record, id=organism)
