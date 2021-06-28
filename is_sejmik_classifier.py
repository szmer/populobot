import argparse
import csv
import json
import random

import onnxruntime as onnx_rt
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import StringTensorType
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from popbot_src.indexing_common import load_indexed

argparser = argparse.ArgumentParser(description='Train and use a model for classifying documents'
        ' as sejmik-issued (pertinent) ones and others.')
argparser.add_argument('command', help='Either train or annot.')
argparser.add_argument('model_path', help='The path to the model to write to/load from.')
argparser.add_argument('input', help='If train, a file tab-separated config, raw edition files and'
        ' author anottation files. If annot, a raw csv file to annotate.')

args = argparser.parse_args()

def section_ngrams(section, n=3):
    ngrams = []
    for pg, par in section.pages_paragraphs[:3]:
        for char_n in range(len(par)):
            if char_n + n <= len(par):
                ngrams.append(par[char_n:char_n+n])
    return ngrams

if args.command == 'train':
    samples = []
    labels = []
    with open(args.input) as inputs_file:
        reader = csv.reader(inputs_file, delimiter='\t')

        # Read our corpus of opening paragraphs with authorship annotations.
        for row in reader:
            with open(row[0]) as config_file:
                config = json.load(config_file)
            with open(row[1]) as sections_file:
                edition_sections = load_indexed(sections_file)
            authors = dict()
            with open(row[2]) as authors_file:
                reader = csv.reader(authors_file)
                for row in reader:
                    title = row[1]
                    authors[f'{row[0]}:::{title}'] = row[3]
            for sec in edition_sections:
                if sec.section_type != 'document':
                    continue
                samples.append(section_ngrams(sec))
                author = authors[f'{sec.inbook_document_id}:::{sec.title(config)}']
                if 'sejmik' in author:
                    labels.append(1)
                else:
                    labels.append(0)

        # Divide the corpus into the train and test subset.
        test_idxs = random.sample(range(len(samples)), int(len(samples)/15))
        train_samples = [s for (si, s) in enumerate(samples) if not si in test_idxs]
        train_labels = [l for (li, l) in enumerate(labels) if not li in test_idxs]
        test_samples = [s for (si, s) in enumerate(samples) if si in test_idxs]
        test_labels = [l for (li, l) in enumerate(labels) if li in test_idxs]

        # Vectorize the data, train and evaluate the model.
        vectorizer = CountVectorizer(
                    analyzer=lambda x: x, # we have the data already tokenized into ngrams
                    max_features=500,
                    binary=True, # ignore the exact frequency
                    min_df=int(len(train_samples)/20))
        train_sample_vecs = vectorizer.fit_transform(train_samples)
        regression = LogisticRegression(n_jobs=4, class_weight='balanced', solver='saga', max_iter=200)
        regression.fit(train_sample_vecs, train_labels)
        test_sample_vecs = vectorizer.transform(test_samples)
        print('Number of features', len(vectorizer.vocabulary_))
        print('Train accuracy', regression.score(train_sample_vecs, train_labels))
        print('Test accuracy', regression.score(test_sample_vecs, test_labels))

        # Save the model to disk.
        pipeline = Pipeline(steps=[
            ('vectorizer', vectorizer),
            ('regression', regression)
            ])
        initial_type = [
                ('ngrams', StringTensorType([None, 1])),
                ]
        model_onnx = convert_sklearn(pipeline, initial_types=initial_type)
        with open(args.model_path, 'wb+') as model_file:
            model_file.write(model_onnx.SerializeToString())
elif args.command == 'annot':
    with open(args.input) as sections_file:
        edition_sections = load_indexed(sections_file)
    sess = onnx_rt.InferenceSession(args.model_path)
    input_name = sess.get_inputs()[0].name
    label_name = sess.get_outputs()[0].name
    for sec in edition_sections:
        if sec.section_type != 'document':
            pred = sess.run([label_name], {input_name: section_ngrams(sec)})[0]
            sec.pertinence = int(pred) == 1
        for row in sec.row_strings():
            print(row)
else:
    raise NotImplementedError(f'Unknown command {args.command}')
