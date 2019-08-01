import argparse
import re
import enchant

from popbot_src.indexing_common import load_indexed

argparser = argparse.ArgumentParser(description='Correct a parsed (with Morfeusz&Conraft) csv file, using a dictionary generated with extract_dictionary.py and PyLucene spellchecking.')
argparser.add_argument('indexed_file_path')
argparser.add_argument('dictionary_file')
argparser.add_argument('wordlist')
argparser.add_argument('--use_lemmas', action='store_true')

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
# token str -> a list of Concraft-approved interps (and optionally lemmas)
# Interps are useful because Concraft assigns them also to non-dictionary words.
tags_dictionary = dict()
with open(args.dictionary_file) as dict_file:
    for row in dict_file.readlines():
        row = row.strip()
        if len(row) == 0:
            continue
        # The first colon separates the form from the rest of the row.
        first_colon = row.index(':')
        form = row[:first_colon-1]
        tags = eval(row[first_colon+1:])
        tags_dictionary[form] = tags

#
# Set up Enchant spellchecking.
#
spellchecker = enchant.DictWithPWL(tag='pl_PL', pwl=args.wordlist)
for form, tags in tags_dictionary.items():
    spellchecker.add(form)

#
# Load the section and go through them with corrections. 
#
def correct_word(word, tag):
    """The function expects a interp dictionary without lemmas."""
    try:
        candidates = spellchecker.suggest(word)
    except ValueError:
        return False
    pruned_candidates = [cand for cand in candidates
            if (cand in tags_dictionary and tag in tags_dictionary[cand])]
    if len(pruned_candidates) > 0:
        candidates = pruned_candidates
    if len(candidates) > 0:
        return candidates[0].replace(' ', '_')
    return False

def correct_word_with_lemma(word, tag):
    try:
        candidates = spellchecker.suggest(word)
    except ValueError:
        return False, False
    for cand in candidates:
        if cand in tags_dictionary:
            delemmatized_tags = [':'.join(tag.split(':')[1:]) for tag in tags_dictionary[cand]]
            try:
                chosen_tag_n = delemmatized_tags.index(tag)
                return cand, tags_dictionary[cand][chosen_tag_n].split(':')[0]
            except:
                pass
    return False, False

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
                    if args.use_lemmas:
                        correction, new_lemma = correct_word_with_lemma(token.form, token.interp)
                    else:
                        correction = correct_word(token.form, token.interp)
                    if correction:
                        token.form = correction
                        if args.use_lemmas:
                            token.lemma = new_lemma
                        token.unknown_form = False
                        token.corrected = True
                new_pages_paragraphs[-1] = (pg, new_pages_paragraphs[-1][1] + ' ' + repr(token))
        section.pages_paragraphs = new_pages_paragraphs
    # Print the section.
    for row in section.row_strings():
        print(row)
