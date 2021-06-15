import requests
import subprocess
from lxml import etree
from elasticsearch import Elasticsearch
import json

es = Elasticsearch(hosts=["45.86.170.227:31664"])
data_portal = es.search(index='statuses_index', size=10000)
names = list()
for organism in data_portal['hits']['hits']:
    names.append(organism['_id'])
        
mappings = dict()
for index, organism in enumerate(names):
    if(organism != "Asterina gibbosa (Pennant, 1777)" and organism != "Inachis io"):
        response = requests.get("https://www.ebi.ac.uk/ena/taxonomy/rest/scientific-name/"+organism).json()
    else:
        if(organism == "Asterina gibbosa (Pennant, 1777)"):
            response = requests.get("https://www.ebi.ac.uk/ena/taxonomy/rest/scientific-name/Asterina%20gibbosa").json()
    mappings[organism] = response[0]['taxId']

ranks = list()
with open('ranks.txt', 'r') as f:
    for line in f:
        line = line.rstrip()
        ranks.append(line)
for organism in data_portal['hits']['hits']:
    if(organism['_id'] != "Asterina gibbosa (Pennant, 1777)" and organism['_id'] != "Inachis io"):
        tax_id = mappings[organism['_id']]
        organism_id = organism['_id']
        organism = organism['_source']
        organism['taxonomies'] = dict()        
        for rank in ranks:
            organism['taxonomies'][rank] = "Other"
        results = subprocess.run('curl -k https://www.ebi.ac.uk/ena/browser/api/xml/'+tax_id, shell=True, capture_output=True)
        root = etree.fromstring(results.stdout)
        for taxon in root.find('taxon').find('lineage').findall('taxon'):
            rank = taxon.get('rank')
            if rank:
                if rank == 'species group':
                    rank = 'species_group'
                elif rank == 'species subgroup':
                    rank = 'species_subgroup'
                organism['taxonomies'][rank] = taxon.get('scientificName')
        es.index('statuses_index', organism, id=organism_id)