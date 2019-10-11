import argparse
import datetime
import yaml

from popbot_src.methods import apply_method, basic_stats, form_frequency, lemma_frequency, form_bigrams, form_trigrams, lemma_bigrams, lemma_trigrams
from popbot_src.meta_methods import keyword_distribution
from popbot_src.subset_getter import make_subset_index

argparser = argparse.ArgumentParser(description='Apply methods to the files and write results to the ./results/ directory.')
argparser.add_argument('file_list_path')
argparser.add_argument('--omit_suspicious_interps', '-s', action='store_true', help='Omit suspicious interpretations when counting lemma frequency.')
argparser.add_argument('--experiment_name', help='Use (possibly overwrite) an existing experiment name.')
argparser.add_argument('--skip_basic', action='store_true', help='Omit all the basic methods.')
argparser.add_argument('--skip_meta', action='store_true', help='Omit all the meta methods.')
args = argparser.parse_args()

# load date ranges from the profile:
with open('profile/date_ranges.yaml') as dranges_file:
    date_ranges = yaml.load(dranges_file.read(), Loader=yaml.FullLoader)['ranges']
with open('profile/indexed_attributes.yaml') as attrs_file:
    indexed_attrs = yaml.load(attrs_file.read(), Loader=yaml.FullLoader)['attributes']

# a list of (name, sections):
subsets = make_subset_index(args.file_list_path, indexed_attrs, date_ranges=date_ranges)

if args.experiment_name:
    experiment_name = args.experiment_name
else:
    experiment_name = datetime.datetime.now().isoformat()

method_options = {'omit_suspicious_interps': args.omit_suspicious_interps,
                  'profile_dir': 'profile' }

if not args.skip_basic:
    for name, fun in [
            ('basic_stats', basic_stats),
            ('form_frequency', form_frequency),
            ('lemma_frequency', lemma_frequency),
            ('form_bigrams', form_bigrams),
            ('form_trigrams', form_trigrams),
            ('lemma_bigrams', lemma_bigrams),
            ('lemma_trigrams', lemma_trigrams),
            ]:
        apply_method(experiment_name, name, fun, subsets, method_options)

if not args.skip_meta:
    keyword_distribution(experiment_name, [name for name, sections in subsets], method_options)
