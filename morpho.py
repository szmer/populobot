import argparse

from popbot_src.indexing_common import load_indexed
from popbot_src.parsing import parse_sentences
from popbot_src.load_helpers import join_linebreaks

argparser = argparse.ArgumentParser(description='Tag an indexed edition file with Morfeusz. You need to have morfeusz_analyzer and an appropriate Morfeusz dictionary.')
argparser.add_argument('indexed_file_path')
argparser.add_argument('--strip_meta', action='store_true')
argparser.add_argument('--leave_hyphens', action='store_true',
        help="Don't join the word broken by lines with hyphens")
argparser.add_argument('--start_section', type=int, default=-1)

args = argparser.parse_args()
start_section = False

with open(args.indexed_file_path) as indexed_file:
    sections = load_indexed(indexed_file)

section_counter = -1
for section in sections:
    section_counter += 1
    if section_counter < args.start_section:
        continue
    if section.section_type == 'document':
        new_pages_paragraphs = []
        for (page, paragraph) in section.pages_paragraphs:
            if len(paragraph.strip()) == 0:
                continue
            if not args.leave_hyphens:
                paragraph = join_linebreaks(paragraph)
            parsed_sentences = parse_sentences(paragraph)
            parsed_paragraph = ''
            for sent in parsed_sentences:
                parsed_paragraph += ' '.join([repr(token) for token in sent]) + '\n'
            new_pages_paragraphs.append((page, parsed_paragraph))
        section.pages_paragraphs = new_pages_paragraphs
    if args.strip_meta and section.section_type == 'meta':
        continue
    for row in section.row_strings():
        print(row)
