import scrapy
from scrapy.crawler import CrawlerProcess
from elasticsearch import Elasticsearch
from elasticsearch import RequestsHttpConnection
import requests
import re
import urllib
import ssl
from bs4 import BeautifulSoup
from lxml import etree

notes = list()

class GetGenomeNotes():
    def start(self):
        headerWithJWT = dict()
        articleVersionIds = list()
        treeOfLifeArticlesList = list()
        
        headers = {'content-type': 'application/json'}
        jwt = requests.get("https://wellcomeopenresearch.org/api/token", headers=headers, timeout=10000).json()
        headerWithJWT['f1000-authbearer'] = jwt['token']
        headerWithJWT['content-type'] = 'application/json'
        treeOfLifeArticlesRequest = requests.get("https://gateway.f1000.com/gateway/231?details=true", headers=headerWithJWT, timeout=10000).json()
        treeOfLifeArticleIds = treeOfLifeArticlesRequest['members'][0]['ids']
        for id in treeOfLifeArticleIds:
            articleVersionRequestURI = 'https://article.f1000.com/articles?id='+str(id)+'&publishedOnly=true'
            articleVersionRequestURI = articleVersionRequestURI+'&publishedOnly=true'
            articleVersionRequest = requests.get(articleVersionRequestURI, headers=headerWithJWT, timeout=10000).json()
            articleVersionIds.append(articleVersionRequest[0]['versionIds'][0])

        count = 0
        for id in articleVersionIds:
            count = count + 1
            if count == 1:
                articleRequestWithVersionURI = 'https://article.f1000.com/versions?id='+str(id)
            else:
                articleRequestWithVersionURI = articleRequestWithVersionURI + '&id='+str(id)
        articleRequestWithVersionURI = articleRequestWithVersionURI + '&publishedOnly=true'
        treeOfLifeArticlesList = requests.get(articleRequestWithVersionURI, headers=headerWithJWT, timeout=10000).json()
        
        for article in treeOfLifeArticlesList:
            genNote = dict()
            url = article["htmlUrl"]
            url = url.replace(" ", "%20")
            context = ssl._create_unverified_context()
            html = urllib.request.urlopen(url, context=context).read()
            soup = BeautifulSoup(html,'html.parser')
        
            figureTag=soup.find_all('a', href=re.compile('figure1.gif'))
            if(len(figureTag) > 0):
                figureUri = figureTag[0]['href']
            else:
                figureUri = "#"
                
            prjID=soup.find_all('a', href=re.compile('/PRJE'))
            if len(prjID) > 0:
                prjIDLink = prjID[0]['href']
                prjIDLinkArray = prjIDLink.split("/")
                if(prjIDLinkArray[-1] == ""):
                    genNote["id"] = prjIDLinkArray[-2]
                else:
                    genNote["id"] = prjIDLinkArray[-1]
            else:
                prjID1=soup.find_all('a', href=re.compile(':PRJE'))
                if len(prjID1) > 0:
                    prjIdString = prjID1[0].text
                    prjIdNumber = prjIdString.split(":")[2]
                    genNote["id"] = prjIdNumber
                else:
                    genNote["id"] = None
            
                
            if genNote["id"] != None:
                url = (article['pdfUrl']).split('/pdf')[0]
                genNote["id"] = genNote["id"]
                genNote["url"] = url
                genNote["citeURL"] = "https://doi.org/"+article["doi"]
                genNote["title"] = BeautifulSoup(article["title"], "html.parser").text
                genNote["abstract"] = BeautifulSoup(article["abstractText"], "html.parser").text
                genNote["figureURI"] = figureUri
                figureCaptionHtml=soup.find_all('div', {'class' : 'caption'})
                figureCaptionText = figureCaptionHtml[0].h3.text
                genNote["caption"] = BeautifulSoup(figureCaptionText, "html.parser").text
                notes.append(genNote)

class ImportNotes():
    def start(self, notesJsonString):
        es = Elasticsearch('http://45.88.81.118:80/elasticsearch', connection_class=RequestsHttpConnection,
                    use_ssl=False, verify_certs=False, timeout=10000)

        def get_samples(index_name, es):
            samples = dict()
            data = es.search(index=index_name, size=100000)
            for sample in data['hits']['hits']:
                samples[sample['_id']] = sample['_source']
            return samples

        data_portal = get_samples("data_portal", es)
        data = notesJsonString

        for record in data:
            results = requests.get(f"https://www.ebi.ac.uk/ena/browser/api/xml/{record['id']}")
            root = etree.fromstring(results.content)
            if record['id'] == 'PRJNA550988' or record['id'] == 'PRJEB40665' or record['id'] == 'PRJEB3308':
                continue
            try:
                organism_name = root.find("PROJECT").find("UMBRELLA_PROJECT").find("ORGANISM").find("SCIENTIFIC_NAME").text
            except AttributeError:
                organism_name = root.find("PROJECT").find("SUBMISSION_PROJECT").find("ORGANISM").find("SCIENTIFIC_NAME").text

            if organism_name not in data_portal:
                print(f"Error: {organism_name} doesn't exist in data_portal index")
            else:
                if 'genome_notes' not in data_portal[organism_name] or len(data_portal[organism_name]['genome_notes']) == 0:
                    data_portal[organism_name]['genome_notes'] = [record]
                    print(data_portal[organism_name]['genome_notes'])
                    es.index("data_portal", data_portal[organism_name], id=organism_name)
                
if __name__ == "__main__":
    genNotesObj = GetGenomeNotes()
    genNotesObj.start()
    notesList = notes
    importNotes = ImportNotes()
    importNotes.start(notesList)
