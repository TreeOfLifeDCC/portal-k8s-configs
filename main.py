from elasticsearch import Elasticsearch
from flask_cors import CORS, cross_origin
from flask import Flask
app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
es = Elasticsearch(['elasticsearch:9200'])


@app.route("/dtol")
@cross_origin()
def dtol_samples():
    data = es.search(index='dtol', size=10000)
    return data


@app.route("/dtol/<sample_id>")
@cross_origin()
def dtol_samples_details(sample_id):
    data = es.search(index='dtol', q=f"accession:{sample_id}")
    if data['hits']['total'] == 0:
        data = es.search(index='dtol', q=f"organism:{sample_id}")
    return data


@app.route("/statuses")
@cross_origin()
def dtol_statuses():
    data = es.search(index='statuses', size=10000)
    return data


if __name__ == "__main__":
    # Only for debugging while developing
    app.run(host='0.0.0.0', debug=True, port=80)
