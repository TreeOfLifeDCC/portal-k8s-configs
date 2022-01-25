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
    es = Elasticsearch(hosts=["45.88.81.118:80/elasticsearch"])
    aggregationsQuery = '{ "size":0, "aggregations": {"experiment": {"nested": {"path": "experiment"},"aggs": {"accession": {"terms": {"field": "experiment.study_accession","size": 20000}}}}}}'
    figureURI  = '';
    figureImgURI = '';
    figureImgAlt = '';
    caption = '';
    description = '';
    artTitle = '';
    abstract = '';
    prj = ''
            
    def get_prj_from_es(self):
        aggregationsResp = requests.post("http://45.88.81.118/elasticsearch/data_portal/_search?pretty",data=self.aggregationsQuery, headers=self.headers).json()
        self.projectIds = aggregationsResp['aggregations']['experiment']['accession']['buckets']
        with open('ESPrjList.json', 'w') as f:
            f.write(json.dumps(self.projectIds))
        f.close()
    
    def start_requests(self):
        urls = [
            'https://wellcomeopenresearch.org/gateways/treeoflife',
            'https://wellcomeopenresearch.org/gateways/treeoflife?&show=20&page=2',
            'https://wellcomeopenresearch.org/gateways/treeoflife?&show=20&page=3',
            'https://wellcomeopenresearch.org/gateways/treeoflife?&show=20&page=4'
        ]
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)
 
    def parse(self, response):
        articleUriArray = list()
        notes = response.css('div.article-browse-wrapper')
        count=0
        for row in notes:
            articleURI = "https://doi.org/" + row.css('div::attr(data-article-doi)').extract_first()
            articleUriArray.append(articleURI)
        for article in articleUriArray:
            yield scrapy.Request(url=article, callback=self.check_if_prj_exists)

    
    def check_if_prj_exists(self, response):
        res = response
        respPrjId = response.xpath("//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'accession number')]/a/@href").extract_first()
        # respPrjId = response.xpath("//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'accession number')]//p/text()").extract()
        # respPrjId = response.xpath("//*[contains(text(), 'PRJ')]//text()").extract_first()
        # self.prj = respPrjId
        prjArray = respPrjId.split("/")
        prjLen = 0
        if ((prjArray[len(prjArray) - 1]) != ''):
            self.prj = prjArray[len(prjArray) - 1]
        else:
            self.prj = prjArray[len(prjArray) - 2]
        if('ena.embl:' in self.prj):
            obj = self.prj.split(":")
            self.prj = obj[1]
        if ('PRJ' not in self.prj):
            temp = response.xpath("//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'accession number')]/a/text()").extract_first()
            if('PRJ' not in temp):
                respPrjId = response.xpath("//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'accession number')]/p/text()").extract_first()
                respPrjId = respPrjId.split(" ")
                if("PRJ" in respPrjId[len(respPrjId) -1]):
                    self.prj = respPrjId[len(respPrjId) -1]
                else:
                    self.prj = respPrjId[len(respPrjId) -2]
                    if(':' in self.prj):
                        tmp = self.prj.split(':')
                        self.prj = tmp[0]
            else:
                self.prj = temp
                    
        if self.prj != None:
            self.figureURI = res.css("div.fig.panel a::attr(href)").extract_first();
            self.figureImgURI = res.css("div.fig.panel a img::attr(src)").extract_first()
            self.figureImgAlt = res.css("div.fig.panel a img::attr(alt)").extract_first()
            
            titleArrayLength = len(res.css("h1.js-article-title::text").extract())
            self.artTitle = res.css("h1.js-article-title::text").extract()[0].strip()
            self.artTitle = self.artTitle + " "+res.css("h1.js-article-title i::text").extract()[0].strip()
            self.artTitle = self.artTitle + " "+res.css("h1.js-article-title::text").extract()[titleArrayLength-1].strip()
            
            absArrayLength = len(res.css("div.abstract-text::text").extract())
            abstract = res.css("div.abstract-text::text").extract()
            abs = res.css("div.abstract-text i::text").extract()
            for x in range(absArrayLength):
                if (x == 0):
                    self.abstract = abstract[0] + " " +abs[0].strip()
                else:
                    self.abstract = self.abstract + " " +abstract[x].strip()
            
            captionArray = res.css("div.fig.panel div.caption h3::text").extract()
            captionArrayItalic = res.css("div.fig.panel div.caption h3 i::text").extract()
                    
            self.caption = captionArray[0] + captionArrayItalic[0].strip();
            if("Figure 2" not in captionArray[1]):
                self.caption =self.caption + " " +captionArray[1].strip();
            if("Figure 2" not in captionArray[2]):
                self.caption =self.caption + " " +captionArray[2].strip();
                
            citeURL = res.xpath("//div[@class='article-information']/span[@data-test-id='box-latest-published']/a/text()").extract_first();
            prjArticleArray = list()
            prjArticleMap = dict()
            prjArticleMap['id'] = self.prj
            prjArticleMap['title'] = self.artTitle
            prjArticleMap['abstract'] = self.abstract
            prjArticleMap['url'] = response.url
            prjArticleMap['figureURI'] = self.figureURI
            prjArticleMap['caption'] = self.caption
            prjArticleMap['citeURL'] = citeURL
            prjArticleArray.append(prjArticleMap)
            yield prjArticleMap
            
    def write_prj_to_file(response, respPrjId):
        prjArticleArray = list()
        prjArticleMap = dict()
        prjArticleMap['id'] = respPrjId
        prjArticleMap['url'] = response.url
        prjArticleArray.append(prjArticleMap)
        yield prjArticleMap
        
if __name__ == "__main__":
    process = CrawlerProcess(settings={ "FEEDS": {"genome-notes.json": {"format": "json"}}, "LOG_ENABLED": False})
    process.crawl(ScrapeTableSpider)
    process.start()