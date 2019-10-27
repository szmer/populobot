#
# Methods than depend on data from usic basic methods.
#
import os
from os import makedirs

# TODO: integrate into methods.py and preloading profile in running script
#

def keyword_distribution(experiment_name, subset_names, method_options):
    """Count occurences of keyword lemmas configured in profile (using lemma frequency)."""
    # Collect the lemma categories.
    #
    # Categories are stored as tuples: (category_name, list of lists of lemmas)
    categories = []
    top_dir = method_options['profile_dir']+'/keyword_categories/'
    for root, dirs, files in os.walk(top_dir):
        for filename in files:
            category_name = filename[:-len('.txt')]
            if not filename.endswith('.txt') or category_name[0] == '_': # skip if starts with an underscore
                continue
            categories.append((category_name, []))
            with open(top_dir+filename) as category_file:
                for line in category_file:
                    line_lemmas = line.strip().split()
                    categories[-1][1].append(line_lemmas)
    # Collect and write data for keywords.
    #
    for subset_name in subset_names:
        # Copy the categories list and add a frequency counter to each individual lemma.
        # (Convert category tuples to list to allow modifying in place)
        category_freqs = [[category_name, [[(l, 0) for l in lemmas] for lemmas in lemma_categories]]
                        for (category_name, lemma_categories) in categories]
        with open('results/{}/lemma_frequency/{}.csv'.format(experiment_name, subset_name)) as subset_file:
            for line in subset_file:
                fields = line.strip().split('\t')
                row_lemma, row_freq = fields[0], int(fields[-2])
                for category_n, category_entry in enumerate(category_freqs):
                    for lemmas_n, lemmas in enumerate(category_entry[1]):
                        for lemma_n, lemma_entry in enumerate(lemmas):
                            if lemma_entry[0] == row_lemma:
                                category_freqs[category_n][1][lemmas_n][lemma_n] = (lemma_entry[0], lemma_entry[1]+row_freq)
        makedirs('results/{}/keyword_dist'.format(experiment_name), exist_ok=True)
        with open('results/{}/keyword_dist/{}.txt'.format(experiment_name, subset_name), 'w+') as subset_file:
            for category_entry in category_freqs:
                print('#'*10, file=subset_file)
                print('#'*10, file=subset_file)
                print('###{}'.format(category_entry[0]), file=subset_file)
                categories_sorted = sorted(category_entry[1],
                                       key=lambda lemmas: sum([l_entry[1] for l_entry in lemmas]),
                                       reverse=True)
                for lemmas in categories_sorted:
                    freq_sum = sum([l_entry[1] for l_entry in lemmas])
                    print('##{} etc. - {}'.format(lemmas[0][0], freq_sum), file=subset_file)
                    # Sort lemmas in that category.
                    lemmas = sorted(lemmas, key=lambda x: x[1], reverse=True)
                    for lemma_entry in lemmas:
                        if lemma_entry[1] == 0:
                            continue
                        print('{} - {}'.format(lemma_entry[0], lemma_entry[1]), file=subset_file)
