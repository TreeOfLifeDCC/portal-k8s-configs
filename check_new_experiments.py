from elasticsearch import Elasticsearch
import requests
from lxml import etree

from common_functions import get_reads, get_samples
es = Elasticsearch(['elasticsearch:9200'])


def main():
    specimens = get_samples("specimens_test", es)
    data_portal = get_samples("data_portal_index", es)
    for biosample_id, item in specimens.items():
        experiments = get_reads(biosample_id)
        organism_name = item['organism']['text']

        # check existing experiments
        existing_ids = list()
        for exp in data_portal[organism_name]['experiment']:
            existing_ids.append(exp['experiment_accession'])

        # check experiments that ENA returns
        for exp in experiments:
            # new experiment was returned by ENA
            if exp['experiment_accession'] not in existing_ids:
                # getting information about library construction protocol
                response = requests.get(
                    f"https://www.ebi.ac.uk/ena/browser/api/xml/"
                    f"{exp['experiment_accession']}")
                root = etree.fromstring(response.content)
                library_construction_protocol = root.find('EXPERIMENT').find(
                    'DESIGN').find('LIBRARY_DESCRIPTOR').find(
                    'LIBRARY_CONSTRUCTION_PROTOCOL')
                if library_construction_protocol is None:
                    exp['library_construction_protocol'] = None
                else:
                    exp[
                        'library_construction_protocol'] = \
                        library_construction_protocol.text
                # getting new experiment to specimen_test
                item['experiment'].append(exp)
                # getting new experiment to data_portal_index
                data_portal[organism_name]['experiment'].append(exp)
                # Changing status on more advanced
                if data_portal[organism_name]['trackingSystem']['status'] \
                        == 'Submitted to BioSamples':
                    data_portal[organism_name]['trackingSystem'][
                        'status'] = 'Mapped Reads - Submitted'
                    data_portal[organism_name]['trackingSystem']['rank'] = 1
                es.index('specimens_test', item, id=biosample_id)
                es.index('data_portal_index', data_portal[organism_name],
                         id=organism_name)


if __name__ == "__main__":
    main()
