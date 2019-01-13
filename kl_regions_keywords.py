import csv, math, os, re
from sys import argv, exit

from nltk.tokenize import word_tokenize
from nltk.probability import FreqDist, DictionaryProbDist

if len(argv) != 4:
    print('USAGE: python3 kl_regions_keywords.py REGION1_CSV REGION2_CSV CHECKED_WORDS_COUNT')
    exit(-1)

region1_path = argv[1]
region2_path = argv[2]
checked_words_count = int(argv[3])

# These are used to find most common words.
region1_freqs = FreqDist()
region2_freqs = FreqDist()

# Collect word frequencies.
for (path, freqs) in [(region1_path, region1_freqs), (region2_path, region2_freqs)]:
    with open(path) as reg_file:
        csv_reader = csv.reader(reg_file)
        for row in csv_reader:
            if row[6] == 'document':
                text = row[12].replace('\\n', ' ')
                tokens = word_tokenize(text)
                for token in tokens:
                    if re.match('^\w+$', token):
                        token = token.lower()
                        freqs[token] += 1

# Select the words that will be checked.
region1_words = region1_freqs.most_common(checked_words_count)
region2_words = region2_freqs.most_common(checked_words_count)

# Collect KL divergences.
partial_kls_1 = dict()
partial_kls_2 = dict()

for (src_words, kls, src_freq, target_freq) in [(region1_words, partial_kls_1, region1_freqs, region2_freqs), (region2_words, partial_kls_2, region2_freqs, region1_freqs)]:
    for word in src_words:
        if src_freq.freq(word) > 0 and target_freq.freq(word) > 0:
            # Taken from Klingenstein et al. 2014
            p = src_freq.freq(word) / src_freq.N() 
            q = target_freq.freq(word) / target_freq.N()
            kls[word] = p * log((2*p) / (p + q))

# Print results.
sorted_kls_1 = sorted(list(partial_kls_1.items()), reverse=True, key=lambda x: x[1])
sorted_kls_2 = sorted(list(partial_kls_2.items()), reverse=True, key=lambda x: x[1])

print('Results for', region1_path)
for (word, kl) in sorted_kls_1:
    print('{}: {}'.format(word, kl))

print() # newline
print('Results for', region2_path)
for (word, kl) in sorted_kls_2:
    print('{}: {}'.format(word, kl))
