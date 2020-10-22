import requests
import json
from lxml import etree
from elasticsearch import Elasticsearch

es = Elasticsearch(['elasticsearch:9200'])


def main():
    root_project = requests.get(
        'https://www.ebi.ac.uk/ena/browser/api/xml/PRJEB40665?download=true')
    root_xml = root = etree.fromstring(root_project.content)
    primary_related_projects = parse_related_projects(root_xml)
    secondary_related_projects = list()
    for project in primary_related_projects:
        secondary_root_project = requests.get(
            f'https://www.ebi.ac.uk/ena/browser/api/xml/'
            f'{project}?download=true')
        secondary_root_xml = etree.fromstring(secondary_root_project.content)
        secondary_related_projects.extend(parse_related_projects(
            secondary_root_xml))
    source_primary_accessions = parse_source_primary_accessions(
        secondary_related_projects)
    biosamples = parse_biosamples(source_primary_accessions)
    for _, sample in biosamples.items():
        parse_biosamples_data(sample)
        break


def parse_related_projects(root_xml):
    related_projects = list()
    for project in root_xml[0][5]:
        if project[0].tag == 'CHILD_PROJECT':
            related_projects.append(project[0].attrib['accession'])
    return related_projects


def parse_source_primary_accessions(related_projects):
    source_primary_accessions = list()
    for project in related_projects:
        results = requests.get(
            f'https://www.ebi.ac.uk/ena/xref/rest/json/search?accession='
            f'{project}&expanded=true')
        if len(results.json()) > 0:
            source_primary_accessions.append(
                results.json()[0]['Source Primary Accession'])
    return source_primary_accessions


def parse_biosamples(primary_accessions):
    biosamples = dict()
    for acc in primary_accessions:
        results = requests.get(
            f"https://www.ebi.ac.uk/ena/browser/api/summary/"
            f"{acc}?offset=0&limit=100")
        biosample_id = results.json()['summaries'][0]['sample']
        if biosample_id not in biosamples:
            biosamples[biosample_id] = requests.get(
                f'https://www.ebi.ac.uk/biosamples/samples/{biosample_id}'
            ).json()
    return biosamples


def parse_biosamples_data(sample):
    sample_to_submit = dict()
    # Parse mandatory attributes
    sample_to_submit['accession'] = sample['accession']
    sample_to_submit['commonName'] = check_field_existence(
        sample['characteristics'], 'common name')
    sample_to_submit['organism'] = check_field_existence(
        sample['characteristics'], 'organism')
    sample_to_submit['scientificName'] = sample['name']
    sample_to_submit['taxonId'] = sample['taxId']
    if 'sex' in sample['characteristics']:
        sample_to_submit['sex'] = sample['characteristics']['sex']
    else:
        sample_to_submit['sex'] = list()

    # parse customField
    sample_to_submit['customField'] = parse_custom_fields(
        sample['characteristics'])

    # parse experiment
    sample_to_submit['experiment'] = parse_experiments(sample['accession'])

    # parse relationships
    sample_to_submit['relationship'] = sample['relationships']

    # TODO: check tracking system status
    sample_to_submit['trackingSystem'] = get_tracking_status(sample)
    print(json.dumps(sample_to_submit))


def check_field_existence(data, field_name):
    if field_name in data:
        return data[field_name][0]['text']
    else:
        return None


def parse_custom_fields(sample):
    custom_fields = list()
    for k, v in sample.items():
        tmp = dict()
        if k not in ['common name', 'organism', 'sex']:
            # TODO: add units
            tmp['name'] = k
            tmp['value'] = v[0]['text']
            if 'ontologyTerms' in v[0]:
                tmp['ontologyTerms'] = v[0]['ontologyTerms']
        # only add dict if it's not empty
        if len(tmp.keys()) > 0:
            custom_fields.append(tmp)
    return custom_fields


def parse_experiments(sample_id):
    experiments = list()
    experiments_data = requests.get(f'https://www.ebi.ac.uk/ena/portal/'
                                        f'api/filereport?result=read_run'
                                        f'&accession={sample_id}'
                                        f'&offset=0&limit=1000&format=json'
                                        f'&fields=study_accession,'
                                        f'secondary_study_accession,'
                                        f'sample_accession,'
                                        f'secondary_sample_accession,'
                                        f'experiment_accession,run_accession,'
                                        f'submission_accession,tax_id,'
                                        f'scientific_name,instrument_platform,'
                                        f'instrument_model,library_name,'
                                        f'nominal_length,library_layout,'
                                        f'library_strategy,library_source,'
                                        f'library_selection,read_count,'
                                        f'base_count,center_name,first_public,'
                                        f'last_updated,experiment_title,'
                                        f'study_title,study_alias,'
                                        f'experiment_alias,run_alias,'
                                        f'fastq_bytes,fastq_md5,fastq_ftp,'
                                        f'fastq_aspera,fastq_galaxy,'
                                        f'submitted_bytes,submitted_md5,'
                                        f'submitted_ftp,submitted_aspera,'
                                        f'submitted_galaxy,submitted_format,'
                                        f'sra_bytes,sra_md5,sra_ftp,sra_aspera,'
                                        f'sra_galaxy,cram_index_ftp,'
                                        f'cram_index_aspera,cram_index_galaxy,'
                                        f'sample_alias,broker_name,'
                                        f'sample_title,nominal_sdev,'
                                        f'first_created').json()
    for experiment in experiments_data:
        tmp = dict()
        tmp['experiment_accession'] = experiment['experiment_accession']
        tmp['fastq_ftp'] = [file for file in experiment['fastq_ftp'].split(";")]
        tmp['run_accession'] = experiment['run_accession']
        tmp['scientific_name'] = experiment['scientific_name']
        tmp['sra_ftp'] = [file for file in experiment['sra_ftp'].split(";")]
        tmp['study_accession'] = experiment['study_accession']
        tmp['submitted_ftp'] = [
            file for file in experiment['submitted_ftp'].split(";")]
        tmp['tax_id'] = experiment['tax_id']
        experiments.append(tmp)
    return experiments


def get_tracking_status(sample):
    return 'In Progress'


if __name__ == "__main__":
    main()
