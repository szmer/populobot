import csv, math, os, re
from sys import argv, exit

from nltk.tokenize import word_tokenize
from nltk.probability import FreqDist, DictionaryProbDist
from matplotlib import pyplot as plt

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
                    if re.match('^\w+$', token) and len(token) > 4: # kludgy token length cutoff
                        token = token.lower()
                        freqs[token] += 1

# Select the words that will be checked.
region1_words = region1_freqs.most_common(checked_words_count)
region2_words = region2_freqs.most_common(checked_words_count)

# Collect KL divergences.
partial_kls_1 = dict()
partial_kls_2 = dict()

for (src_words, kls, src_freq, target_freq) in [(region1_words, partial_kls_1, region1_freqs, region2_freqs), (region2_words, partial_kls_2, region2_freqs, region1_freqs)]:
    for (word, _) in src_words:
        if target_freq.freq(word) > 0:
            # Taken from Klingenstein et al. 2014
            p = src_freq.freq(word) / src_freq.N() 
            q = target_freq.freq(word) / target_freq.N()
            kls[word] = p * math.log((2*p) / (p + q))
###        else:
###            kls[word] = 1.0

# Print results.
sorted_kls_1 = sorted(list(partial_kls_1.items()), reverse=True, key=lambda x: x[1])
sorted_kls_2 = sorted(list(partial_kls_2.items()), reverse=True, key=lambda x: x[1])

print('Results for', region1_path)
for (word, kl) in sorted_kls_1:
    print('{}: {:.9f}'.format(word, kl))
plotpoints_x = []
for (word, kl) in sorted_kls_1:
    plotpoints_x.append(kl)
fig = plt.figure(1, figsize=(9, 9), dpi=200)
fig.suptitle('{} ↹ {}'.format(region2_path, region1_path))
plt.hlines(0, -0.000000002, 0.000000002)
ax = fig.add_subplot(111)
plt.eventplot(plotpoints_x, orientation='horizontal', colors='b')
plt.rcParams.update({'font.size': 5})
for (wi, (word, kl)) in enumerate(sorted_kls_1):
    ax.annotate(word, (plotpoints_x[wi], 0.5), xytext=(plotpoints_x[wi], 0.12*(wi%4)),
                                               arrowprops={'arrowstyle': '-[' })
ax.ticklabel_format(useOffset=False)
plt.show()

###print() # newline
print('Results for', region2_path)
for (word, kl) in sorted_kls_2:
    print('{}: {:.9f}'.format(word, kl))
plotpoints_x = []
for (word, kl) in sorted_kls_2:
    plotpoints_x.append(kl)
fig = plt.figure(2, figsize=(9, 9), dpi=200)
fig.suptitle('{} ↹ {}'.format(region1_path, region2_path))
plt.hlines(0, -0.000000002, 0.000000002)
ax = fig.add_subplot(111)
plt.eventplot(plotpoints_x, orientation='horizontal', colors='b')
plt.rcParams.update({'font.size': 5})
for (wi, (word, kl)) in enumerate(sorted_kls_2):
    ax.annotate(word, (plotpoints_x[wi], 0.5), xytext=(plotpoints_x[wi], 0.12*(wi%4)),
                                               arrowprops={'arrowstyle': '-[' })
ax.ticklabel_format(useOffset=False)
plt.show()
