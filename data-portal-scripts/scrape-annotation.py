import scrapy
from scrapy.crawler import CrawlerProcess
 
class ScrapeTableSpider(scrapy.Spider):
    name = 'annotations'
    custom_settings = { 'DOWNLOD_DELAY': 1 }
    allowed_domains = ['https://projects.ensembl.org/darwin-tree-of-life']
    start_urls = ['https://projects.ensembl.org/darwin-tree-of-life']
    annotationsArray = list()
    
    def start_requests(self):
        urls = [
            'https://projects.ensembl.org/darwin-tree-of-life',
        ]
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)
 
    def parse(self, response):
        for row in response.xpath('//*[@class="table_zebra"]//tbody/tr'):
            yield {
                'species' : row.xpath('normalize-space(td[2]//text())').extract_first(),
                'accession': row.xpath('normalize-space(td[3]//text())').extract_first(),
                'annotation' : { 'GTF': row.xpath('normalize-space(td[4]/span/a[contains(text(),"GTF")]/@href)').extract_first(),'GFF3': row.xpath('normalize-space(td[4]/span/a[contains(text(),"GFF3")]/@href)').extract_first()},
                'proteins':{'FASTA':row.xpath('normalize-space(td[5]/a/@href)').extract_first()},
                'transcripts':{'FASTA':row.xpath('normalize-space(td[6]/a/@href)').extract_first()},
                'softmasked_genome':{'FASTA':row.xpath('normalize-space(td[7]/a/@href)').extract_first()},
                'repeat_library':{'FASTA':row.xpath('normalize-space(td[8]/a/@href)').extract_first()},
                'other_data':{'ftp_dumps':row.xpath('normalize-space(td[9]/a/@href)').extract_first()},
                'view_in_browser':row.xpath('normalize-space(td[10]/a/@href)').extract_first(),
            }

if __name__ == "__main__":
    process = CrawlerProcess(settings={ "FEEDS": {"annotations.json": {"format": "json"}}, "LOG_ENABLED": False})
    process.crawl(ScrapeTableSpider)
    process.start()