from typing import List
import requests
import subprocess
from lxml import etree
from elasticsearch import Elasticsearch
import json
import scrapy
from scrapy.crawler import CrawlerProcess
import re


 
class ScrapeTableSpider(scrapy.Spider):
    name = 'annotations'
    custom_settings = { 'DOWNLOD_DELAY': 1 }
    allowed_domains = ['https://projects.ensembl.org/darwin-tree-of-life']
    start_urls = ['https://projects.ensembl.org/darwin-tree-of-life']
    annotationsArray = list()
    es = Elasticsearch(hosts=["45.88.81.118:80/elasticsearch"])
    data_portal = es.search(index='data_portal', size=10000)
    codes = dict()
    tolidArrayList = list()
    
    codes['m'] = 'mammals'
    codes['d'] = 'dicots'
    codes['i'] = 'insects'
    codes['u'] = 'algae'
    codes['p'] = 'protists'
    codes['x'] = 'molluscs'
    codes['t'] = 'other-animal-phyla'
    codes['q'] = 'arthropods'
    codes['k'] = 'chordates'
    codes['f'] = 'fish'
    codes['a'] = 'amphibians'
    codes['b'] = 'birds'
    codes['e'] = 'echinoderms'
    codes['w'] = 'annelids'
    codes['j'] = 'jellyfish'
    codes['h'] = 'platyhelminths'
    codes['n'] = 'nematodes'
    codes['v'] = 'vascular-plants'
    codes['l'] = 'monocots'
    codes['c'] = 'non-vascular-plants'
    codes['g'] = 'fungi'
    codes['o'] = 'sponges'
    codes['r'] = 'reptiles'
    codes['s'] = 'sharks'
    codes['y'] = 'bacteria'
    codes['z'] = 'archea'
    
    def getTolList(self):
        for org in self.data_portal['hits']['hits']:
            tolObj = dict()
            organism_id = org["_id"]
            organism = org['_source']
            organismName = organism_id.replace(' ','_');
            tolid = organism['tolid']
            tolid_link = ''
            if(tolid != None):
                clade = self.codes[tolid[0]];
                tolid_link = 'https://tolqc.cog.sanger.ac.uk/darwin/'+clade+'/'+organismName;
                
            tolObj['tolid'] = tolid
            tolObj['organism'] = organism_id
            tolObj['url'] = tolid_link
            self.tolidArrayList.append(tolObj)

        return self.tolidArrayList
    
    def start_requests(self):
        for obj in self.tolidArrayList:
            if(obj['url']):
                yield scrapy.Request(url=obj['url'], callback=self.parse)
            break
 
    def parse(self, response):
        data = response.url, re.findall("var gscope =(.+?);\n", response.body.decode("utf-8"), re.S)
        spectraList = list()
        for row in data[0]:
            spectraObj = dict()
            spectraObj['source'] = row['type'],
            spectraObj['specimen'] = row['specimen'],
            spectraObj['k-mer'] = row['k'],
            spectraObj['k-cov'] = row['kcov'],
            spectraObj['haploid'] = row['max']['len'],
            spectraObj['repeat'] = row['type'],
            spectraObj['het'] = row['type'],
            spectraObj['fit'] = row['type'],
            spectraObj['error'] = row['type'],
            spectraObj['plot'] = list()
            plotObj = dict()
            plotObj['img'] = col.xpath('normalize-space(td[9]/a/@href)').extract()
            spectraList.append(spectraList)
            print(spectraList, col.xpath('normalize-space(td[9]/a/@href)').extract())

if __name__ == "__main__":
    tolidArrayList = ScrapeTableSpider().getTolList()
    process = CrawlerProcess(settings={ "FEEDS": {"tol.json": {"format": "json"}}, "LOG_ENABLED": False})
    process.crawl(ScrapeTableSpider)
    process.start()