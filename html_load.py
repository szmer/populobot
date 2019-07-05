import argparse
import json
from bs4 import BeautifulSoup, Tag

from popbot_src.section import Section
from popbot_src.load_helpers import is_meta_fragment

argparser = argparse.ArgumentParser(description='Load and index an edition of sejmik resolutions from a HTML doc exported from LibreOffice writer.')
argparser.add_argument('config_file_path')
argparser.add_argument('--strip_ruthenian', action='store_true')

args = argparser.parse_args()

with open(args.config_file_path) as config_file:
    config = json.load(config_file)

sections = []
current_pages_paragraphs = []
current_document_id = 0

with open(config['html_file_path']) as html_file:
    doc = BeautifulSoup(html_file.read(), 'html.parser')
    for html_par in doc.body.contents:
        if not isinstance(html_par, Tag):
            continue
        if args.strip_ruthenian and len(html_par.findAll(attrs={'lang': 'ru-RU'})) > 0:
            continue
        # A heading.
        if html_par.name == 'ol' and len(html_par.findAll('li')) == 1:
            if current_pages_paragraphs:
                # Commit the previous document.
                Section.new(config, 'document', current_pages_paragraphs,
                    document_id=current_document_id).join_to_list(sections)
                current_document_id += 1
            current_pages_paragraphs = [(-1, html_par.text)]
        # A meta section.
        elif len(html_par.findAll('b')) > 0:
            Section.new(config, 'meta', [(-1, html_par.text)]).join_to_list(sections)
        elif html_par.name == 'p':
            if is_meta_fragment(html_par.text, config):
                Section.new(config, 'meta', [(-1, html_par.text)]).join_to_list(sections)
            else:
                current_pages_paragraphs.append((-1, html_par.text))

# If something remains in the document buffer, commit it.
if len(current_pages_paragraphs) > 0:
    Section.new(config, 'document', current_pages_paragraphs,
        document_id=current_document_id).join_to_list(sections)

# Print collected sections as csv rows.
for section in sections:
    for row in section.row_strings():
        print(row)
