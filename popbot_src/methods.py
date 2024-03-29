from collections import Counter
import re
import csv
from os import makedirs
from nltk.probability import FreqDist
from nltk.collocations import BigramCollocationFinder, BigramAssocMeasures, TrigramCollocationFinder, TrigramAssocMeasures
from popbot_src.rule import rules_from_freqs
from popbot_src.parsed_token import ParsedToken, NoneTokenError
from collections import defaultdict

def zero():
    return 0

def basic_stats(sections, method_options):
    "Returns sorted tuples reflecting the frequency of word forms."
    full_tokens = []
    for section in sections:
        for pg, par in section.pages_paragraphs:
            tokens = list(re.split('\\s', par))
            for t_str in tokens:
                try: # can fail if something isn't a readable token
                    full_tokens.append(ParsedToken.from_str(t_str))
                except NoneTokenError:
                    pass
    # Collect statistics of token types.
    stats = defaultdict(zero)
    stats['all_docs'] = len(sections)
    stats['all_tokens'] = len(full_tokens)
    for token in full_tokens:
        if token.corrected:
            stats['corrected_tokens'] += 1
        if token.unknown_form:
            stats['unknown_form_tokens'] += 1
        if token.proper_name:
            stats['proper_name_tokens'] += 1
        if token.latin:
            stats['latin_tokens'] += 1
    return list(stats.items())

#
# Methods for forms frequency and collocations.
#

def prepare_form_corpus(sections):
    "Return all tokens in one list, in form form%lemma%interp"
    full_tokens = []
    for section in sections:
        for pg, par in section.pages_paragraphs[1:]: # skip the title
            tokens = list(re.split('\\s', par))
            for t_str in tokens:
                try: # can fail if something isn't a readable token
                    token = ParsedToken.from_str(t_str)
                    full_tokens.append('{}%{}%{}'.format(token.form, token.lemma, token.interp_str()))
                except NoneTokenError:
                    pass
    return full_tokens

def unpack_ngram_forms(ngram_tuple):
    """Take a tuple of n forms coded with lemmas and interpretations and unpack it into a n*3 tuple
    with these elements separated."""
    result = []
    for form_record in ngram_tuple:
        result += form_record.split('%')
    return result

def find_form_collocations(full_tokens, finder, metrics_obj, needed_words=[]):
    coll_finder = finder.from_words(full_tokens)
    coll_finder.apply_freq_filter(2)
    coll_finder.apply_word_filter(lambda w: len(w.split('%')[0]) < 2)
    if needed_words:
        # Reject all ngrams that don't have one of required words as their lemmas.
        coll_finder.apply_ngram_filter(lambda *args: not any([(a.split('%')[1] in needed_words)
                                                              for a in args]))
    result = coll_finder.score_ngrams(metrics_obj.raw_freq)
    # Format the result as a list of tuples.
    for row_n, row in enumerate(result):
        # join the word entries of the phrase into the outer tuple:
        result[row_n] = (unpack_ngram_forms(row[0])
                         # the retrieved frequency will be an integer, but sometimes with a minor
                         # float corruption
                         + [round(row[1] * len(full_tokens)),
                             # Add other metrics to the tuple; the list of arguments needs to be
                             # constructed at runtime for both n-gram sizes.
                             coll_finder.score_ngram(*([metrics_obj.jaccard] + list(row[0]))),
                             coll_finder.score_ngram(*([metrics_obj.likelihood_ratio] + list(row[0])))])
    # Sort by frequency.
    result.sort(key=lambda x: x[-3], reverse=True)
    return result

def form_frequency(sections, method_options):
    "Returns sorted tuples reflecting the frequency of word forms."
    fd = FreqDist(prepare_form_corpus(sections))
    # This contains (token, freq) tuples.
    result = list(fd.most_common(fd.B()))
    for row_n, row in enumerate(result):
        # re-splitted token info, frequency, frequency as a ratio
        result[row_n] = tuple(row[0].split('%')) + (row[1], row[1]/fd.N())
    return result

def form_bigrams(sections, method_options):
    full_tokens = prepare_form_corpus(sections)
    result = find_form_collocations(full_tokens, BigramCollocationFinder, BigramAssocMeasures())
    return result

def form_trigrams(sections, method_options):
    full_tokens = prepare_form_corpus(sections)
    result = find_form_collocations(full_tokens, TrigramCollocationFinder, TrigramAssocMeasures())
    return result

#
# Methods for lemmas frequency and collocations.
#
def prepare_lemma_corpus(sections, omit_suspicious_interps):
    "Return all tokens in one list"
    full_tokens = []
    for section in sections:
        for pg, par in section.pages_paragraphs[1:]: # skip the title
            tokens = list(re.split('\\s', par))
            for t_str in tokens:
                try: # can fail if something isn't a readable token
                    token = ParsedToken.from_str(t_str)
                    if not omit_suspicious_interps or not 'brev' in token.interp:
                        full_tokens.append(token.lemma)
                except NoneTokenError:
                    pass
    return full_tokens

def find_lemma_collocations(full_tokens, finder, metrics_obj, needed_words=[]):
    coll_finder = finder.from_words(full_tokens)
    coll_finder.apply_freq_filter(2)
    coll_finder.apply_word_filter(lambda w: len(w) < 2)
    if needed_words:
        # Reject all ngrams that don't have one of required words as their lemmas.
        coll_finder.apply_ngram_filter(lambda *args: not any([(a in needed_words) for a in args]))
    result = coll_finder.score_ngrams(metrics_obj.raw_freq)
    # Format the result as a list of tuples.
    for row_n, row in enumerate(result):
        # join the word entries of the phrase into the outer tuple:
        result[row_n] = (list(row[0])
                         # the retrieved frequency will be an integer, but sometimes with a minor
                         # float corruption
                         + [round(row[1] * len(full_tokens)),
                             # Add other metrics to the tuple; the list of arguments needs to be
                             # constructed at runtime for both n-gram sizes.
                             coll_finder.score_ngram(*([metrics_obj.jaccard] + list(row[0]))),
                             coll_finder.score_ngram(*([metrics_obj.likelihood_ratio] + list(row[0])))])
    # Sort by frequency.
    result.sort(key=lambda x: x[-3], reverse=True)
    return result

def lemma_frequency(sections, method_options):
    "Returns sorted tuples reflecting the frequency of word forms."
    fd = FreqDist(prepare_lemma_corpus(sections, method_options['omit_suspicious_interps']))
    # This contains (token, freq) tuples.
    result = list(fd.most_common(fd.B()))
    for row_n, row in enumerate(result):
        result[row_n] = row + (row[1]/fd.N(),)
    return result

def lemma_bigrams(sections, method_options):
    full_tokens = prepare_lemma_corpus(sections, method_options['omit_suspicious_interps'])
    result = find_lemma_collocations(full_tokens, BigramCollocationFinder, BigramAssocMeasures()) 
    return result

def lemma_trigrams(sections, method_options):
    full_tokens = prepare_lemma_corpus(sections, method_options['omit_suspicious_interps'])
    result = find_lemma_collocations(full_tokens, TrigramCollocationFinder, TrigramAssocMeasures()) 
    return result

#
# Keyword collocations.
#
def group_placeholder(group):
    """Give the group marker a mock form/lemma formed from its constituents."""
    return '__' + '-'.join(group[:3]+(['...'] if len(group) > 3 else []))

def keywords_bigrams(sections, method_options):
    category = method_options['keyword_category']
    full_tokens = prepare_form_corpus(sections)
    for token_n, form_token in enumerate(full_tokens):
        fields = form_token.split('%')
        for group_n, group in enumerate(category):
            if fields[1] in group:
                fields[0] = group_placeholder(group)
                fields[1] = group_placeholder(group)
                break
        full_tokens[token_n] = '%'.join(fields)
    result = find_form_collocations(full_tokens, BigramCollocationFinder,
                                    BigramAssocMeasures(),
                                    needed_words=[group_placeholder(group) for group in category])
    return result

def keywords_lemma_bigrams(sections, method_options):
    category = method_options['keyword_category']
    full_tokens = prepare_lemma_corpus(sections, method_options['omit_suspicious_interps'])
    for token_n, lemma_token in enumerate(full_tokens):
        for group_n, group in enumerate(category):
            if lemma_token in group:
                full_tokens[token_n] = group_placeholder(group)
                break
    result = find_lemma_collocations(full_tokens, BigramCollocationFinder,
                                    BigramAssocMeasures(),
                                    needed_words=[group_placeholder(group) for group in category])
    return result

def keywords_trigrams(sections, method_options):
    category = method_options['keyword_category']
    full_tokens = prepare_form_corpus(sections)
    for token_n, form_token in enumerate(full_tokens):
        fields = form_token.split('%')
        for group_n, group in enumerate(category):
            if fields[1] in group:
                fields[0] = group_placeholder(group)
                fields[1] = group_placeholder(group)
                break
        full_tokens[token_n] = '%'.join(fields)
    result = find_form_collocations(full_tokens, TrigramCollocationFinder,
                                    TrigramAssocMeasures(),
                                    needed_words=[group_placeholder(group) for group in category])
    return result

def keywords_lemma_trigrams(sections, method_options):
    category = method_options['keyword_category']
    full_tokens = prepare_lemma_corpus(sections, method_options['omit_suspicious_interps'])
    for token_n, lemma_token in enumerate(full_tokens):
        for group_n, group in enumerate(category):
            if lemma_token in group:
                full_tokens[token_n] = group_placeholder(group)
                break
    result = find_lemma_collocations(full_tokens, TrigramCollocationFinder,
                                    TrigramAssocMeasures(),
                                    needed_words=[group_placeholder(group) for group in category])
    return result

def rule_lifetime_tables(sections, method_options):
    """
    Get the dictionaries of rule -> the years when it was applicable (and not, in the second
    returned value). The third value is the frequency dictionary of year -> number of tokens, the
    fourth the dictionary (keyword group's first lemma) -> dict of frequency by year.
    """
    year_freqs = dict() # year -> lemma frequency counter
    year_freq_numbers = dict() # year -> the number of tokens found for it
    group_year_freqs = dict() # keyword group's first lemma -> list of years where it appears
    lemma_groups = dict() # lemma -> the list of keyword groups, can be empty
    for section in sections:
        if not section.pertinence:
            continue
        if not section.date:
            continue
        year = section.date.year
        local_counter = Counter()
        for pg, par in section.pages_paragraphs[1:]: # skip the title
            tokens = list(re.split('\\s', par))
            for t_str in tokens:
                try: # can fail if something isn't a readable token
                    token = ParsedToken.from_str(t_str)
                    if not method_options['omit_suspicious_interps'] or not 'brev' in token.interp:
                        if not token.lemma in lemma_groups:
                            lemma_groups[token.lemma] = []
                            for category in method_options['keyword_categories']:
                                for group in method_options['keyword_categories'][category]:
                                    for lemma in group:
                                        if token.lemma == lemma:
                                            lemma_groups[token.lemma].append(f"{category}_{group[0]}")
                        # Add an occurence for each of the keyword groups associated with the lemma.
                        for group in lemma_groups[token.lemma]:
                            local_counter.update([group])
                        if not year in year_freq_numbers:
                            year_freq_numbers[year] = 0
                        year_freq_numbers[year] += 1
                except NoneTokenError:
                    pass
        if not year in year_freqs:
            year_freqs[year] = Counter()
        year_freqs[year].update(local_counter)
    # Extract the rules from years and create tables of their applicability.
    rules_lifetime = dict() # rule -> years applicable
    rules_lifetime_neg = dict() # rule -> years not applicable
    known_years = set()
    for year in range(method_options['history_start_year'],
            method_options['history_end_year']+1):
        if not year in year_freqs:
            continue
        # Collect the group_year_freqs.
        for keyword_group in year_freqs[year]:
            if not keyword_group in group_year_freqs:
                group_year_freqs[keyword_group] = dict()
            group_year_freqs[keyword_group][year] = year_freqs[year][keyword_group]
        # Get the rules applicable in the given year.
        rules = rules_from_freqs(year_freqs[year])
        # Observe rule changes.
        for rule in rules_lifetime:
            if not rule in rules:
                rules_lifetime_neg[rule].append(str(year))
        for rule in rules:
            if not rule in rules_lifetime:
                rules_lifetime_neg[rule] = list(known_years)
                rules_lifetime[rule] = [str(year)]
            else:
                rules_lifetime[rule].append(str(year))
        known_years.add(str(year))
        with open(f"rules_{year}.csv", "w+") as rules_file:
            for rule in rules:
                print(str(rule), file=rules_file)
    return rules_lifetime, rules_lifetime_neg, year_freq_numbers, group_year_freqs

#
# The generic method applier.
#
def apply_method(experiment_name, method_name, method_function, subset_index, method_options):
    makedirs('results/{}/{}'.format(experiment_name, method_name), exist_ok=True)
    for (subset_name, sections) in subset_index:
        with open('results/{}/{}/{}.csv'.format(experiment_name, method_name, subset_name), 'w+') as result_file:
            writer = csv.writer(result_file, delimiter='\t')
            writer.writerows(method_function(sections, method_options))
