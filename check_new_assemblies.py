from elasticsearch import Elasticsearch
import requests
from common_functions import get_samples, parse_assemblies

es = Elasticsearch(['elasticsearch:9200'])


def main():
    organisms = get_samples("organisms_test", es)
    data_portal = get_samples("data_portal_index", es)
    for biosample_id, item in organisms.items():
        assemblies = parse_assemblies(biosample_id)
        organism_name = item['organism']['text']
        existing_ids = list()
        # getting existing assemblies
        for assmbl in data_portal[organism_name]['assemblies']:
            existing_ids.append(assmbl['accession'])
        for assmbl in assemblies:
            # if we found new assembly
            if assmbl['accession'] not in existing_ids:
                # add it to organisms_test
                item['assemblies'].append(assmbl)
                # add it to specimens_test
                data_portal[organism_name]['assemblies'].append(assmbl)
                # changing statuses of data_portal_index
                if data_portal[organism_name]['trackingSystem']['status'] \
                        != 'Assemblies - Submitted':
                    data_portal[organism_name]['trackingSystem'][
                        'status'] = 'Assemblies - Submitted'
                    data_portal[organism_name]['trackingSystem']['rank'] = 2
                # changing statuses of linked records
                for record in data_portal[organism_name]['records']:
                    if record['accession'] == biosample_id:
                        record['trackingSystem'] = 'Assemblies - Submitted'
                es.index('organisms_test', item, id=biosample_id)
                es.index('data_portal_index', data_portal[organism_name],
                         id=organism_name)


if __name__ == "__main__":
    main()
