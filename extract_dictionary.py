import re
from itertools import chain
import argparse

from popbot_src.indexing_common import load_indexed
from popbot_src.parsed_token import ParsedToken

argparser = argparse.ArgumentParser(description='Extract a dictionary of correct forms and morphosyntactical tags from a list of csv edition files, parsed with Morfeusz & Concraft.')
argparser.add_argument('file_list_path')
argparser.add_argument('--assume_all_correct', action='store_true')

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
    tokens = [ParsedToken.from_str(t_str) for t_str in tokens if t_str.strip() != '']
    for t in tokens:
        if t.form.strip() == '' or (t.unknown_form and not args.assume_all_correct):
            continue
        if not t.form in interps_dictionary:
            interps_dictionary[t.form] = [ ':'.join(t.interp) ]
        else:
            interps_dictionary[t.form] += [ ':'.join(t.interp) ]

# Dump the collected dictionary.
for (form, interps) in interps_dictionary.items():
    print('{} : {}'.format(form, list(set(interps))))
