import argparse, json, os, re, sys
from collections import defaultdict
import yaml

from popbot_src.section import Section
from popbot_src.load_helpers import heading_score, doc_beginning_score, is_meta_fragment, fuzzy_match
from popbot_src.indexing_common import commit_doc_with_decisions

argparser = argparse.ArgumentParser(description='Load and index an edition of sejmik resolutions from scanned pages.')
argparser.add_argument('config_file_path')
argparser.add_argument('--manual_decisions_file', '-m')

def load(config_file_path, manual_decisions_file=False, output_stream=sys.stdout):
    # Load the config
    config = None
    with open(config_file_path) as config_file:
        config = json.loads(config_file.read())

    # Load the manual decisions.
    manual_decisions = defaultdict(list) # page number -> a list of decisions
    if manual_decisions_file:
        with open(manual_decisions_file) as decisions_file:
            all_decisions = yaml.load(decisions_file, Loader=yaml.Loader)
            for decision in all_decisions:
                manual_decisions[decision.pagenum].append(decision)

    # Load all the files.
    pages = [] # as lists of lines
    for dirname, dirnames, filenames in os.walk(config['path']):
        filenames = sorted(filenames)
        for filename in filenames:
            if re.match('^'+config['prefix'], filename):
                with open(dirname + filename) as text_file:
                    pages.append(text_file.read())

    # Process content lines for files sequentially.
    # We accumulate lines here until a heading or short line:
    current_document_paragraphs = [] # pairs (pagenum, paragraph)
    # NOTE New sections should be added only with their join_to_list method.
    sections = []
    # Meta sections found after a title are added after the whole document, so
    # they can be merged if needed.
    meta_sections_buffer = []
    current_document_id = 0
    # We need to keep track of section index of the latest document section,
    # because we may want to merge subsequent sections to it.
    latest_doc_section_n = False
    # We keep the score to use it with beginning paragraph detection.
    previous_heading_score = 0
    possible_heading = False
    possible_heading_page = False
    for page_n, page in enumerate(pages):
        ignored_page = False
        if 'ignore_page_ranges' in config:
            for page_range in config['ignore_page_ranges']:
                if page_n >= page_range[0] and page_n < page_range[1]:
                    ignored_page = True
        if ignored_page:
            continue
        paragraphs = page.split('\n\n')
        page_decisions = manual_decisions[page_n]
        for paragraph in paragraphs:
            if len(paragraph.strip()) == 0:
                continue
            commit_previous = False # we need to do that if we've encountered a heading
            new_title = False # we will store it here to set after commiting the previous one
            meta = False # depends on detection and possibly a manual decision
            if is_meta_fragment(paragraph, config):
                meta = True
                section = Section.new(config, 'meta', [(page_n, paragraph)])
                # A meta section is one paragraph long and cannot be split, but it
                # can be merged.
                for decision in page_decisions:
                    # Section type decisions.
                    if (decision.decision_type == 'type'
                            and decision.section_type == 'document'
                            and fuzzy_match(decision.from_title, paragraph)):
                        # This will send the paragraph to document paragraphs handling.
                        meta = False
                        break
                    # Title form decisions.
                    if (decision.decision_type == 'title_form' 
                            and fuzzy_match(decision.from_title, paragraph)):
                        section.pages_paragraphs[0] = (section.pages_paragraphs[0][0], decision.to_title)
                if meta:
                    meta_sections_buffer.append(section)
            if not meta:
                # If it's not meta, handle the case where there might have been a heading previosly.
                # Note that all document paragraphs pass through here
                if possible_heading:
                    if previous_heading_score + doc_beginning_score(paragraph, config) > 0:
                        commit_previous = True
                        new_title = possible_heading
                        # The new title will be added to the next document's paragraphs
                        # when we commit the current one.
                    # If there's no chance for a heading, add it to the current
                    # document section.
                    else:
                        # Since the section wasn't yet created, we don't need to go
                        # through the .add_text Section method, it will be called later
                        current_document_paragraphs.append((page_n, possible_heading))
                    possible_heading = False
                heading_score_estimation = heading_score(paragraph, config)
                previous_heading_score = heading_score_estimation
                possible_heading = paragraph
                possible_heading_page = page_n
            # Commit the previous document, without what we decided to be a heading.
            if commit_previous:
                commit_previous = False
                if len(current_document_paragraphs) > 0:
                    current_document_id, latest_doc_section_n = commit_doc_with_decisions(
                            config, sections, current_document_paragraphs, manual_decisions,
                            meta_sections_buffer, current_document_id, latest_doc_section_n)
                current_document_paragraphs = [(possible_heading_page, new_title)]
    # If something remains in the document buffer, commit it.
    if possible_heading:
        if config['ignore_page_ranges']:
            last_page = config['ignore_page_ranges'][-1][0]
        else:
            last_page = len(pages) - 1
        current_document_paragraphs.append((last_page, paragraph))
    if len(current_document_paragraphs) > 0:
        current_document_id, latest_doc_section_n = commit_doc_with_decisions(
                config, sections, current_document_paragraphs, manual_decisions,
                meta_sections_buffer, current_document_id, latest_doc_section_n)

    # Print collected sections as csv rows.
    for section in sections:
        for row in section.row_strings():
            output_stream.write(row+'\n')

if __name__ == '__main__':
    args = argparser.parse_args()
    load(args.config_file_path, args.manual_decisions_file)
