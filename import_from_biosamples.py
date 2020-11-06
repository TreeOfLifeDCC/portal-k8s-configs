import requests
from elasticsearch import Elasticsearch

es = Elasticsearch(['elasticsearch:9200'])

organism_terms = ['WHOLE ORGANISM', 'MYCELIUM', 'WHOLE PLANT']


def import_records():
    samples = requests.get(
        "https://www.ebi.ac.uk/biosamples/samples?size=10000&"
        "filter=attr%3Aproject%20name%3ADTOL").json()
    for sample in samples['_embedded']['samples']:
        parse_record(sample['characteristics'])


def parse_record(sample):
    index = 'organisms' if sample['organism part'][0]['text'] \
                           in organism_terms else 'specimens'
    record = dict()
    # Mandatory fields
    record['accession'] = sample['accession']
    record['taxonId'] = sample['taxId']
    record['organismPart'] = sample['organism part'][0]['text']
    record['lifestage'] = check_field_existence(sample, 'lifestage')
    record['projectName'] = sample['project name'][0]['text']
    record['collectedBy'] = sample['collected by'][0]['text']
    record['collectionDate'] = sample['collection date'][0]['text']
    record['geographicLocationCountryAndOrSea'] = sample[
        'geographic location (country and/or sea)'][0]['text']
    record['geographicLocationLatitude'] = {
        'text': sample['geographic location (latitude)'][0]['text'],
        'unit': sample['geographic location (latitude)'][0]['unit']
    }
    record['geographicLocationLongitude'] = {
        'text': sample['geographic location (longitude)'][0]['text'],
        'unit': sample['geographic location (longitude)'][0]['unit']
    }
    record['geographicLocationRegionAndLocality'] = sample[
        'geographic location (region and locality)'][0]['text']
    record['identifiedBy'] = sample['identified by'][0]['text']
    record['habitat'] = sample['habitat'][0]['text']
    record['identifierAffiliation'] = sample[
        'identifier_affiliation'][0]['text']
    record['sex'] = check_field_existence(sample, 'sex')
    record['collectingInstitution'] = sample[
        'collecting institution'][0]['text']
    record['gal'] = sample['GAL'][0]['text']
    record['specimenVoucher'] = check_field_existence(
        sample, 'specimen voucher')
    record['specimenId'] = sample['specimen id'][0]['text']
    record['galSampleId'] = check_field_existence(sample, 'GAL_sample_id')
    record['organism'] = check_field_existence(
        sample, 'organism', ontology=True)
    if record['organism']['text']:
        record['commonName'] = get_common_name(record['organism']['text'])
    else:
        record['commonName'] = None

    # Optional fields
    record['geographicLocationDepth'] = check_field_existence(
        sample, 'geographic location (depth)', units=True)
    record['geographicLocationElevation'] = check_field_existence(
        sample, 'geographic location (elevation)', units=True)
    record['sampleDerivedFrom'] = check_field_existence(
        sample, 'sample derived from')
    record['relationship'] = check_field_existence(sample, 'relationship')
    record['cultureOrStrainId'] = check_field_existence(
        sample, 'culture or strain id')
    record['experiment'] = list()
    record['assemblies'] = list()
    record['trackingSystem'] = 'Submitted to BioSamples'
    record['etag'] = get_etag(record['accession'])
    if index == 'organisms':
        record['specimens'] = list()

    # Write data to ES
    es.index(index, record, id=record['accession'])


def check_field_existence(sample, field_name, units=False, ontology=False):
    if units:
        if field_name in sample:
            return {
                'text': sample[field_name][0]['text'],
                'unit': sample[field_name][0]['unit']
            }
        else:
            return {
                'text': None,
                'unit': None
            }
    elif ontology:
        if field_name in sample:
            return {
                'text': sample[field_name][0]['text'],
                'ontologyTerm': sample[field_name][0]['ontologyTerms'][0]
            }
        else:
            return {
                'text': None,
                'unit': None
            }
    else:
        if field_name in sample:
            return sample[field_name][0]['text']
        else:
            return None


def get_common_name(latin_name):
    common_name_response = requests.get(
        f"https://www.ebi.ac.uk/ena/taxonomy/rest/scientific-name/{latin_name}")
    common_name_response = common_name_response.json()
    if 'commonName' in common_name_response[0]:
        return common_name_response[0]['commonName']
    else:
        return None


def get_etag(biosamples_id):
    sample = requests.get(
        f"https://www.ebi.ac.uk/biosamples/samples/{biosamples_id}")
    return sample.headers['ETag']


# TODO: check etag
def check_sample_exists(biosamples_id):
    pass


if __name__ == "__main__":
    import_records()
