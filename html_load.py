import argparse
import json
import re
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
page_num = 0 # track it for wlkp_pdf structure

with open(config['html_file_path']) as html_file:
    doc = BeautifulSoup(html_file.read(), 'html.parser')
    container = doc.body.contents
    if 'text_section' in config and config['text_section']:
        container = doc.body.find('div')
    for html_par in container:
    # The config needs to specify one of the predefined structure types for
    # HTML docs: nowogr, wlkp_pdf, generic_doc.
        if config['structure'] == 'nowogr':
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
                current_pages_paragraphs = [(-1, html_par.text.strip())]
            # A meta section.
            elif len(html_par.findAll('b')) > 0:
                Section.new(config, 'meta', [(-1, html_par.text.strip())]).join_to_list(sections)
            elif html_par.name == 'p':
                if is_meta_fragment(html_par.text.strip(), config):
                    Section.new(config, 'meta', [(-1, html_par.text.strip())]).join_to_list(sections)
                else:
                    current_pages_paragraphs.append((-1, html_par.text.strip()))
        elif config['structure'] == 'generic_doc':
            if not isinstance(html_par, Tag):
                continue
            elif html_par.name == 'p':
                # A meta section.
                if len(html_par.findAll('b')) > 0:
                    Section.new(config, 'meta', [(-1, html_par.text.strip())]).join_to_list(sections)
                # A heading.
                elif len(html_par.findAll('i')) > 0:
                    # the second term should exclude the table of contents
                    if ('Wstęp' in html_par.text.strip()
                            or html_par.text.count('.') > 10
                            or not re.search('^\\d+\\.', html_par.text.strip())):
                        Section.new(config, 'meta', [(-1, html_par.text.strip())]).join_to_list(sections)
                        continue
                    if current_pages_paragraphs:
                        # Commit the previous document.
                        Section.new(config, 'document', current_pages_paragraphs,
                            document_id=current_document_id).join_to_list(sections)
                        current_document_id += 1
                    current_pages_paragraphs = [(-1, html_par.text.strip())]
                # Basically skip everything until we have a document title.
                elif len(current_pages_paragraphs) > 1:
                    current_pages_paragraphs.append((-1, html_par.text.strip()))
                else:
                    Section.new(config, 'meta', [(-1, html_par.text.strip())]).join_to_list(sections)
        elif config['structure'] == 'wlkp_pdf':
            if html_par.name == 'hr':
                page_num += 1
            if 'ignore_page_ranges' in config:
                for page_range in config['ignore_page_ranges']:
                    if page_num >= page_range[0] and page_num < page_range[1]:
                        continue
            if not isinstance(html_par, Tag):
                # Can be a meta section if we are at the start of the page.
                if page_num % 2 == 1 and html_par.previous_sibling.name == 'a':
                    Section.new(config, 'meta', [(-1, str(html_par).strip())]).join_to_list(sections)
                elif str(html_par).strip() != '':
                    current_pages_paragraphs.append((-1, str(html_par).strip()))
            elif html_par.name == 'i':
                # A heading.
                if re.search('^\\d+\\.', html_par.text.strip()):
                    if current_pages_paragraphs:
                        # Commit the previous document.
                        Section.new(config, 'document', current_pages_paragraphs,
                            document_id=current_document_id).join_to_list(sections)
                        current_document_id += 1
                    current_pages_paragraphs = [(-1, html_par.text.strip())]
                # A meta section.
                else:
                    Section.new(config, 'meta', [(-1, html_par.text.strip())]).join_to_list(sections)
        else:
            raise ValueError('{} is not a known structure type'.format(config['structure']))

# If something remains in the document buffer, commit it.
if len(current_pages_paragraphs) > 0:
    Section.new(config, 'document', current_pages_paragraphs,
        document_id=current_document_id).join_to_list(sections)

# Print collected sections as csv rows.
for section in sections:
    for row in section.row_strings():
        print(row)
