import argparse
import re
import enchant

from popbot_src.indexing_common import load_indexed

argparser = argparse.ArgumentParser(description='Correct a parsed (with Morfeusz&Conraft) csv file, using a dictionary generated with extract_dictionary.py and PyLucene spellchecking.')
argparser.add_argument('indexed_file_path')
argparser.add_argument('dictionary_file')

args = argparser.parse_args()

class Token():
    def __init__(self, parsed_edition_str):
        semantic_fields = parsed_edition_str.split('_')
        self.proper_name = 'PN' in semantic_fields
        self.unknown_form = '??' in semantic_fields
        self.corrected = False
        self.interp = '_'.join([f for f in semantic_fields if not f in ['PN', '??']]).split(':')
        self.form = self.interp[0]
        self.lemma = self.interp[1]
        self.interp = ':'.join(self.interp[2:])

    def __repr__(self):
        repr_str = '{}:{}:{}'.format(self.form, self.lemma, self.interp)
        if self.unknown_form:
            repr_str = '??_' + repr_str
        elif self.corrected:
            repr_str = '!!_' + repr_str
        if self.proper_name:
            repr_str = 'PN_' + repr_str
        return repr_str

#
# Load the dictionary of correct forms.
#
# token str -> a list of Concraft-approved interps
# Interps are useful because Concraft assigns them also to non-dictionary words.
interps_dictionary = dict()
with open(args.dictionary_file) as dict_file:
    for row in dict_file.readlines():
        row = row.strip()
        if len(row) == 0:
            continue
        first_colon = row.index(':')
        form = row[:first_colon-1]
        interps = eval(row[first_colon+1:])
        interps_dictionary[form] = interps

#
# Set up Enchant spellchecking.
#
spellchecker = enchant.Dict(tag='pl_PL')
for form, interps in interps_dictionary.items():
    spellchecker.add(form)

#
# Load the section and go through them with corrections. 
#
def correct_word(word, interp):
    try:
        candidates = spellchecker.suggest(word)
    except ValueError:
        return False
    pruned_candidates = [cand for cand in candidates
            if (cand in interps_dictionary and interp in interps_dictionary[cand])]
    if len(pruned_candidates) > 0:
        candidates = pruned_candidates
    if len(candidates) > 0:
        return candidates[0]
    return False

with open(args.indexed_file_path) as sections_file:
    edition_sections = load_indexed(sections_file)

for section in edition_sections:
    if section.section_type == 'document':
        new_pages_paragraphs = []
        for (pg, par) in section.pages_paragraphs:
            tokens = list(re.split('\\s', par))
            tokens = [Token(t_str) for t_str in tokens if t_str.strip() != '']
            new_pages_paragraphs.append((pg, ''))
            for token in tokens:
                if token.form.strip() != '' and token.unknown_form:
                    correction = correct_word(token.form, token.interp)
                    if correction:
                        token.form = correction
                        token.unknown_form = False
                        token.corrected = True
                new_pages_paragraphs[-1] = (pg, new_pages_paragraphs[-1][1] + ' ' + repr(token))
        section.pages_paragraphs = new_pages_paragraphs
    # Print the section.
    for row in section.row_strings():
        print(row)