#
# Methods than depend on data from usic basic methods.
#
import os
from os import makedirs

def keyword_distribution(experiment_name, subset_names, method_options):
    """(dependent on lemma frequency)"""
    # Collect the lemma groups.
    #
    # Groups are stored as tuples: (group_name, list of lists of lemmas)
    groups = []
    top_dir = method_options['profile_dir']+'/lemma_groups/'
    for root, dirs, files in os.walk(top_dir):
        for filename in files:
            group_name = filename[:-len('.txt')]
            if group_name[0] == '_': # skip if starts with an underscore
                continue
            groups.append((group_name, []))
            with open(top_dir+filename) as group_file:
                for line in group_file:
                    line_lemmas = line.strip().split()
                    groups[-1][1].append(line_lemmas)
    # Collect and write data for keywords.
    #
    for subset_name in subset_names:
        # Copy the groups list and add a frequency counter to each individual lemma.
        # (Convert group tuples to list to allow modifying in place)
        group_freqs = [[group_name, [[(l, 0) for l in lemmas] for lemmas in lemma_groups]]
                        for (group_name, lemma_groups) in groups]
        with open('results/{}/lemma_frequency/{}.csv'.format(experiment_name, subset_name)) as subset_file:
            for line in subset_file:
                fields = line.strip().split('\t')
                row_lemma, row_freq = fields[0], int(fields[-2])
                for group_n, group_entry in enumerate(group_freqs):
                    for lemmas_n, lemmas in enumerate(group_entry[1]):
                        for lemma_n, lemma_entry in enumerate(lemmas):
                            if lemma_entry[0] == row_lemma:
                                group_freqs[group_n][1][lemmas_n][lemma_n] = (lemma_entry[0], lemma_entry[1]+row_freq)
        makedirs('results/{}/keyword_dist'.format(experiment_name), exist_ok=True)
        with open('results/{}/keyword_dist/{}.txt'.format(experiment_name, subset_name), 'w+') as subset_file:
            for group_entry in group_freqs:
                print('#'*10, file=subset_file)
                print('#'*10, file=subset_file)
                print('###{}'.format(group_entry[0]), file=subset_file)
                groups_sorted = sorted(group_entry[1],
                                       key=lambda lemmas: sum([l_entry[1] for l_entry in lemmas]),
                                       reverse=True)
                for lemmas in groups_sorted:
                    freq_sum = sum([l_entry[1] for l_entry in lemmas])
                    print('##{} etc. - {}'.format(lemmas[0][0], freq_sum), file=subset_file)
                    for lemma_entry in lemmas:
                        if lemma_entry[1] == 0:
                            continue
                        print('{} - {}'.format(lemma_entry[0], lemma_entry[1]), file=subset_file)

