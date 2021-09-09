import requests
import subprocess
from lxml import etree
from elasticsearch import Elasticsearch
import json

es = Elasticsearch(hosts=["45.86.170.227:80/elasticsearch"])
data_portal = es.search(index='data_portal_index', size=10000)
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
    if(organism['_id'] != "Inachis io"):
        tax_id = mappings[organism['_id']]
        organism_id = organism['_id']
        organism = organism['_source']
        organism['tax_id'] = tax_id
        organism['taxonomies'] = dict()        
        for rank in ranks:
            taxa = {'scientificName': 'Other', 'commonName': 'Other'}
            organism['taxonomies'][rank] = taxa
        results = subprocess.run('curl -k https://www.ebi.ac.uk/ena/browser/api/xml/'+tax_id, shell=True, capture_output=True)
        root = etree.fromstring(results.stdout)
        for taxon in root.find('taxon').find('lineage').findall('taxon'):
            rank = taxon.get('rank')
            if rank:
                if rank == 'species group':
                    rank = 'species_group'
                elif rank == 'species subgroup':
                    rank = 'species_subgroup'
                organism['taxonomies'][rank]['scientificName'] = taxon.get('scientificName')
                if taxon.get('commonName'):
                    organism['taxonomies'][rank]['commonName'] = taxon.get('commonName')
        es.index('data_portal_index', organism, id=organism_id)
    else:
        if(organism['_id'] == "Inachis io"):
            tax_id = mappings[organism['_id']]
            organism_id = organism['_id']
            organism = organism['_source']
            organism['tax_id'] = 0
            organism['taxonomies'] = dict()        
            for rank in ranks:
                taxa = {'scientificName': 'Other', 'commonName': 'Other'}
                organism['taxonomies'][rank] = taxa
            es.index('data_portal_index', organism, id=organism_id)