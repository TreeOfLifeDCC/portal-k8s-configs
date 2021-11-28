import json
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.http import Request
from elasticsearch import Elasticsearch
import requests


class ScrapeTableSpider(scrapy.Spider):
    prjList = list()
    projectIds = list()
    aggregationsResp = dict()
    name = 'genome-notes'
    custom_settings = { 'DOWNLOD_DELAY': 1 }
    allowed_domains = ['wellcomeopenresearch.org', 'doi.org']
    start_urls = ['https://wellcomeopenresearch.org/gateways/treeoflife']
    headers = {'content-type': 'application/json'}
    es = Elasticsearch(hosts=["45.86.170.227:80/elasticsearch"])
    aggregationsQuery = '{ "size":0, "aggregations": {"experiment": {"nested": {"path": "experiment"},"aggs": {"accession": {"terms": {"field": "experiment.study_accession","size": 20000}}}}}}'
    
    def get_prj_from_es(self):
        aggregationsResp = requests.post("http://45.86.170.227/elasticsearch/data_portal_index/_search?pretty",data=self.aggregationsQuery, headers=self.headers).json()
        self.projectIds = aggregationsResp['aggregations']['experiment']['accession']['buckets']
        with open('ESPrjList.json', 'w') as f:
            f.write(json.dumps(self.projectIds))
        f.close()
    
    def start_requests(self):
        urls = [
            'https://wellcomeopenresearch.org/gateways/treeoflife',
        ]
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)
 
    def parse(self, response):
        articleUriArray = list()
        self.get_prj_from_es()
        notes = response.css('div.article-browse-wrapper')
        for row in notes:
            articleURI = "https://doi.org/" + row.css('div::attr(data-article-doi)').extract_first()
            articleUriArray.append(articleURI)
        for article in articleUriArray:
            yield scrapy.Request(url=article, callback=self.check_if_prj_exists)

    
    def check_if_prj_exists(self, response):
        respPrjId = response.xpath("//*[contains(text(), 'PRJE')]//text()").extract_first()
        if respPrjId != None:
            for prj in self.projectIds:
                if prj['key'] == respPrjId:
                    print(prj, respPrjId)
                    self.write_prj_to_file(response, respPrjId)
            
    def write_prj_to_file(response, respPrjId):
        prjArticleArray = list()
        prjArticleMap = dict()
        prjArticleMap['id'] = respPrjId
        prjArticleMap['url'] = response.url
        prjArticleArray.append(prjArticleMap)
        yield prjArticleMap
        
if __name__ == "__main__":
    process = CrawlerProcess(settings={ "FEEDS": {"genome-prj.json": {"format": "json"}}, "LOG_ENABLED": False})
    process.crawl(ScrapeTableSpider)
    process.start()