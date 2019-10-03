import re
import csv
from os import makedirs
from nltk.probability import FreqDist
from nltk.collocations import BigramCollocationFinder, BigramAssocMeasures, TrigramCollocationFinder, TrigramAssocMeasures
from popbot_src.parsed_token import ParsedToken
from collections import defaultdict

def zero():
    return 0

def basic_stats(sections):
    "Returns sorted tuples reflecting the frequency of word forms."
    full_tokens = []
    for section in sections:
        for pg, par in section.pages_paragraphs:
            tokens = list(re.split('\\s', par))
            for t_str in tokens:
                try: # can fail if something isn't a readable token
                    full_tokens.append(ParsedToken.from_str(t_str))
                except:
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

def form_frequency(sections):
    "Returns sorted tuples reflecting the frequency of word forms."
    full_tokens = []
    for section in sections:
        for pg, par in section.pages_paragraphs:
            tokens = list(re.split('\\s', par))
            for t_str in tokens:
                try: # can fail if something isn't a readable token
                    full_tokens.append(ParsedToken.from_str(t_str).form)
                except:
                    pass
    fd = FreqDist(full_tokens)
    # This contains (token, freq) tuples.
    result = list(fd.most_common(fd.B()))
    for row_n, row in enumerate(result):
        result[row_n] = row + (row[1]/fd.N(),)
    return result

def lemma_frequency(sections):
    "Returns sorted tuples reflecting the frequency of word forms."
    full_tokens = []
    for section in sections:
        for pg, par in section.pages_paragraphs:
            tokens = list(re.split('\\s', par))
            for t_str in tokens:
                try: # can fail if something isn't a readable token
                    full_tokens.append(ParsedToken.from_str(t_str).lemma)
                except:
                    pass
    fd = FreqDist(full_tokens)
    # This contains (token, freq) tuples.
    result = list(fd.most_common(fd.B()))
    for row_n, row in enumerate(result):
        result[row_n] = row + (row[1]/fd.N(),)
    return result

def form_bigrams(sections):
    full_tokens = []
    for section in sections:
        for pg, par in section.pages_paragraphs:
            tokens = list(re.split('\\s', par))
            for t_str in tokens:
                try: # can fail if something isn't a readable token
                    full_tokens.append(ParsedToken.from_str(t_str).form)
                except:
                    pass
    coll_finder = BigramCollocationFinder.from_words(full_tokens)
    coll_finder.apply_freq_filter(5)
    coll_finder.apply_word_filter(lambda w: len(w) < 3)
    result = coll_finder.score_ngrams(BigramAssocMeasures().raw_freq)
    # Join the word entries of the phrase.
    for row_n, row in enumerate(result):
        # the retrieved frequency will be an integer, but sometimes with a minor float corruption
        result[row_n] = (' '.join(row[0]), row[1], round(row[1] * len(full_tokens)))
    # Sort by frequency.
    result.sort(key=lambda x: x[1], reverse=True)
    return result

def form_trigrams(sections):
    full_tokens = []
    for section in sections:
        for pg, par in section.pages_paragraphs:
            tokens = list(re.split('\\s', par))
            for t_str in tokens:
                try: # can fail if something isn't a readable token
                    full_tokens.append(ParsedToken.from_str(t_str).form)
                except:
                    pass
    coll_finder = TrigramCollocationFinder.from_words(full_tokens)
    coll_finder.apply_freq_filter(5)
    coll_finder.apply_word_filter(lambda w: len(w) < 3)
    result = coll_finder.score_ngrams(TrigramAssocMeasures().raw_freq)
    # Join the word entries of the phrase.
    for row_n, row in enumerate(result):
        result[row_n] = (' '.join(row[0]), row[1], round(row[1] * len(full_tokens)))
    # Sort by frequency.
    result.sort(key=lambda x: x[1], reverse=True)
    return result

def lemma_bigrams(sections):
    full_tokens = []
    for section in sections:
        for pg, par in section.pages_paragraphs:
            tokens = list(re.split('\\s', par))
            for t_str in tokens:
                try: # can fail if something isn't a readable token
                    full_tokens.append(ParsedToken.from_str(t_str).lemma)
                except:
                    pass
    coll_finder = BigramCollocationFinder.from_words(full_tokens)
    coll_finder.apply_freq_filter(5)
    coll_finder.apply_word_filter(lambda w: len(w) < 3)
    result = coll_finder.score_ngrams(BigramAssocMeasures().raw_freq)
    # Join the word entries of the phrase.
    for row_n, row in enumerate(result):
        result[row_n] = (' '.join(row[0]), row[1], round(row[1] * len(full_tokens)))
    # Sort by frequency.
    result.sort(key=lambda x: x[1], reverse=True)
    return result

def lemma_trigrams(sections):
    full_tokens = []
    for section in sections:
        for pg, par in section.pages_paragraphs:
            tokens = list(re.split('\\s', par))
            for t_str in tokens:
                try: # can fail if something isn't a readable token
                    full_tokens.append(ParsedToken.from_str(t_str).lemma)
                except:
                    pass
    coll_finder = TrigramCollocationFinder.from_words(full_tokens)
    coll_finder.apply_freq_filter(5)
    coll_finder.apply_word_filter(lambda w: len(w) < 3)
    result = coll_finder.score_ngrams(TrigramAssocMeasures().raw_freq)
    # Join the word entries of the phrase.
    for row_n, row in enumerate(result):
        result[row_n] = (' '.join(row[0]), row[1], round(row[1] * len(full_tokens)))
    # Sort by frequency.
    result.sort(key=lambda x: x[1], reverse=True)
    return result

def apply_method(method_name, method_function, subset_index):
    makedirs('results/'+method_name, exist_ok=True)
    for (subset_name, sections) in subset_index:
        with open('results/{}/{}.csv'.format(method_name, subset_name), 'w+') as result_file:
            writer = csv.writer(result_file, delimiter='\t')
            writer.writerows(method_function(sections))
