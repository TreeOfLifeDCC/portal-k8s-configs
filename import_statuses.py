from elasticsearch import Elasticsearch

from common_functions import get_samples

es = Elasticsearch(['elasticsearch:9200'])


def main():
    data_portal_samples = get_samples('data_portal_index')
    for organism, record in data_portal_samples.items():
        tmp = dict()
        tmp['organism'] = record['organism']
        tmp['commonName'] = record['commonName']
        tmp['biosamples'] = 'Done'
        tmp['biosamples_date'] = None
        tmp['ena_date'] = None
        tmp['annotation_date'] = None
        tmp['raw_data'] = check_raw_data_status(record)
        tmp['mapped_reads'] = tmp['raw_data']
        tmp['assemblies'] = check_assemblies(record)
        tmp['annotation'] = 'Waiting'
        tmp['annotation_complete'] = check_annotation_complete(record)
        tmp['trackingSystem'] = [
            {'name': 'biosamples', 'status': 'Done', 'rank': 1},
            {'name': 'mapped_reads', 'status': tmp['mapped_reads'], 'rank': 2},
            {'name': 'assemblies', 'status': tmp['assemblies'], 'rank': 3},
            {'name': 'raw_data', 'status': tmp['raw_data'], 'rank': 4},
            {'name': 'annotation', 'status': 'Waiting', 'rank': 5},
            {'name': 'annotation_complete',
             'status': tmp['annotation_complete'], 'rank': 6}
        ]
        if 'taxonomies' in record:
            tmp['taxonomies'] = record['taxonomies']
        es.index('tracking_status_index', tmp, id=organism)


def check_raw_data_status(record):
    if 'experiment' in record and len(record['experiment']) > 0:
        return 'Done'
    else:
        return 'Waiting'


def check_assemblies(record):
    if 'assemblies' in record and len(record['assemblies']) > 0:
        return 'Done'
    else:
        return 'Waiting'


def check_annotation_complete(record):
    if record['trackingSystem']['status'] == 'Annotation Complete':
        return 'Done'
    else:
        return 'Waiting'


if __name__ == "__main__":
    main()

