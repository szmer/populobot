import argparse
import csv
import json
import sys

from popbot_src.indexing_common import load_indexed

argparser = argparse.ArgumentParser(description='Unpack document IDs and titles from a CSV edition'
        ' to annotate authors (print to the standard output).')
argparser.add_argument('config_file_path', help='The config file describing where to find the corpus'
        ' and its metadata.')
argparser.add_argument('raw_csv_path', help='The csv file containing the loaded edition with no'
        ' further processing.')

args = argparser.parse_args()

with open(args.raw_csv_path) as sections_file:
    edition_sections = load_indexed(sections_file)
with open(args.config_file_path) as config_file:
    config = json.load(config_file)

writer = csv.writer(sys.stdout)
for sec in edition_sections:
    if sec.section_type == 'document':
        writer.writerow([sec.inbook_document_id, sec.title(config), sec.pertinence, ""])
