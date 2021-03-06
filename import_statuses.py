from elasticsearch import Elasticsearch

es = Elasticsearch(['elasticsearch:9200'])


def main():
    data = es.search(index='organisms', size=10000)
    existing_data = get_existing_data()
    for record in data['hits']['hits']:
        tmp = dict()
        print(record)
        tmp['organism'] = record['_source']['organism']['text']
        tmp['commonName'] = record['_source']['commonName']
        tmp['biosamples'] = 'Done'
        tmp['biosamples_date'] = get_biosamples_date(
            record['_source']['customFields'])
        if len(record['_source']['experiment']):
            tmp['ena_date'] = record['_source']['experiment'][0]['first_public']
        else:
            tmp['ena_date'] = None
        # TODO: add an ENSEMBL check
        tmp['annotation_date'] = None
        if len(record['_source']['experiment']):
            tmp['raw_data'] = check_raw_data_status(record['_source']['experiment'])
            tmp['mapped_reads'] = check_mapped_reads_status(record['_source']['experiment'])
        else:
            tmp['raw_data'] = None
            tmp['mapped_reads'] = None
        tmp['assemblies'] = check_assemblies(record['_source']['assemblies'])
        # TODO: add an ENSEMBL check
        tmp['annotation'] = 'Waiting'
        tmp['annotation_complete'] = check_annotation_complete(tmp['organism'])
        if tmp['organism'] in existing_data:
            # es.index('statuses', tmp, id=existing_data[tmp['organism']])
            pass
        else:
            es.index('statuses', tmp)


def get_biosamples_date(record):
    for item in record:
        if item['name'] == 'releaseDate':
            return item['value']


def get_existing_data():
    existing_data = dict()
    data = es.search(index='statuses', size=10000)
    for record in data['hits']['hits']:
        existing_data[record['_source']['organism']] = record['_id']
    return existing_data


# TODO: refactor
def check_raw_data_status(record):
    if len(record[0]['fastq_ftp']) != 0:
        return 'Done'
    else:
        return 'Waiting'


# TODO: refactor
def check_mapped_reads_status(record):
    if len(record[0]['submitted_ftp']) != 0:
        return 'Done'
    else:
        return 'Waiting'


# TODO: refactor
def check_assemblies(record):
    if len(record) != 0:
        return 'Done'
    else:
        return 'Waiting'


def check_annotation_complete(record):
    if record == 'Salmo trutta' or record == 'Sciurus vulgaris' \
            or record == 'Aquila chrysaetos chrysaetos':
        return 'Done'
    else:
        return 'Waiting'


if __name__ == "__main__":
    main()