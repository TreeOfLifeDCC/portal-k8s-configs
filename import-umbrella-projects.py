from elasticsearch import Elasticsearch
import requests
from common_functions import get_common_name, get_reads, check_field_existence, get_etag, parse_experiments, \
    parse_custom_fields
from constants import projects
import multiprocessing

es = Elasticsearch(
    ['https://prj-ext-prod-planet-bio-dr.es.europe-west2.gcp.elastic-cloud.com'],
    http_auth=('elastic', 'LYbx3h2EIz8COQIHEZ3oQxHo'),
    scheme="https", port=443, )

new_specimens_samples = dict()
projectIds = []


def main():
    for project in projects:
        if project[0] not in ['PRJEB40665', 'PRJEB43510', 'PRJEB43743']:
            source_primary_accessions = get_parent_and_child_projects(project[0], project[0])
            print(f"{len(source_primary_accessions)}: child Projects count")
            biosamples = parse_biosamples(source_primary_accessions)
            print(len(biosamples))
            data_portal_samples = dict()
            organisms_samples = dict()
            # for _, sample in biosamples.items():
            #     parse_biosamples_data(sample, data_portal_samples, organisms_samples, project[1])

            cpus = multiprocessing.cpu_count()
            pool = multiprocessing.Pool(cpus if cpus < 8 else 10)
            for _, sample in biosamples.items():
                parse_biosamples_data(sample, data_portal_samples, organisms_samples, project[1])
                pool.apply_async(parse_biosamples_data,
                                 args=(sample, data_portal_samples, organisms_samples, project[1]))
            pool.close()
            pool.join()

def get_parent_and_child_projects(study_accession, parent_study_accession):
    result = requests.post('https://www.ebi.ac.uk/ena/portal/api/search',
                           data='result=study&query=study_accession=' + study_accession + ' OR parent_study_accession='
                                + parent_study_accession + '&fields=study_accession,parent_study_accession&format=json',
                           headers={'Content-Type': 'application/x-www'
                                                    '-form-urlencoded'}).json()
    if result is not None and len(result) == 1:
        projectIds.append(result[0]['study_accession'])
    else:
        for record in result:
            if record['study_accession'] not in ['PRJEB40665', 'PRJEB43510', 'PRJEB43743'] and record[
                'study_accession'] != study_accession:
                get_parent_and_child_projects(record['study_accession'], record['study_accession'])
    return projectIds


def parse_biosamples(primary_accessions):
    biosamples = dict()
    for acc in primary_accessions:
        data = get_ena_data(acc)
        print(f"{len(data)}: Ena Data Length ")
        for ena_data_record in data:
            sample_id = ena_data_record['sample_accession']
            if sample_id is not None and sample_id != "":
                biosamples[sample_id] = requests.get(
                    f'https://www.ebi.ac.uk/biosamples/samples/{sample_id}'
                ).json()
    return biosamples


def get_ena_data(project_id):
    print(f"{project_id}: get ena data for project id")
    return requests.get(
        'https://www.ebi.ac.uk/ena/portal/api/filereport?result=read_run&accession=' + project_id + '&limit=1000'
                                                                                                    '&format=json'
                                                                                                    '&fields'
                                                                                                    '=sample_accession').json()


def parse_biosamples_data(sample, data_portal_samples=None, organisms_samples=None, project_name=None):
    if "_embedded" in sample and sample['_embedded']['samples'] is not None and len(sample['_embedded']['samples']) > 0:
        for sampleObje in sample['_embedded']['samples']:
            parse_biosamples_data(sampleObje, data_portal_samples, organisms_samples)
    else:
        if 'organism' in sample['characteristics']:
            organism = sample['characteristics']['organism'][0]['text']
            if 'sample derived from' not in sample['characteristics']:
                if organism in data_portal_samples:

                    data_portal_samples[organism]['assemblies'] = parse_assemblies(sample['accession'])
                    data_portal_samples[organism]['records'].append(
                        parse_record_data_portal(sample['characteristics'],
                                                 sample['accession']))
                    data_portal_samples[organism]['project_name'] = project_name
                else:
                    sample_to_submit = dict()
                    # Parse mandatory attributes
                    organism = sample['characteristics']['organism'][0]['text']
                    sample_to_submit['accession'] = sample['accession']
                    sample_to_submit['project_name'] = project_name
                    sample_to_submit['commonName'] = check_field_existence(
                        sample['characteristics'], 'common name')
                    sample_to_submit['scientificName'] = sample['name']
                    sample_to_submit['taxonId'] = sample['taxId']
                    if 'sex' in sample['characteristics']:
                        sample_to_submit['sex'] = sample['characteristics']['sex']
                    else:
                        sample_to_submit['sex'] = list()

                    if 'organism part' in sample:
                        sample_to_submit['organismPart'] = sample['organism part'][0]['text']
                    else:
                        sample_to_submit['organismPart'] = None
                    sample_to_submit['lifestage'] = check_field_existence(sample['characteristics'], 'lifestage')
                    sample_to_submit['projectName'] = check_field_existence(sample['characteristics'], 'project name')
                    sample_to_submit['collectedBy'] = check_field_existence(sample['characteristics'], 'collected by')
                    sample_to_submit['collectionDate'] = check_field_existence(sample, 'collection date')
                    sample_to_submit['geographicLocationCountryAndOrSea'] = check_field_existence(
                        sample['characteristics'], 'geographic location (country and/or sea)', units=True)
                    sample_to_submit['geographicLocationLatitude'] = check_field_existence(
                        sample['characteristics'], 'geographic location (latitude)', units=True)
                    sample_to_submit['geographicLocationLongitude'] = check_field_existence(
                        sample['characteristics'], 'geographic location (longitude)', units=True)
                    sample_to_submit['geographicLocationRegionAndLocality'] = check_field_existence(
                        sample['characteristics'], 'geographic location (region and locality)', units=True)
                    sample_to_submit['identifiedBy'] = check_field_existence(sample['characteristics'], 'identified by')
                    sample_to_submit['habitat'] = check_field_existence(sample['characteristics'], 'habitat')
                    sample_to_submit['identifierAffiliation'] = check_field_existence(
                        sample['characteristics'], 'identifier_affiliation')
                    sample_to_submit['sex'] = check_field_existence(sample['characteristics'], 'sex')
                    sample_to_submit['collectingInstitution'] = check_field_existence(
                        sample['characteristics'], 'collecting institution')
                    sample_to_submit['gal'] = check_field_existence(sample['characteristics'], 'GAL')
                    sample_to_submit['specimenVoucher'] = check_field_existence(sample['characteristics'],
                                                                                'specimen voucher')
                    sample_to_submit['specimenId'] = check_field_existence(sample['characteristics'], 'specimen id')
                    sample_to_submit['galSampleId'] = check_field_existence(sample['characteristics'], 'GAL_sample_id')
                    sample_to_submit['organism'] = check_field_existence(sample['characteristics'], 'organism',
                                                                         ontology=True)
                    if sample_to_submit['organism']['text']:
                        sample_to_submit['commonName'] = get_common_name(sample_to_submit['organism']['text'])
                    else:
                        sample_to_submit['commonName'] = None

                    # Optional fields
                    sample_to_submit['geographicLocationDepth'] = check_field_existence(
                        sample['characteristics'], 'geographic location (depth)', units=True)
                    sample_to_submit['geographicLocationElevation'] = check_field_existence(
                        sample['characteristics'], 'geographic location (elevation)', units=True)
                    sample_to_submit['sampleDerivedFrom'] = check_field_existence(
                        sample['characteristics'], 'sample derived from')
                    sample_to_submit['relationship'] = check_field_existence(sample['characteristics'], 'relationship')
                    sample_to_submit['cultureOrStrainId'] = check_field_existence(
                        sample['characteristics'], 'culture or strain id')

                    sample_to_submit['etag'] = get_etag(sample_to_submit['accession'])

                    # Write data to ES
                    # sample_to_submit['releaseDate'] = sample['releaseDate']
                    sample_to_submit['records'] = list()
                    sample_to_submit['records'].append(
                        parse_record_data_portal(sample['characteristics'],
                                                 sample['accession']))
                    # parse experiment
                    sample_to_submit['experiment'] = parse_experiments(sample['accession'])

                    # parse assemblies
                    sample_to_submit['assemblies'] = parse_assemblies(sample['accession'])

                    if len(sample_to_submit['assemblies']) > 0:
                        sample_to_submit['currentStatus'] = 'Assemblies - Submitted'
                    else:
                        sample_to_submit['currentStatus'] = 'Submitted to BioSamples'
                    if len(sample_to_submit['assemblies']) > 0:
                        sample_to_submit['trackingSystem'] = 'Assemblies - Submitted'
                    else:
                        sample_to_submit['trackingSystem'] = 'Submitted to  BioSamples'

                    if 'tax_id' not in sample and 'ontologyTerm' in sample_to_submit['records'][0]['organism']:
                        sample_to_submit['tax_id'] = \
                            sample_to_submit['records'][0]['organism']['ontologyTerm'].split("/")[-1].split("_")[-1]

                    parse_record(sample['characteristics'], sample['accession'],
                                 sample['taxId'], 'specimens_test_index', organisms_samples)

                    get_tracking_status(sample_to_submit)
                    sample_to_submit['organism'] = sample_to_submit['organism']['text']
                    data_portal_samples[organism] = sample_to_submit
                index = 'organisms_test_index'
            else:
                index = 'specimens_test_index'
            parse_record(sample['characteristics'], sample['accession'],
                         sample['taxId'], index, organisms_samples)
            for organism, record in data_portal_samples.items():
                es.index('data_portal_index', record, id=organism)
            for biosample_id, record in organisms_samples.items():
                es.index('organisms_test_index', record, id=biosample_id)


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


def get_tracking_status(sample):
    if 'experiment' in sample and len(sample['experiment']) > 0:
        mapped_reads = 'Done'
        raw_data = 'Done'
    else:
        mapped_reads = 'Waiting'
        raw_data = 'Waiting'
    if 'assemblies' in sample and len(sample['assemblies']) > 0:
        assemblies = 'Done'
    else:
        assemblies = 'Waiting'
    if sample['currentStatus'] == 'Annotation Complete':
        annotation_complete = 'Done'
    else:
        annotation_complete = 'Waiting'
    sample['trackingSystem'] = [
        {'name': 'biosamples', 'status': 'Done', 'rank': 1},
        {'name': 'mapped_reads', 'status': mapped_reads, 'rank': 2},
        {'name': 'assemblies', 'status': assemblies, 'rank': 3},
        {'name': 'raw_data', 'status': raw_data, 'rank': 4},
        {'name': 'annotation', 'status': 'Waiting', 'rank': 5},
        {'name': 'annotation_complete', 'status': annotation_complete, 'rank': 6}
    ]
    for status in sample['trackingSystem']:
        if status['name'] == 'assemblies':
            sample['assemblies_status'] = status['status']
        elif status['name'] == 'annotation':
            sample['annotation_status'] = status['status']
        else:
            sample[status['name']] = status['status']


def parse_record_data_portal(sample, accession):
    print(" creating abstract sample from "
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
    if index == 'organisms_test_index':
        record['assemblies'] = parse_assemblies(accession)
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
    if index == 'specimens_test_index':
        record['experiment'] = get_reads(record['accession'])
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


if __name__ == "__main__":
    main()
