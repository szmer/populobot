import re
from itertools import chain
import argparse

from popbot_src.indexing_common import load_indexed

class Token():
    def __init__(self, parsed_edition_str):
        semantic_fields = parsed_edition_str.split('_')
        self.proper_name = 'PN' in semantic_fields
        self.unknown_form = '??' in semantic_fields
        self.interp = '_'.join([f for f in semantic_fields if not f in ['PN', '??']]).split(':')
        return self

argparser = argparse.ArgumentParser(description='Extract a dictionary of correct forms and morphosyntactical tags from the given csv edition file, parsed with Morfeusz & Concraft.')
argparser.add_argument('indexed_file_path')

args = argparser.parse_args()

with open(args.indexed_file_path) as indexed_file:
    sections = load_indexed(indexed_file)

words_dictionary = dict()
for section in sections:
    tokens = chain.from_iterable([re.split('\\s', par) for par in section.pages_paragraphs])
    tokens = [Token(t_str) for t_str in tokens]
    # token str -> a list of Concraft-approved interps
