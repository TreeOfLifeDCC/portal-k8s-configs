FROM python:latest
RUN pip install elasticsearch flask-cors
COPY ./import_from_biosamples.py ./
COPY ./import_statuses.py ./
COPY ./run_import.sh ./
ENTRYPOINT ["bash", "run_import.sh"]