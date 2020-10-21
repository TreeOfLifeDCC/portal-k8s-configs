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
    # TODO: parse mandatory attributes (this method)
    # TODO: parse customField
    parse_custom_fields(sample)
    # TODO: parse experiment
    parse_experiments(sample)
    # TODO: parse relationships
    parse_relationships(sample)
    # TODO: parse sex (this method)
    # TODO: check tracking system status
    get_tracking_status(sample)
    print(sample)


def parse_custom_fields(sample):
    pass


def parse_experiments(sample):
    pass


def parse_relationships(sample):
    pass


def get_tracking_status(sample):
    pass


if __name__ == "__main__":
    main()
