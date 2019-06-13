import csv, json, os, re, sys
from collections import defaultdict
from copy import copy
from itertools import chain
import yaml

from popbot_src.section import Section
from popbot_src.load_helpers import heading_score, doc_beginning_score, is_meta_fragment, fuzzy_match

def load_indexed(csv_file):
    edition_sections = []
    csv_reader = csv.reader(csv_file)
    for row in csv_reader:
        appended = False
        if len(edition_sections) > 0:
            appended = edition_sections[-1].append_csv_row(row)
        if not appended:
            section = Section.from_csv_row(row)
            edition_sections.append(section)
    return edition_sections 

def load_document_sections(csv_path, print_titles=False):
    with open(csv_path) as csv_file:
        edition_sections = load_indexed(csv_file)
    document_sections = []
    for section in edition_sections:
        if section.section_type == 'document':
            document_sections.append(section)
            if print_titles:
                print(section.title())
    return document_sections

def merge_possible(manual_decisions, page_paragraph):
    return (
        len([d for d in manual_decisions[page_paragraph[0]]
        if (d.decision_type=='merge_sections'
        and fuzzy_match(page_paragraph[1], d.from_title))])
        > 0)

def find_doc_and_merge(sections, pages_paragraphs, manual_decisions, meta_sections_buffer,
        config, current_document_id):
    """Find a document to merge to and merge, if there is a decision (check
    with merge_possible beforehand to save on computation). Note that splits
    can happen when merging, so additional indexing state arguments need to
    be provided."""
    bad_merge = False
    for doc_section in reversed(sections):
        if doc_section.section_type == 'document':
            try:
                additional_sections = doc_section.merge_if(
                        manual_decisions, pages_paragraphs,
                        meta_sections_buffer, config, current_document_id)
                bad_merge = False
                break
            except ValueError:
                bad_merge = True
                continue
    if bad_merge:
        raise RuntimeError('There was an unresolved merge decision.')
    return additional_sections

def commit_doc_with_decisions(config, sections, pages_paragraphs, manual_decisions,
    meta_sections_buffer, current_document_id, latest_doc_section_n):
    # See if we need merging.
    if merge_possible(manual_decisions, pages_paragraphs[0]):
        additional_sections = find_doc_and_merge(sections, pages_paragraphs, manual_decisions,
                meta_sections_buffer, config, current_document_id)
    else:
        additional_sections = False
    if additional_sections:
        if isinstance(additional_sections, list):
            for add_section in additional_sections:
                add_section.join_to_list(sections)
    # If not merged.
    else:
        section = Section.new(config, 'document',
                [], # leave empty for now
                document_id=current_document_id)
        # Apply corrections before adding the text and commiting
        # (split decisions will be applied then).
        corrected_date = False
        meta = False
        # Get page decisions for all the pages of the document.
        page_decisions = chain.from_iterable([manual_decisions[pn]
            for pn in range(pages_paragraphs[0][0], pages_paragraphs[-1][0]+1)])
        for decision in page_decisions:
            # Title form decisions.
            if (decision.decision_type == 'title_form'
                    and fuzzy_match(decision.from_title, pages_paragraphs[0][1])):
                pages_paragraphs[0] = (pages_paragraphs[0][0],
                        decision.to_title)
            # Section type decisions.
            if (decision.decision_type == 'type'
                    and decision.section_type == 'meta'
                    and fuzzy_match(decision.from_title, pages_paragraphs[0][1])):
                for (page, paragraph) in pages_paragraphs:
                    section = Section.new(config, 'meta', [(page, paragraph)])
                    meta_sections_buffer.append(section)
                meta = True
                break
            # Date decisions.
            if decision.decision_type == 'date' and fuzzy_match(decision.from_title, pages_paragraphs[0][1]):
                section.date = decision.date
                corrected_date = True
            # Pertinence decisions.
            if decision.decision_type == 'pertinence' and fuzzy_match(decision.from_title, pages_paragraphs[0][1]):
                section.pertinence = decision.pertinence_status
        # After applying decisions, if they do not include
        # changing the type to meta.
        if not meta:
            # Finally add the text content.
            additional_sections = section.add_to_text(
                    pages_paragraphs,
                    manual_decisions, meta_sections_buffer, config,
                    # indices need to be already incremented for the
                    # main section that we will add
                    current_document_id+1)
            if not corrected_date:
                section.guess_date()
            section.join_to_list(sections)
            # Operate on a copy, so we will ignore additional metas that will
            # be added downstream.
            for meta_section in copy(meta_sections_buffer):
                # See if needs to be merged to a recently
                # commited document section.
                if merge_possible(manual_decisions, meta_section.pages_paragraphs[0]):
                    meta_additional_sections = find_doc_and_merge(sections,
                            meta_section.pages_paragraphs, manual_decisions,
                            meta_sections_buffer, config, current_document_id)
                else:
                    meta_additional_sections = False
                if meta_additional_sections:
                    if isinstance(meta_additional_sections, list):
                        for add_section in meta_additional_sections:
                            add_section.join_to_list(sections)
                else:
                    meta_section.join_to_list(sections)
            # We need to do it this way to actually empty the provided list.
            del meta_sections_buffer[:]
            for add_section in additional_sections:
                add_section.join_to_list(sections)
            current_document_id += 1
            current_document_id += len([sec for sec
                in additional_sections if sec.section_type == 'document'])
            latest_doc_section_n = ''.join([s.section_type[0] for s in sections]).rfind('d')
    return current_document_id, latest_doc_section_n

def load_edition(config_file_path, manual_decisions_file=False, output_stream=sys.stdout):
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
            paragraph = paragraph.strip()
            if len(paragraph) == 0:
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
                        current_document_paragraphs.append((possible_heading_page, possible_heading))
                    possible_heading = False
                # Commit the previous document, without what we decided to be a heading.
                if commit_previous:
                    commit_previous = False
                    if len(current_document_paragraphs) > 0:
                        current_document_id, latest_doc_section_n = commit_doc_with_decisions(
                                config, sections, current_document_paragraphs, manual_decisions,
                                meta_sections_buffer, current_document_id, latest_doc_section_n)
                    current_document_paragraphs = [(possible_heading_page, new_title)]
                heading_score_estimation = heading_score(paragraph, config)
                previous_heading_score = heading_score_estimation
                possible_heading = paragraph
                possible_heading_page = page_n
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
