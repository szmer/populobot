import argparse
import datetime

from popbot_src.methods import apply_method, basic_stats, form_frequency, lemma_frequency, form_bigrams, form_trigrams, lemma_bigrams, lemma_trigrams
from popbot_src.subset_getter import make_subset_index

argparser = argparse.ArgumentParser(description='Apply methods to the files and write results to the ./results/ directory.')
argparser.add_argument('file_list_path')
argparser.add_argument('--omit_suspicious_interps', '-s', action='store_true', help='Omit suspicious interpretations when counting lemma frequency.')

args = argparser.parse_args()

subsets = make_subset_index(args.file_list_path)

experiment_name = datetime.datetime.now().isoformat()
for name, fun in [
        ('basic_stats', basic_stats),
        ('form_frequency', form_frequency),
        ('lemma_frequency', lemma_frequency),
        ('form_bigrams', form_bigrams),
        ('form_trigrams', form_trigrams),
        ('lemma_bigrams', lemma_bigrams),
        ('lemma_trigrams', lemma_trigrams),
        ]:
    apply_method(experiment_name, name, fun, subsets, {'omit_suspicious_interps':'args.omit_suspicious_interps'})
