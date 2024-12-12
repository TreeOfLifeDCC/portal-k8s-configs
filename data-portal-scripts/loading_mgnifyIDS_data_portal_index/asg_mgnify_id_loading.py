import asyncio
import json
from aiohttp import ClientSession, ClientTimeout
from elasticsearch import AsyncElasticsearch
import datetime

ES_HOST = os.getenv('ES_CONNECTION_URL')
ES_USERNAME = os.getenv('ES_USERNAME')
ES_PASSWORD = os.getenv('ES_PASSWORD')

# connect to Elasticsearch cluster
es = AsyncElasticsearch(
    [ES_HOST],
    http_auth=(ES_USERNAME, ES_PASSWORD),
    use_ssl=True,
    verify_certs=False,
    ssl_show_warn=False
)

# Define a semaphore to limit concurrent API requests
# the EBI Seach api allows only 99 requests at a time, but we are keeping the limit to 50 to be on the safe side
RATE_LIMIT = 50
semaphore = asyncio.Semaphore(RATE_LIMIT)


async def get_mgnify_study_id(session, biosample_id):
    url = (f'https://www.ebi.ac.uk/ebisearch/ws/rest/metagenomics_analyses?format=json&start=0'
           f'&query=BIOSAMPLES:{biosample_id}&size=25'
           f'&fields=METAGENOMICS_PROJECTS,pipeline_version,experiment_type,'
           f'sample_name,project_name,ENA_RUN,ANALYSIS,SRA-SAMPLE')

    # Semaphore used to limit concurrency
    await semaphore.acquire()
    try:
        await asyncio.sleep(2)
        async with session.get(url) as response:
            response.raise_for_status()
            data = await response.json()
            return data['entries'][0]['fields']['METAGENOMICS_PROJECTS']
    except Exception as e:
        # print(f"MGnify entry for biosample ID {biosample_id} was not found: {e}")
        return None
    finally:
        semaphore.release()


async def process_record(session, record):
    update_flag = False
    recordset = record['_source']

    if 'metagenomes_records' in recordset and recordset['metagenomes_records']:
        tasks = []

        for metagenome_rec in recordset['metagenomes_records']:
            biosample_id = metagenome_rec['accession']
            tasks.append(get_mgnify_study_id(session, biosample_id))

        results = await asyncio.gather(*tasks)

        for metagenome_rec, mgnify_ids_list in zip(recordset['metagenomes_records'], results):
            if mgnify_ids_list is not None:
                print(recordset['organism'])
                print(metagenome_rec['accession'])
                print(mgnify_ids_list)

                metagenome_rec['mgnify_study_ids'] = mgnify_ids_list
                update_flag = True

        # Update Elasticsearch document if modified
        if update_flag:
            try:
                await es.update(
                    index='data_portal_test',
                    id=record['_id'],
                    body={
                        "doc": {
                            "metagenomes_records": recordset['metagenomes_records'],
                            "mgnify_status": "true"
                        }
                    }
                )
                print(f"Successfully updated record {record['_id']}")
            except Exception as e:
                print(f"Failed to update record {record['_id']}: {e}")


async def update_data_portal_index_production():
    filters = {'query': {'match_all': {}}}
    query = json.dumps(filters)

    try:
        print('Process started at ', datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        data = await es.search(
            index='data_portal_test',
            size=1000,
            from_=0,
            track_total_hits=True,
            body=json.loads(query)
        )
    except Exception as e:
        print(f"Failed to get data portal entries: {e}")
        return

    timeout = ClientTimeout(total=30)
    async with ClientSession(timeout=timeout) as session:
        tasks = [process_record(session, record) for record in data['hits']['hits']]
        await asyncio.gather(*tasks)

    print('Process finished at ', datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

# Main execution
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(update_data_portal_index_production())

