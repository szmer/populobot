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
        self.form = self.interp[0]
        self.lemma = self.interp[1]
        self.interp = self.interp[2:]

argparser = argparse.ArgumentParser(description='Extract a dictionary of correct forms and morphosyntactical tags from a list of csv edition files, parsed with Morfeusz & Concraft.')
argparser.add_argument('file_list_path')

args = argparser.parse_args()

sections = []
with open(args.file_list_path) as list_file:
    for file_path in list_file.readlines():
        file_path = file_path.strip()
        with open(file_path) as indexed_file:
            sections += [sec for sec in load_indexed(indexed_file) if sec.section_type == 'document']

# token str -> a list of Concraft-approved interps
# Interps are useful because Concraft assigns them also to non-dictionary words.
interps_dictionary = dict()
for section in sections:
    tokens = chain.from_iterable([re.split('\\s', par) for (pg, par) in section.pages_paragraphs])
    tokens = [Token(t_str) for t_str in tokens if t_str.strip() != '']
    for t in tokens:
        if t.form.strip() == '' or t.unknown_form:
            continue
        if not t.form in interps_dictionary:
            interps_dictionary[t.form] = [ ':'.join(t.interp) ]
        else:
            interps_dictionary[t.form] += [ ':'.join(t.interp) ]

# Dump the collected dictionary.
for (form, interps) in interps_dictionary.items():
    print('{} : {}'.format(form, list(set(interps))))
