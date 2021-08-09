import requests

from elasticsearch import Elasticsearch
from datetime import datetime

from common_functions import get_date_and_time, get_samples, parse_assemblies, \
    get_reads

es = Elasticsearch(['elasticsearch:9200'])
new_data_portal_samples = list()
new_organisms_samples = list()
new_specimens_samples = list()


def main():
    print(f"{get_date_and_time()}: starting samples update")
    # get existing records from ES
    data_portal_samples = get_samples('data_portal_index', es)
    organisms_samples = get_samples('organisms_test', es)
    specimens_samples = get_samples('specimens_test', es)
    # check assemblies for organisms
    for biosample_id, record in organisms_samples.items():
        # Get percent of data checked
        keys = list(organisms_samples.keys())
        percent = keys.index(biosample_id)/len(organisms_samples)
        percent = int(percent * 100)
        print(f"{get_date_and_time()}: organisms {percent}% ready")

        assemblies = parse_assemblies(biosample_id)
        # Check assemblies for organisms
        if len(assemblies) > 0 and len(record['assemblies']) == 0:
            record['assemblies'] = assemblies
            # Mark this sample to be indexed in ES
            new_organisms_samples.append(biosample_id)
            organism = record['organism']['text']
            # Add assemblies for data_portal_index
            data_portal_samples[organism].setdefault('assemblies', list())
            data_portal_samples[organism]['assemblies'].extend(assemblies)
            # Update data_portal_index status
            for abstract_sample in data_portal_samples[organism]['records']:
                if abstract_sample['accession'] == biosample_id:
                    abstract_sample['trackingSystem'] = 'Assemblies - Submitted'
            if data_portal_samples[organism]['trackingSystem']['status'] in \
                    ['Submitted to BioSamples', 'Mapped Reads - Submitted']:
                data_portal_samples[organism]['trackingSystem'] = {
                    'rank': 2,
                    'status': 'Assemblies - Submitted'
                }
            # Add this organism to be indexed in ES
            new_data_portal_samples.append(organism)

    # Check raw data and mapped reads for specimens
    for biosample_id, record in specimens_samples.items():
        # Get percent of data checked
        keys = list(specimens_samples.keys())
        percent = keys.index(biosample_id) / len(specimens_samples)
        percent = int(percent * 100)
        print(f"{get_date_and_time()}: specimens {percent}% ready")
        experiment = get_reads(biosample_id)
        if len(experiment) > 0 and len(record['experiment']) == 0:
            record['experiment'] = experiment
            # Mark this sample to be indexed in ES
            new_specimens_samples.append(biosample_id)
            # Add experiments for data_portal_index
            organism = record['organism']['text']
            data_portal_samples[organism].setdefault('experiment', list())
            data_portal_samples[organism]['assemblies'].extend(experiment)
            # Update tracking status of data_portal_index if required
            if data_portal_samples[organism]['trackingSystem']['status'] == \
                    'Submitted to BioSamples':
                data_portal_samples[organism]['trackingSystem'] = {
                    'rank': 1,
                    'status': 'Mapped Reads - Submitted'
                }
                new_data_portal_samples.append(organism)

    # Number of records to be unpdated
    print(f"{get_date_and_time()}: new data_portal_index records: "
          f"{len(list(set(new_data_portal_samples)))}")
    print(f"{get_date_and_time()}: new organisms_test records: "
          f"{len(list(set(new_organisms_samples)))}")
    print(f"{get_date_and_time()}: new specimens_test records: "
          f"{len(list(set(new_specimens_samples)))}")

    print(f"{get_date_and_time()}: indexing data_portal_index data")
    for organism, record in data_portal_samples.items():
        if organism in new_data_portal_samples:
            es.index('data_portal_index', record, id=organism)

    print(f"{get_date_and_time()}: indexing organisms_test data")
    for biosample_id, record in organisms_samples.items():
        if biosample_id in new_organisms_samples:
            es.index('organisms_test', record, id=biosample_id)

    print(f"{get_date_and_time()}: indexing specimens_test data")
    for biosample_id, record in specimens_samples.items():
        if biosample_id in new_specimens_samples:
            es.index('specimens_test', record, id=biosample_id)
    print(f"{get_date_and_time()}: finishing samples update")


if __name__ == "__main__":
    main()
