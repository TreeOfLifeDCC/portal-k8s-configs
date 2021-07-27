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
    
    statusArray = list();
    if organism['_source']['biosamples'] == 'Done':
        jsonObj = {"name":"biosamples", "status":"Done", "rank":1}
        statusArray.append(jsonObj)
    elif organism['_source']['biosamples'] == 'Waiting':
        jsonObj = {"name":"biosamples", "status":"Waiting", "rank":1}
        statusArray.append(jsonObj)
    
    if organism['_source']['mapped_reads'] == 'Done':
        jsonObj = {"name":"mapped_reads", "status":"Done", "rank":2}
        statusArray.append(jsonObj)
    elif organism['_source']['mapped_reads'] == 'Waiting':
        jsonObj = {"name":"mapped_reads", "status":"Waiting", "rank":2}
        statusArray.append(jsonObj)
        
    if organism['_source']['assemblies'] == 'Done':
        jsonObj = {"name":"assemblies", "status":"Done", "rank":3}
        statusArray.append(jsonObj)
    elif organism['_source']['assemblies'] == 'Waiting':
        jsonObj = {"name":"assemblies", "status":"Waiting", "rank":3}
        statusArray.append(jsonObj)
        
    if organism['_source']['raw_data'] == 'Done':
        jsonObj = {"name":"raw_data", "status":"Done", "rank":4}
        statusArray.append(jsonObj)
    elif organism['_source']['raw_data'] == 'Waiting':
        jsonObj = {"name":"raw_data", "status":"Waiting", "rank":4}
        statusArray.append(jsonObj)
        
    if organism['_source']['annotation'] == 'Done':
        jsonObj = {"name":"annotation", "status":"Done", "rank":5}
        statusArray.append(jsonObj)
    elif organism['_source']['annotation'] == 'Waiting':
        jsonObj = {"name":"annotation", "status":"Waiting", "rank":5}
        statusArray.append(jsonObj)
        
    if organism['_source']['annotation_complete'] == 'Done':
        jsonObj = {"name":"annotation_complete", "status":"Done", "rank":6}
        statusArray.append(jsonObj)
    elif organism['_source']['annotation_complete'] == 'Waiting':
        jsonObj = {"name":"annotation_complete", "status":"Waiting", "rank":6}
        statusArray.append(jsonObj)
    organism['_source']['trackingSystem'] = statusArray
        
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
        es.index('tracking_status_index', organism, id=organism_id)
    else:
        if(organism['_id'] == "Inachis io"):
            tax_id = mappings[organism['_id']]
            organism_id = organism['_id']
            organism = organism['_source']
            organism['tax_id'] = 0
            organism['taxonomies'] = dict()        
            for rank in ranks:
                if(rank != 'superkingdom'):
                    taxa = {'scientificName': 'Other', 'commonName': 'Other'}
                    organism['taxonomies'][rank] = taxa
                elif(rank == 'superkingdom'):
                    taxa = {'scientificName': 'Eukaryota', 'commonName': 'eucaryotes'}
                    organism['taxonomies'][rank] = taxa
            es.index('tracking_status_index', organism, id=organism_id)