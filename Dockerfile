FROM python:latest
RUN pip install elasticsearch==7.13.4 flask-cors requests==2.28.0
COPY ./import-umbrella-projects.py ./
COPY ./constants.py ./
COPY ./common_functions.py ./
COPY ./run_import.sh ./
ENTRYPOINT ["bash", "run_import.sh"]