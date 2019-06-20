import argparse
import pexpect

from popbot_src.indexing_common import load_indexed
from popbot_src.parsing import parse_sentences

argparser = argparse.ArgumentParser(description='Tag an indexed edition file with Morfeusz. You need to have morfeusz_analyzer and an appropriate Morfeusz dictionary.')
argparser.add_argument('dict_dir')
argparser.add_argument('dict_name')
argparser.add_argument('concraft_model_path')
argparser.add_argument('indexed_file_path')
argparser.add_argument('strip_meta', action='store_true')

args = argparser.parse_args()

with open(args.indexed_file_path) as indexed_file:
    sections = load_indexed(indexed_file)

morfeusz_analyzer = pexpect.spawn('morfeusz_analyzer --dict-dir {} -d {}'.format(args.dict_dir, args.dict_name))
pexp_result = morfeusz_analyzer.expect(['Using dictionary: [^\\n]*$', pexpect.EOF, pexpect.TIMEOUT])
if pexp_result != 0:
    raise RuntimeError('cannot run morfeusz_analyzer properly')

for section in sections:
    if section.section_type == 'document':
        new_pages_paragraphs = []
        for (page, paragraph) in section.pages_paragraphs:
            parsed_sentences = parse_sentences(morfeusz_analyzer, args.concraft_model_path, paragraph)
            parsed_paragraph = ''
            for sent in parsed_sentences:
                parsed_paragraph += ' '.join([':'.join(interp) for interp in sent]) + '\n'
            new_pages_paragraphs.append((page, parsed_paragraph))
        section.pages_paragraphs = new_pages_paragraphs
    if args.strip_meta and section.section_type == 'meta':
        continue
    for row in section.row_strings():
        print(row)
