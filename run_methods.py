import argparse
import datetime
import os
import yaml

from popbot_src.methods import apply_method, basic_stats, form_frequency, lemma_frequency, form_bigrams, form_trigrams, lemma_bigrams, lemma_trigrams, keywords_bigrams, keywords_trigrams
from popbot_src.meta_methods import keyword_distribution
from popbot_src.subset_getter import make_subset_index

argparser = argparse.ArgumentParser(description='Apply methods to the files and write results to the ./results/ directory.')
argparser.add_argument('file_list_path')
argparser.add_argument('--omit_suspicious_interps', '-s', action='store_true', help='Omit suspicious interpretations when counting lemma frequency.')
argparser.add_argument('--experiment_name', help='Use (possibly overwrite) an existing experiment name.')
argparser.add_argument('--skip_basic', action='store_true', help='Omit all the basic methods.')
argparser.add_argument('--skip_meta', action='store_true', help='Omit all the meta methods.')
argparser.add_argument('--dont_weight', action='store_true', help='Do not apply subcorpus weightings.')
args = argparser.parse_args()

profile_dir = 'profile'

# load date ranges from the profile:
with open(profile_dir + '/date_ranges.yaml') as dranges_file:
    date_ranges = yaml.load(dranges_file.read(), Loader=yaml.FullLoader)['ranges']
for di, date_range in enumerate(date_ranges):
    r1 = [int(e) for e in date_range[0].split('-')]
    r2 = [int(e) for e in date_range[1].split('-')]
    date_ranges[di] = [datetime.date(r1[2], r1[1], r1[0]), datetime.date(r2[2], r2[1], r2[0])]
# load attributes that will be indexed in the results:
with open(profile_dir + '/indexed_attributes.yaml') as attrs_file:
    indexed_attrs = yaml.load(attrs_file.read(), Loader=yaml.FullLoader)['attributes']
# load subcorpus weightings:
weightings = []
if not args.dont_weight:
    for root, dirs, files in os.walk(profile_dir + '/subcorpus_weights/'):
        for filename in files:
            if not filename.endswith('.yaml'):
                continue
            weighted_parameter = filename[:-len('.yaml')]
            with open(profile_dir + '/subcorpus_weights/'+filename) as weights_file:
                weightings.append((weighted_parameter,
                                   yaml.load(weights_file.read(), Loader=yaml.FullLoader)['weights']))
# load keyword categories:
# Categories are stored as tuples: (category_name, list of groups as lists of lemmas)
keyword_categories = []
top_dir = profile_dir+'/keyword_categories/'
for root, dirs, files in os.walk(top_dir):
    for filename in files:
        category_name = filename[:-len('.txt')]
        if category_name[0] == '_': # skip if starts with an underscore
            continue
        keyword_categories.append((category_name, []))
        with open(top_dir+filename) as category_file:
            for line in category_file:
                line_lemmas = line.strip().split()
                keyword_categories[-1][1].append(line_lemmas)

# a list of (name, sections):
subsets = make_subset_index(args.file_list_path, indexed_attrs,
                            date_ranges=date_ranges, subcorpus_weightings=weightings)

if args.experiment_name:
    experiment_name = args.experiment_name
else:
    experiment_name = datetime.datetime.now().isoformat()

method_options = {'omit_suspicious_interps': args.omit_suspicious_interps,
                  'profile_dir': profile_dir }

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
    for (category_name, groups) in keyword_categories:
        method_options['keyword_category'] = groups
        apply_method(experiment_name, 'keywords_bigr_'+category_name, keywords_bigrams,
                     subsets, method_options)
        apply_method(experiment_name, 'keywords_trigr_'+category_name, keywords_trigrams,
                     subsets, method_options)

if not args.skip_meta:
    keyword_distribution(experiment_name, [name for name, sections in subsets], method_options)
