import argparse
import csv
import json
import logging
import sys

from popbot_src.load_helpers import join_linebreaks
from popbot_src.indexing_common import load_indexed
from popbot_src.parsing import pathed_sections
from popbot_src.tei import write_tei_corpus

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    stream=sys.stdout,
    datefmt='%Y-%m-%d %H:%M:%S')

argparser = argparse.ArgumentParser()
argparser.add_argument('output_tei_path', help='Name of a catalog of TEI corpora when the corpus'
        'will be placed. This path will be created if does not exist.')
argparser.add_argument('config_file_path', help='The config file describing where to find the corpus'
        ' and its metadata.')
argparser.add_argument('raw_csv_path', help='The csv file containing the loaded edition with no'
        ' further processing.')
argparser.add_argument('--authors_file',
        help="Path to a CSV file with doc section ID in the first column, extracted title in the"
        " econd one, and assigned author in the fourth (the default author will be used if empty).")
argparser.add_argument('--leave_hyphens', action='store_true',
        help="Don't join the word broken by lines with hyphens")
argparser.add_argument('--dont_parse', action='store_true',
        help="Don't parse the edition with Morfeusz and Concraft, skip printing segmentation and "
        "morphosyntactic information.")

args = argparser.parse_args()

with open(args.raw_csv_path) as sections_file:
    edition_sections = [sec for sec in load_indexed(sections_file)
            # skip sections that have only the title.
            if len(sec.pages_paragraphs) > 1]
with open(args.config_file_path) as config_file:
    config = json.load(config_file)
if args.authors_file is not None:
    with open(args.authors_file) as authors_file:
        reader = csv.reader(authors_file)
        authors = dict()
        for row in reader:
            if not args.leave_hyphens:
                title = join_linebreaks(row[1]).strip() # preprocess like in the loaded edition
            else:
                title = row[1]
            authors[f'{row[0]}:::{title}'] = row[3]
        config["authors"] = authors

# Join the hyphens unless this is turned off.
if not args.leave_hyphens:
    for sec in edition_sections:
        for par_n, (page, paragraph) in enumerate(sec.pages_paragraphs):
            sec.pages_paragraphs[par_n] = (page, join_linebreaks(paragraph).strip()) # also trim whitespace

# Parse the edition unless this is turned off.
pathed_edition_sections = False
if not args.dont_parse:
    pathed_edition_sections = pathed_sections(edition_sections)

# Print the TEI corpus.
write_tei_corpus(args.output_tei_path, config['tei_code'], edition_sections,
        pathed_edition_sections, config)
