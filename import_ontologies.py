import subprocess
from lxml import etree
from elasticsearch import Elasticsearch

from common_functions import get_samples

es = Elasticsearch(['elasticsearch:9200'])


def main():
    data_portal_samples = get_samples('data_portal_index', es)
    ranks = get_ranks()
    for organism, record in data_portal_samples.items():
        if 'taxonomies' not in record:
            print(organism)
            record['taxonomies'] = dict()
            for rank in ranks:
                record['taxonomies'][rank] = {
                    "scientificName": "Other",
                    "commonName": "Other"
                }
            results = subprocess.run(
                f'curl -k https://www.ebi.ac.uk/ena/browser/api/xml/'
                f'{record["tax_id"]}',
                shell=True, capture_output=True)
            root = etree.fromstring(results.stdout)
            if root.find('taxon') is None:
                es.index('data_portal_index', record, id=organism)
                continue
            for taxon in root.find('taxon').find('lineage').findall('taxon'):
                rank = taxon.get('rank')
                if rank:
                    scientific_name = taxon.get('scientificName')
                    common_name = taxon.get('commonName')
                    if scientific_name:
                        record['taxonomies'][rank]['scientificName'] = \
                            scientific_name
                    if common_name:
                        record['taxonomies'][rank]['commonName'] = common_name
            es.index('data_portal_index', record, id=organism)


def get_ranks():
    ranks = list()
    with open('ranks.txt', 'r') as f:
        for line in f:
            line = line.rstrip()
            ranks.append(line)
    return ranks


if __name__ == "__main__":
    main()