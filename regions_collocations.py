import csv, math, os, re
from sys import argv, exit

from nltk.tokenize import word_tokenize
from nltk.collocations import BigramCollocationFinder, BigramAssocMeasures, TrigramCollocationFinder, TrigramAssocMeasures

if len(argv) != 4:
    print('USAGE: python3 kl_regions_keywords.py REGION_CSV KEY_STRING MAX_COUNT')
    exit(-1)

region_path = argv[1]
key_string = argv[2]
max_count = int(argv[3])

all_tokens = []
with open(region_path) as reg_file:
    csv_reader = csv.reader(reg_file)
    for row in csv_reader:
        if row[6] == 'document':
            text = row[12].replace('\\n', ' ')
            tokens = word_tokenize(text)
            for token in tokens:
                if re.match('^\w+$', token):
                    token = token.lower()
                    all_tokens.append(token)

# Collocations
print('=== BIGRAMS ===')
coll_finder = BigramCollocationFinder.from_words(all_tokens)
###coll_finder.apply_word_filter(lambda w: w.upper() == w or '(' in w or ')' in w or len(w) < 4)
coll_finder.apply_freq_filter(2)
coll_scored = coll_finder.score_ngrams(BigramAssocMeasures().raw_freq)
coll_n = 1
for ((w1, w2), score) in sorted(((coll, score) for coll, score in coll_scored), key=lambda x: x[1], reverse=True):
    if key_string in w1 or key_string in w2:
        print('{}. {} {}: {:.9f}'.format(coll_n, w1, w2, score))
        if coll_n == max_count:
            break
        coll_n += 1

print('=== TRIGRAMS ===')
coll_finder = TrigramCollocationFinder.from_words(all_tokens)
###coll_finder.apply_word_filter(lambda w: w.upper() == w or '(' in w or ')' in w or len(w) < 4)
coll_finder.apply_freq_filter(2)
coll_scored = coll_finder.score_ngrams(TrigramAssocMeasures().raw_freq)
coll_n = 1
for ((w1, w2, w3), score) in sorted(((coll, score) for coll, score in coll_scored), key=lambda x: x[1], reverse=True):
    if key_string in w1 or key_string in w2 or key_string in w3:
        print('{}. {} {} {}: {:.9f}'.format(coll_n, w1, w2, w3, score))
        if coll_n == max_count:
            break
        coll_n += 1
