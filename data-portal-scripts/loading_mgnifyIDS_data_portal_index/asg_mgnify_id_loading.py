import json
import requests
import urllib3
from elasticsearch import Elasticsearch, AIOHttpConnection
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import warnings

# disable insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='Unverified HTTPS request')
warnings.filterwarnings("ignore")

# establish session with retry settings
session = requests.Session()
retries = Retry(total=5, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retries))


ES_HOST = os.getenv('ES_CONNECTION_URL')
ES_USERNAME = os.getenv('ES_USERNAME')
ES_PASSWORD = os.getenv('ES_PASSWORD')

# connect to Elasticsearch cluster
es = AsyncElasticsearch([ES_HOST],
                        connection_class=AIOHttpConnection,
                        http_auth=(ES_USERNAME, ES_PASSWORD),
                        use_ssl=True, verify_certs=False)


def update_data_portal_index_production():
    filters = {'query': {'match_all': {}}}
    query = json.dumps(filters)

    try:
        data = es.search(index='data_portal', size=1000, from_=0, track_total_hits=True,
                         body=json.loads(query))
    except Exception as e:
        print(f"Failed to get data portal entries: {e}")
        return

    for record in data['hits']['hits']:
        update_flag = False
        recordset = record['_source']

        if 'metagenomes_records' in recordset and recordset['metagenomes_records']:
            print(recordset['organism'])
            for metagenome_rec in recordset['metagenomes_records']:
                biosample_id = metagenome_rec['accession']

                mgnify_ids_list = get_mgnify_study_id(biosample_id)
                if mgnify_ids_list is not None:
                    print(biosample_id)
                    print(mgnify_ids_list)

                    # Update metagenome record
                    metagenome_rec['mgnify_study_ids'] = mgnify_ids_list
                    update_flag = True
                    print(metagenome_rec)
                    print()

            # After looping through all entries, update the document in Elasticsearch
            try:
                if update_flag:
                    es.update(
                        index='data_portal',
                        id=record['_id'],
                        body={
                            "doc": {
                                "metagenomes_records": recordset['metagenomes_records']
                            }
                        }
                    )
                    print(f"Successfully updated record {record['_id']}")
            except Exception as e:
                print(f"Failed to update record {record['_id']}: {e}")


def get_mgnify_study_id(biosample_id):
    try:
        api_data = session.get(f'https://www.ebi.ac.uk/metagenomics/api/v1/samples/{biosample_id}')
        api_data.raise_for_status()
        mgnify_id = api_data.json()
        mgnify_study_ids = mgnify_id['data']['relationships']['studies']['data']
        mgnify_ids_list = [item['id'] for item in mgnify_study_ids]
        return mgnify_ids_list
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch data for biosample ID {biosample_id}: {e}")
        return None


# Main execution
if __name__ == '__main__':
    update_data_portal_index_production()
