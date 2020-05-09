import argparse
import json
import logging
import sys

from popbot_src.load_helpers import join_linebreaks
from popbot_src.indexing_common import load_indexed
from popbot_src.parsing import parsed_sections
from popbot_src.tei import write_tei_corpus

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    stream=sys.stdout,
    datefmt='%Y-%m-%d %H:%M:%S')

argparser = argparse.ArgumentParser()
argparser.add_argument('output_tei_path')
argparser.add_argument('config_file_path')
argparser.add_argument('raw_csv_path', help='The csv file containing the loaded edition with no'
        ' further processing.')
argparser.add_argument('--leave_hyphens', action='store_true',
        help="Don't join the word broken by lines with hyphens")
argparser.add_argument('--dont_parse', action='store_true',
        help="Don't parse the edition with Morfeusz and Concraft, skip printing segmentation and "
        "morphosyntactic information.")

args = argparser.parse_args()

with open(args.raw_csv_path) as sections_file:
    edition_sections = load_indexed(sections_file)
with open(args.config_file_path) as config_file:
    config = json.load(config_file)

# Join the hyphens unless this is turned off.
if not args.leave_hyphens:
    for sec in edition_sections:
        for par_n, (page, paragraph) in enumerate(sec.pages_paragraphs):
            sec.pages_paragraphs[par_n] = join_linebreaks(paragraph)

# Parse the edition unless this is turned off.
parsed_edition_sections = False
if not args.dont_parse:
    parsed_edition_sections = parsed_sections(edition_sections)

# Print the TEI corpus.
write_tei_corpus(args.output_tei_path, config['book_title'].replace(' ', '_'), edition_sections,
        parsed_sections=parsed_sections)
