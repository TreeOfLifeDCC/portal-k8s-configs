import requests
import json

from elasticsearch import Elasticsearch

from common_functions import check_field_existence, get_common_name
from constants import CHECKLIST_FIELDS, ORGANISMS


def main():
    es = Elasticsearch(['elasticsearch:9200'])
    samples = requests.get(
        "https://www.ebi.ac.uk/biosamples/samples?size=100000&"
        "filter=attr%3Aproject%20name%3ADTOL").json()
    data_portal_samples = dict()
    organisms_samples = dict()
    for sample in samples['_embedded']['samples']:
        organism = sample['characteristics']['organism'][0]['text']
        if 'sample derived from' not in sample['characteristics']:
            if organism in data_portal_samples:
                data_portal_samples[organism]['records'].append(
                    parse_record_data_portal(sample['characteristics'],
                                             sample['accession']))
                if organism in ORGANISMS:
                    data_portal_samples[organism]['assemblies'].extend(
                        parse_assemblies(sample['accession']))
                if len(data_portal_samples[organism]['assemblies']) > 0:
                    data_portal_samples[organism]['trackingSystem'] = \
                        'awaiting all data for annotation'
            else:
                abstract_sample = dict()
                abstract_sample['organism'] = sample['characteristics'][
                    'organism'][0]['text']
                abstract_sample['commonName'] = get_common_name(
                    abstract_sample['organism'])
                abstract_sample['records'] = list()
                abstract_sample['records'].append(
                    parse_record_data_portal(sample['characteristics'],
                                             sample['accession']))
                if organism in ORGANISMS:
                    abstract_sample['assemblies'] = parse_assemblies(
                        sample['accession'])
                else:
                    abstract_sample['assemblies'] = list()
                if len(abstract_sample['assemblies']) > 0:
                    abstract_sample[
                        'trackingSystem'] = 'awaiting all data for annotation'
                else:
                    abstract_sample[
                        'trackingSystem'] = 'Submitted to BioSamples'
                data_portal_samples[organism] = abstract_sample
            index = 'organisms_test'
        else:
            index = 'specimens_test'
        parse_record(sample['characteristics'], sample['accession'],
                     sample['taxId'], index, organisms_samples)
    for organism, record in data_portal_samples.items():
        es.index('data_portal_test', record, id=organism)
    for biosample_id, record in organisms_samples.items():
        es.index('organisms_test', record, id=biosample_id)


def parse_record_data_portal(sample, accession):
    record = dict()
    record['accession'] = accession
    record['organism'] = check_field_existence(sample, 'organism',
                                               ontology=True)
    if record['organism']['text']:
        record['commonName'] = get_common_name(record['organism']['text'])
    else:
        record['commonName'] = None
    record['sex'] = check_field_existence(sample, 'sex')
    record['organismPart'] = sample['organism part'][0]['text']
    if record['organism']['text'] in ORGANISMS and len(
            parse_assemblies(accession)) > 0:
        record['trackingSystem'] = 'awaiting all data for annotation'
    else:
        record['trackingSystem'] = 'Submitted to BioSamples'
    return record


def parse_record(sample, accession, taxon_id, index, organisms_samples):
    es = Elasticsearch(['elasticsearch:9200'])
    record = dict()
    # Mandatory fields
    record['accession'] = accession
    record['taxonId'] = taxon_id
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
    record['habitat'] = check_field_existence(sample, 'habitat')
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
    if index == 'organisms_test' and record['organism']['text'] in ORGANISMS \
            and len(parse_assemblies(accession)) > 0:
        record['trackingSystem'] = 'awaiting all data for annotation'
    else:
        record['trackingSystem'] = 'Submitted to BioSamples'
    record['etag'] = get_etag(record['accession'])

    # parse custom fields (those that are not in checklist)
    record['customFields'] = list()
    for k, v in sample.items():
        custom_field = parse_custom_fields(k, v)
        if custom_field:
            record['customFields'].append(custom_field)

    # Write data to ES
    if index == 'specimens_test':
        es.index(index, record, id=record['accession'])
        # Update related organism index
        if record['sampleDerivedFrom'] in organisms_samples:
            organisms_samples[record['sampleDerivedFrom']]['specimens'].append({
                'accession': record['accession'],
                'organism': record['organism']['text'],
                'commonName': record['commonName'],
                'sex': record['sex'],
                'organismPart': record['organismPart']
            })
        else:
            organisms_samples[record['sampleDerivedFrom']] = dict()
            organisms_samples[record['sampleDerivedFrom']]['specimens'] = [{
                'accession': record['accession'],
                'organism': record['organism']['text'],
                'commonName': record['commonName'],
                'sex': record['sex'],
                'organismPart': record['organismPart']
            }]
    else:
        if accession in organisms_samples:
            record['specimens'] = organisms_samples[accession]['specimens']
        else:
            record['specimens'] = list()
        organisms_samples[accession] = record


def parse_custom_fields(field_key, field_value):
    if field_key not in CHECKLIST_FIELDS:
        return {
            'name': field_key,
            'value': field_value[0]['text']
        }


def get_etag(biosamples_id):
    sample = requests.get(
        f"https://www.ebi.ac.uk/biosamples/samples/{biosamples_id}")
    return sample.headers['ETag']


def parse_assemblies(sample_id):
    assemblies = list()
    assemblies_data = requests.get(f"https://www.ebi.ac.uk/ena/portal/api/"
                                   f"links/sample?format=json"
                                   f"&accession={sample_id}&result=assembly"
                                   f"&offset=0&limit=1000")
    if assemblies_data.status_code != 200:
        return assemblies
    assemblies_data = assemblies_data.json()
    for assembly in assemblies_data:
        assemblies.append(assembly)
    return assemblies


if __name__ == "__main__":
    main()
