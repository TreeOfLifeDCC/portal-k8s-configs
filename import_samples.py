import requests

from elasticsearch import Elasticsearch

from common_functions import check_field_existence, get_date_and_time, \
    get_samples, parse_assemblies, get_reads
from constants import CHECKLIST_FIELDS

es = Elasticsearch(['elasticsearch:9200'])
new_data_portal_samples = list()
new_organisms_samples = list()
new_specimens_samples = dict()


def main():
    print(f"{get_date_and_time()}: starting import")
    # get BioSamples data
    samples = requests.get(
        "https://www.ebi.ac.uk/biosamples/samples?size=100000&"
        "filter=attr%3Aproject%20name%3ADTOL").json()
    # get existing data from Elasticsearch
    data_portal_samples = get_samples('data_portal_index', es)
    organisms_samples = get_samples('organisms_test', es)
    specimens_samples = get_samples('specimens_test', es)
    for sample in samples['_embedded']['samples']:
        if sample['accession'] in organisms_samples or sample['accession'] \
                in specimens_samples:
            continue
        print(f"{get_date_and_time()}: starting to import "
              f"{sample['accession']}")
        organism = sample['characteristics']['organism'][0]['text']
        # organisms path
        if 'sample derived from' not in sample['characteristics']:
            if organism in data_portal_samples:
                data_portal_samples[organism]['records'].append(
                    parse_record_data_portal(sample['characteristics'],
                                             sample['accession']))
                data_portal_samples[organism]['assemblies'].extend(
                    parse_assemblies(sample['accession']))
                if len(data_portal_samples[organism]['assemblies']) > 0:
                    data_portal_samples[organism]['trackingSystem'] = {
                        'rank': 2,
                        'status': 'Assemblies - Submitted'
                    }

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
                abstract_sample['assemblies'] = parse_assemblies(
                    sample['accession'])
                if len(abstract_sample['assemblies']) > 0:
                    abstract_sample[
                        'trackingSystem'] = {
                        'rank': 2, 'status': 'Assemblies - Submitted'}
                else:
                    abstract_sample[
                        'trackingSystem'] = {
                        'rank': 0, 'status': 'Submitted to BioSamples'}
                data_portal_samples[organism] = abstract_sample
            index = 'organisms_test'
            new_data_portal_samples.append(organism)
        else:
            # specimens path
            index = 'specimens_test'
        parse_record(sample['characteristics'], sample['accession'],
                     sample['taxId'], index, organisms_samples)
    print(f"{get_date_and_time()}: new organisms_test records: "
          f"{len(list(set(new_organisms_samples)))}")
    print(f"{get_date_and_time()}: new specimens_test records: "
          f"{len(list(set(new_specimens_samples)))}")
    for biosample_id, record in new_specimens_samples.items():
        if len(record['experiment']) > 0:
            organism = record['organism']['text']
            data_portal_samples[organism].setdefault('experiment', list())
            data_portal_samples[organism]['experiment'].append(
                record['experiment'])
            if data_portal_samples[organism]['trackingSystem']['status'] == \
                    'Submitted to BioSamples':
                data_portal_samples[organism]['trackingSystem'] = {
                    'rank': 1,
                    'status': 'Mapped Reads - Submitted'
                }
            new_data_portal_samples.append(organism)
    print(f"{get_date_and_time()}: new data_portal_index records: "
          f"{len(list(set(new_data_portal_samples)))}")

    if len(new_data_portal_samples) != 0:
        print(f"{get_date_and_time()}: indexing data_portal_index data")
        for organism, record in data_portal_samples.items():
            if organism in new_data_portal_samples:
                es.index('data_portal_index', record, id=organism)

    if len(new_organisms_samples) != 0:
        print(f"{get_date_and_time()}: indexing organisms_test data")
        for biosample_id, record in organisms_samples.items():
            if biosample_id in new_organisms_samples:
                es.index('organisms_test', record, id=biosample_id)

    if len(new_specimens_samples) != 0:
        print(f"{get_date_and_time()}: indexing specimens_test data")
        for biosample_id, record in new_specimens_samples.items():
            es.index('specimens_test', record, id=biosample_id)
    print(f"{get_date_and_time()}: finishing import")


def parse_record_data_portal(sample, accession):
    print(f"{get_date_and_time()}: creating abstract sample from "
          f"{accession} for data portal index")
    record = dict()
    record['accession'] = accession
    record['organism'] = check_field_existence(sample, 'organism',
                                               ontology=True)
    if record['organism']['text']:
        record['commonName'] = get_common_name(record['organism']['text'])
    else:
        record['commonName'] = None
    record['sex'] = check_field_existence(sample, 'sex')
    if 'organism part' in sample:
        record['organismPart'] = sample['organism part'][0]['text']
    else:
        record['organismPart'] = None
    if len(parse_assemblies(accession)) > 0:
        record['trackingSystem'] = 'Assemblies - Submitted'
    else:
        record['trackingSystem'] = 'Submitted to BioSamples'
    return record


def parse_record(sample, accession, taxon_id, index, organisms_samples):
    print(f"{get_date_and_time()}: starting to import {accession} to {index}")
    record = dict()
    # Mandatory fields
    record['accession'] = accession
    record['taxonId'] = taxon_id
    if 'organism part' in sample:
        record['organismPart'] = sample['organism part'][0]['text']
    else:
        record['organismPart'] = None
    record['lifestage'] = check_field_existence(sample, 'lifestage')
    record['projectName'] = check_field_existence(sample, 'project name')
    record['collectedBy'] = check_field_existence(sample, 'collected by')
    record['collectionDate'] = check_field_existence(sample, 'collection date')
    record['geographicLocationCountryAndOrSea'] = check_field_existence(
        sample, 'geographic location (country and/or sea)')
    record['geographicLocationLatitude'] = check_field_existence(
        sample, 'geographic location (latitude)', units=True)
    record['geographicLocationLongitude'] = check_field_existence(
        sample, 'geographic location (longitude)', units=True)
    record['geographicLocationRegionAndLocality'] = check_field_existence(
        sample, 'geographic location (region and locality)')
    record['identifiedBy'] = check_field_existence(sample, 'identified by')
    record['habitat'] = check_field_existence(sample, 'habitat')
    record['identifierAffiliation'] = check_field_existence(
        sample, 'identifier_affiliation')
    record['sex'] = check_field_existence(sample, 'sex')
    record['collectingInstitution'] = check_field_existence(
        sample, 'collecting institution')
    record['gal'] = check_field_existence(sample, 'GAL')
    record['specimenVoucher'] = check_field_existence(sample, 'specimen voucher')
    record['specimenId'] = check_field_existence(sample, 'specimen id')
    record['galSampleId'] = check_field_existence(sample, 'GAL_sample_id')
    record['organism'] = check_field_existence(sample, 'organism', ontology=True)
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
    if index == 'organisms_test':
        record['assemblies'] = parse_assemblies(accession)
        if len(record['assemblies']) > 0:
            record['trackingSystem'] = 'Assemblies - Submitted'
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
        record['experiment'] = get_reads(record['accession'])
        # es.index(index, record, id=record['accession'])
        new_specimens_samples[record['accession']] = record
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
        # add this organism to the list to be indexed
        new_organisms_samples.append(record['sampleDerivedFrom'])
    else:
        if accession in organisms_samples:
            record['specimens'] = organisms_samples[accession]['specimens']
        else:
            record['specimens'] = list()
        organisms_samples[accession] = record
        new_organisms_samples.append(accession)


def parse_custom_fields(field_key, field_value):
    if field_key not in CHECKLIST_FIELDS:
        return {
            'name': field_key,
            'value': field_value[0]['text']
        }


def get_etag(biosamples_id):
    print(f"{get_date_and_time()}: getting etag for {biosamples_id}")
    sample = requests.get(
        f"https://www.ebi.ac.uk/biosamples/samples/{biosamples_id}")
    return sample.headers['ETag']


def get_common_name(latin_name):
    print(f"{get_date_and_time()}: getting common name for {latin_name}")
    common_name_response = requests.get(
        f"https://www.ebi.ac.uk/ena/taxonomy/rest/scientific-name/{latin_name}")
    if common_name_response.content.decode('utf-8') == "No results.":
        return None
    common_name_response = common_name_response.json()
    if 'commonName' in common_name_response[0]:
        return common_name_response[0]['commonName']
    else:
        return None


def get_tax_id(organism_name):
    response = requests.get(
        f"https://www.ebi.ac.uk/ena/taxonomy/rest/scientific-name/"
        f"{organism_name}").json()
    return response[0]['taxId']


if __name__ == "__main__":
    main()

