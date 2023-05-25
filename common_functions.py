import requests
from datetime import datetime
from constants import CHECKLIST_FIELDS


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
    if common_name_response.content.decode('utf-8') == "No results.":
        return None
    common_name_response = common_name_response.json()
    if 'commonName' in common_name_response[0]:
        return common_name_response[0]['commonName']
    else:
        return None


def get_date_and_time():
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    return dt_string


def get_samples(index_name, es):
    samples = dict()
    data = es.search(index=index_name, size=100000)
    for sample in data['hits']['hits']:
        samples[sample['_id']] = sample['_source']
    return samples


def parse_assemblies(sample_id):
    print(f"{get_date_and_time()}: parse assemblies for {sample_id}")
    assemblies_data = requests.get(f"https://www.ebi.ac.uk/ena/portal/api/"
                                   f"links/sample?format=json"
                                   f"&accession={sample_id}&result=assembly"
                                   f"&offset=0&limit=1000")
    if assemblies_data.status_code != 200:
        return list()
    else:
        return assemblies_data.json()


def get_reads(sample_id):
    print(f"{get_date_and_time()}: getting reads for {sample_id}")
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
                                        f'first_created')
    if experiments_data.status_code != 200:
        return list()
    else:
        return experiments_data.json()


def check_field_existence(sample, field_name, units=False, ontology=False):
    if units:
        if field_name in sample and 'unit' in sample[field_name][0]:
            return {
                'text': sample[field_name][0]['text'],
                'unit': sample[field_name][0]['unit']
            }
        elif field_name in sample and 'unit' not in sample[field_name][0]:
            return {
                'text': sample[field_name][0]['text'],
                # 'unit': sample[field_name][0]['unit']
            }
        else:
            return {
                'text': None,
                'unit': None
            }
    elif ontology:
        if field_name in sample and 'ontologyTerms' in sample[field_name][0]:
            return {
                'text': sample[field_name][0]['text'],
                'ontologyTerm': sample[field_name][0]['ontologyTerms'][0]
            }
        elif field_name in sample and 'ontologyTerms' not in sample[field_name][0]:
            return {
                'text': sample[field_name][0]['text'],
                # 'ontologyTerm': sample[field_name][0]['ontologyTerms'][0]
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


def get_etag(biosamples_id):
    sample = requests.get(
        f"https://www.ebi.ac.uk/biosamples/samples/{biosamples_id}")
    return sample.headers['ETag']


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
                                    f'first_created')
    if experiments_data.status_code != 200:
        return experiments
    experiments_data = experiments_data.json()
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
        tmp['instrument_platform'] = experiment['instrument_platform']
        tmp['instrument_model'] = experiment['instrument_model']
        tmp['library_layout'] = experiment['library_layout']
        tmp['library_strategy'] = experiment['library_strategy']
        tmp['library_source'] = experiment['library_source']
        tmp['library_selection'] = experiment['library_selection']
        tmp['first_public'] = experiment['first_public']
        experiments.append(tmp)
    return experiments


def parse_custom_fields(field_key, field_value):
    if field_key not in CHECKLIST_FIELDS:
        return {
            'name': field_key,
            'value': field_value[0]['text']
        }

