import argparse
from cltk.corpus.utils.importer import CorpusImporter

corpus_importer = CorpusImporter('latin')
corpus_importer.import_corpus('latin_models_cltk')

from cltk.stem.latin.declension import CollatinusDecliner
decliner = CollatinusDecliner()
import cltk.exceptions


argparser = argparse.ArgumentParser(description='Read a list of Latin lemmas and expand them into lists of forms.')
argparser.add_argument('filepath')

args = argparser.parse_args()

with open(args.filepath) as lemmas_file:
    for line in lemmas_file:
        lemmas = line.strip().split()
        forms = []
        for lemma in lemmas:
            try:
                forms += list(set(decliner.decline(lemma, flatten=True)))
            except cltk.exceptions.UnknownLemma as e:
                print('!!!!!'+str(e))
        if forms:
            print(' '.join(forms))
