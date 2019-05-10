import argparse, json, os, re, sys
from itertools import chain
from collections import defaultdict
import yaml

from popbot_src.section import Section
from popbot_src.load_helpers import heading_score, doc_beginning_score, is_meta_fragment, fuzzy_match

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
    sections = []
    current_document_id = 0
    # We need to keep track of the latest document section, because we may want to
    # merge subsequent sections with it.
    latest_doc_section_n = False
    # Section id is just len(sections).
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
            meta = True
            if len(paragraph.strip()) == 0:
                continue
            commit_previous = False # we need to do that if we've encountered a heading
            new_title = False # we will store it here to set after commiting the previous one
            meta = False # depends on detection and possibly a manual decision
            if is_meta_fragment(paragraph, config):
                section = Section.new(config, 'meta', [(page_n, paragraph)], len(sections))
                # A meta section is one paragraph long and cannot be split, but it
                # can be merged.
                merged_with_previous = False
                for decision in page_decisions:
                    # Section type decisions.
                    if (decision.decision_type == 'type'
                            and decision.section_type == 'document'
                            and fuzzy_match(decision.from_title, paragraph)):
                        # This will send the paragraph to document paragraphs handling.
                        meta = False
                        break
                    # Merge decisions (it can be merged with the previous document).
                    if (decision.decision_type == 'merge_sections' and latest_doc_section_n
                            and fuzzy_match(decision.from_title, paragraph)
                            and fuzzy_match(decision.following_fragm, paragraph[:80])
                            and fuzzy_match(decision.preceding_fragm, sections[latest_doc_section_n].pages_paragraphs[-1][1][-80:])):
                        # Add both the title and the contents to the
                        # previous section.
                        additional_sections = sections[latest_doc_section_n].add_to_text(
                                [(page_n, paragraph)],
                                manual_decisions, config, len(sections), current_document_id)
                        sections += additional_sections
                        current_document_id += len([sec for sec
                            in additional_sections if sec.section_type == 'document'])
                        merged_with_previous = True
                    if (decision.decision_type == 'title_form' 
                            and fuzzy_match(decision.from_title, paragraph)):
                        section.pages_paragraphs[0] = (section.pages_paragraphs[0][0], decision.to_title)
                if meta and not merged_with_previous:
                    sections.append(section)
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
                if len(current_document_paragraphs) > 0:
                    section = Section.new(config, 'document',
                            [], # leave empty for now
                            len(sections),
                            document_id=current_document_id)

                    # Apply corrections before adding the text and commiting
                    # (split decisions will be applied then).
                    corrected_date = False
                    merged_with_previous = False
                    # Get page decisions for all the pages of the document.
                    page_decisions = chain.from_iterable([manual_decisions[pn]
                        for pn in range(current_document_paragraphs[0][0], page_n+1)])
                    for decision in page_decisions:
                        # Title form decisions.
                        if (decision.decision_type == 'title_form' 
                                and fuzzy_match(decision.from_title, current_document_paragraphs[0][1])):
                            current_document_paragraphs[0] = (current_document_paragraphs[0][0],
                                    decision.to_title)
                        # Section type decisions.
                        if (decision.decision_type == 'meta'
                                and decision.section_type == 'document'
                                and fuzzy_match(decision.from_title, paragraph)):
                            section = Section.new(config, 'meta', [(page_n, paragraph)], len(sections))
                            sections.append(section)
                            meta = True
                            break
                        # Merge decisions.
                        if (decision.decision_type == 'merge_sections' and latest_doc_section_n
                                and fuzzy_match(decision.from_title, current_document_paragraphs[0][1])
                                and fuzzy_match(decision.following_fragm, current_document_paragraphs[0][1][:80])
                                and fuzzy_match(decision.preceding_fragm,
                                    sections[latest_doc_section_n].pages_paragraphs[-1][1][-80:])):
                            # Add both the title and the contents to the
                            # previous section.
                            additional_sections = sections[latest_doc_section_n].add_to_text(
                                    current_document_paragraphs,
                                    manual_decisions, config, len(sections), current_document_id)
                            sections += additional_sections
                            current_document_id += len([sec for sec
                                in additional_sections if sec.section_type == 'document'])
                            merged_with_previous = True
                        # Date decisions.
                        if decision.decision_type == 'date' and fuzzy_match(decision.from_title, current_document_paragraphs[0][1]):
                            section.date = decision.date
                            corrected_date = True
                        # Pertinence decisions.
                        if decision.decision_type == 'pertinence' and fuzzy_match(decision.from_title, current_document_paragraphs[0][1]):
                            section.pertinence = decision.pertinence_status

                    if not merged_with_previous and not meta:
                        # Finally add the text content.
                        additional_sections = section.add_to_text(
                                current_document_paragraphs,
                                manual_decisions, config,
                                # indices need to be already incremented for the
                                # main section that we will add
                                len(sections)+1, current_document_id+1)
                        if not corrected_date:
                            section.guess_date()
                        sections.append(section)
                        current_document_id += 1
                        sections += additional_sections
                        current_document_id += len([sec for sec
                            in additional_sections if sec.section_type == 'document'])
                        latest_doc_section_n = ''.join([s.section_type[0] for s in sections]).rfind('d')
                current_document_paragraphs = [(possible_heading_page, new_title)]
    # If something remains in the document buffer, commit it.
    if possible_heading:
        if config['ignore_page_ranges']:
            last_page = config['ignore_page_ranges'][-1][0]
        else:
            last_page = len(pages) - 1
        current_document_paragraphs.append((last_page, paragraph))
    if len(current_document_paragraphs) > 0:
        section = Section.new(config, 'document',
                           current_document_paragraphs,
                           len(sections),
                           document_id=current_document_id)
        sections.append(section)

    # Print collected sections as csv rows.
    for section in sections:
        for row in section.row_strings():
            output_stream.write(row+'\n')

if __name__ == '__main__':
    args = argparser.parse_args()
    load(args.config_file_path, args.manual_decisions_file)
