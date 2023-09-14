from elasticsearch import Elasticsearch, AsyncElasticsearch
import requests
import os
from datetime import datetime

import aiohttp
import asyncio

import json
from common_functions import get_common_name, get_reads, check_field_existence, get_etag, parse_experiments, \
    parse_custom_fields, get_samples

ES_HOST = os.getenv('ES_CONNECTION_URL')
ES_USERNAME = os.getenv('ES_USERNAME')
ES_PASSWORD = os.getenv('ES_PASSWORD')


es = Elasticsearch(
    [ES_HOST],
    http_auth=(ES_USERNAME, ES_PASSWORD),
    scheme="https", port=443, )

new_specimens_samples = dict()
new_organism_samples = dict()
projectIds = []
biosamples = dict()
projects = [
    ['PRJNA489245', 'Bat1K Project']]
    # ['PRJNA720569', 'The California Conservation Genomics Project (CCGP)'],
    # ['PRJNA734913', 'Amphibalanus amphitrite(Genome Sequencing and assembly)']]
    # ['PRJDB6260', 'Elasmobranch shark genome evolution']]
    # ['PRJEB43510', 'ERGA']]

    # ['PRJEB40665', 'DToL']]
    # ['PRJNA163993', 'i5k initiative'],
    # ['PRJNA293101', 'Orestias ascotanensis Genome sequencing and assembly'],
    # ['PRJNA489243', 'Vertebrate Genomes Project'],
    # ['PRJNA512907', 'DNA Zoo'],
    # ['PRJNA682446',
    #  'Genome sequencing data and assemblies generated by the Lewin Lab @ UC Davis Genome Center.'],
    # ['PRJNA813333', 'Canadian BioGenome Project (CBP)'],
    # ['PRJEB51690', 'Anopheles Reference Genomes Project (Data and assemblies)'],
    # ['PRJNA312960', '200 Mammals'],
    # ['PRJNA634441', 'Monomorium pharaonis Genome sequencing and assembly'],
    # ['PRJNA649812', 'The Global Invertebrate Genomics Alliance (GIGA) genomes and transcriptomes'],
    # # ['PRJEB43743', 'ASG']]
    # # ['PRJNA844590', 'Illinois EBP Pilot']] #(no data)
    # ['PRJEB49670', 'Catalan Initiative for the Earth BioGenome Project (CBP)'],
    # ['PRJEB33226', '25 Genomes Project (Genome Data and Assemblies)']]
    # ['PRJNA545868', 'Bird 10000 Genomes (B10K) Project (Family phase)'],
    # ['PRJNA555319', 'USDA Agricultural Research Service’s Ag100Pest Initiative'],
    # ['PRJNA712951', 'ENDEMIXIT'],
    # ['PRJNA811786', 'African BioGenome Project (AfricaBP)'],
    # # ['PRJNA707235', 'University of California Consortium for the Earth BioGenome Project (Cal-EBP)']] (no data)
    # ['PRJNA707598', 'Squalomix (Genome sequencing and assembly of chondrichthyans)']]
    # ['PRJNA706690', 'CanSeq150 Project (Genome Data and Assemblies)'],
    # ['PRJNA706923', 'LOEWE Centre for Translational Biodiversity Genomics (LOEWE-TBG)'],
    # ['PRJNA785018', 'Genome sequencing and assembly of primate species Genome sequencing and assembly'],
    # # ['PRJNA911016', 'Cephalopachus bancanus breed not provided Genome sequencing and assembly']] (no data )
    # ['PRJEB65317', 'Earth BioGenome Project Norway (EBP-Nor)']]


async def get_response(session, study_accession, parent_study_accession, attempt=0):
    headers = {'Content-Type': 'application/x-www'
                               '-form-urlencoded'}
    data = 'result=study&query=study_accession=' + study_accession + ' OR parent_study_accession=' + parent_study_accession + '&fields=study_accession,parent_study_accession&format=json'

    url = 'https://www.ebi.ac.uk/ena/portal/api/search'

    async with session.post(url, data=data, headers=headers) as response:
        data = await response.text()
        result = json.loads(data)
        if result is not None and len(result) == 1:
            projectIds.append(result[0]['study_accession'])
        else:
            for record in result:
                # This never gets called, a coroutine is returned
                if record['study_accession'] != study_accession:
                    await get_response(session, record['study_accession'], record['study_accession'],
                                       attempt + 1)


def get_date_and_time():
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    return dt_string


async def main(projectNumber):
    async with aiohttp.ClientSession() as session:
        tasks = []
        task = asyncio.ensure_future(get_response(session, projectNumber, projectNumber))
        tasks.append(task)
        await asyncio.gather(*tasks, return_exceptions=True)


async def get_ena_data(session, project_id):
    # print(f"{project_id}: get ena data for project id")
    url = "https://www.ebi.ac.uk/ena/portal/api/search?fields=sample_accession&includeAccessions={" \
          "}&result=read_run&format=json".format(project_id)
    resp = await session.get(url)
    data = await resp.text()
    result = json.loads(data)
    async with aiohttp.ClientSession() as session:
        tasks = []
        for my_id in result:
            if 'sample_accession' in my_id:
                task = asyncio.ensure_future(get_bio_sample(session, my_id['sample_accession']))
                tasks.append(task)
        await asyncio.gather(*tasks, return_exceptions=True)


async def get_bio_sample(session, sample_accession):
    # print(f"{sample_accession}: get ena data for sample_accession")
    url = "https://www.ebi.ac.uk/biosamples/samples/{" \
          "}".format(sample_accession)
    resp = await session.get(url)
    data = await resp.text()
    result = json.loads(data)
    biosamples[sample_accession] = result


async def fetch_all_biosample_data(ids):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for my_id in ids:
            task = asyncio.ensure_future(get_ena_data(session, my_id))
            tasks.append(task)
        await asyncio.gather(*tasks, return_exceptions=True)


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

                    if data_portal_samples[organism]['project_name'] and data_portal_samples[organism][
                        'project_name'] != [None]:
                        if project_name not in data_portal_samples[organism]['project_name']:
                            data_portal_samples[organism]['project_name'].append(project_name)
                    else:
                        data_portal_samples[organism]['project_name'] = [project_name]

                    new_organism_samples[organism] = data_portal_samples[organism]
                else:
                    sample_to_submit = dict()
                    # Parse mandatory attributes
                    organism = sample['characteristics']['organism'][0]['text']
                    sample_to_submit['accession'] = sample['accession']
                    sample_to_submit['project_name'] = [project_name]
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
            print(len(new_organism_samples))


if __name__ == '__main__':
    print(f"{get_date_and_time()}: start time ")
    data_portal_samples = get_samples('data_portal', es)
    organisms_samples = dict()
    project_name = ''
    for project in projects:
        project_name = project[1]
        print(project_name)
    asyncio.get_event_loop().run_until_complete(main(project[0]))
    print(len(projectIds))
    print(f"{get_date_and_time()}: end time time ")
    asyncio.get_event_loop().run_until_complete(fetch_all_biosample_data(projectIds))
    print(len(biosamples))
    print(f"{get_date_and_time()}: end for bio sample time ")
    for _, sample in biosamples.items():
        parse_biosamples_data(sample, data_portal_samples, organisms_samples, project_name)
    print(f"{len(data_portal_samples)}: Already stored data count")
    for organism, record in data_portal_samples.items():
        # print(record['project_name'])
        # print(organism)
        es.index('data_portal', record, id=organism)
    for organism, record in new_organism_samples.items():
        # print(record['project_name'])
        es.index('data_portal', record, id=organism)

    for biosample_id, record in organisms_samples.items():
        es.index('organisms_test_index', record, id=biosample_id)
    print(f"{get_date_and_time()}: end for bio sample time ")
