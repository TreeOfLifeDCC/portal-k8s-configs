import scrapy
from scrapy.crawler import CrawlerProcess
import json
import os
from elasticsearch import Elasticsearch
from elasticsearch import RequestsHttpConnection
import requests

annotationsArray = list()

class ScrapeTableSpider(scrapy.Spider):
    name = 'annotations'
    custom_settings = { 'DOWNLOD_DELAY': 1 }
    allowed_domains = ['https://projects.ensembl.org/darwin-tree-of-life']
    start_urls = ['https://projects.ensembl.org/darwin-tree-of-life']
    
    def start_requests(self):
        urls = [
            'https://projects.ensembl.org/darwin-tree-of-life',
        ]
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)
 
    def parse(self, response):
        for row in response.xpath('//*[@class="table_zebra"]//tbody/tr'):
            rowDict = dict()
            rowDict['species'] = row.xpath('normalize-space(td[2]//text())').extract_first()
            rowDict['accession'] = row.xpath('normalize-space(td[3]//text())').extract_first()
            rowDict['annotation'] = { 'GTF': row.xpath('normalize-space(td[5]/span/a[contains(text(),"GTF")]/@href)').extract_first(),'GFF3': row.xpath('normalize-space(td[5]/span/a[contains(text(),"GFF3")]/@href)').extract_first()}
            rowDict['proteins'] = {'FASTA':row.xpath('normalize-space(td[6]/a/@href)').extract_first()}
            rowDict['transcripts'] = {'FASTA':row.xpath('normalize-space(td[7]/a/@href)').extract_first()}
            rowDict['softmasked_genome'] = {'FASTA':row.xpath('normalize-space(td[8]/a/@href)').extract_first()}
            rowDict['repeat_library'] = {'FASTA':row.xpath('normalize-space(td[9]/a/@href)').extract_first()}
            rowDict['other_data'] = {'ftp_dumps':row.xpath('normalize-space(td[10]/a/@href)').extract_first()}
            rowDict['view_in_browser'] = row.xpath('normalize-space(td[11]/a/@href)').extract_first()
            annotationsArray.append(rowDict)

class ImportAnnotations():
    headers = {'content-type': 'application/json'}
    query = '{"size": 50000,"query": {"match_all": {}}}'
    data_portal = requests.post("http://elasticcron:9200/data_portal/_search?pretty",data=query, headers=headers, verify=False, timeout=10000).json()
    es = Elasticsearch('http://elasticcron:9200', connection_class=RequestsHttpConnection,
                   use_ssl=False, verify_certs=False, timeout=10000)
    annotationsArrayClassObj = list()
    organisms = list()

    def read_file(self, filename):
        with open(filename, 'r') as file_content:
            annotations = json.load(file_content)
        return annotations
    
    def import_annotations(self, annotationsArrayObj):
        annotLocalObj = annotationsArrayObj
        for organism in self.data_portal['hits']['hits']:
            organism_id = organism['_id']
            organism = organism['_source']
            annotationsDict = list()
            for annot in annotLocalObj:
                if annot['species'] == organism_id:
                    annotationsDict.append(annot)
            if(len(annotationsDict)> 0):
                organism['annotation'] = annotationsDict
                organism['annotation_complete'] = 'Done'
                organism['trackingSystem'][5] = {'name': 'annotation_complete', 'status': 'Done', 'rank': 6}
                self.es.index('data_portal', organism, id=organism_id)
            
if __name__ == "__main__":
    process = CrawlerProcess(settings={"LOG_ENABLED": False})
    process.crawl(ScrapeTableSpider)
    process.start()
    annotationsArrayObj = annotationsArray
    importAnnotations = ImportAnnotations()
    importAnnotations.import_annotations(annotationsArrayObj)
    annotationsArray = list()