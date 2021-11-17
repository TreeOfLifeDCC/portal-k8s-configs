import requests

from common_functions import check_field_existence, get_common_name


def main():
    samples = requests.get(
        "https://www.ebi.ac.uk/biosamples/samples?size=10000&"
        "filter=attr%3Aproject%20name%3ADTOL").json()








if __name__ == "__main__":
    main()
