from collections import defaultdict
import json
import re
import yaml
from copy import copy
from itertools import chain

from popbot_src.section import Section, tuple_to_datetime, transfer_pause_data
from popbot_src.load_helpers import fuzzy_match, is_pertinent
from popbot_src.parsed_token import ParsedToken

def read_config_file(config_file_path):
    with open(config_file_path) as config_file:
        return json.load(config_file)

def read_manual_decisions(manual_decisions_file):
    manual_decisions = defaultdict(list) # page number -> a list of decisions
    with open(manual_decisions_file) as decisions_file:
        all_decisions = yaml.load(decisions_file, Loader=yaml.Loader)
        for decision in all_decisions:
            manual_decisions[decision.pagenum].append(decision)
    return manual_decisions

def apply_decisions1(sections, manual_decisions, config):
    "Apply some types of decisions to already read sections."
    meta_inserts = [] # tuples (index, list of meta sections)
    for section_n, section in enumerate(sections):
        pages_paragraphs = section.pages_paragraphs
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
                meta_inserts.append([section_n, []])
                for (page, paragraph) in pages_paragraphs[1:]:
                    meta_inserts[-1][1].append(Section.new(config, 'meta', [(page, paragraph)]))
                meta_inserts[-1] = tuple(meta_inserts[-1])
            # Date decisions.
            if decision.decision_type == 'date' and fuzzy_match(decision.from_title, pages_paragraphs[0][1]):
                section.date = tuple_to_datetime(decision.date)
            # Pertinence decisions.
            if decision.decision_type == 'pertinence' and fuzzy_match(decision.from_title, pages_paragraphs[0][1]):
                section.pertinence = decision.pertinence_status
            # Merge, split decisions. TODO
    # Add the splitted meta sections.
    index_shift = 0
    for index, meta_sections in meta_inserts:
        for meta_sec in meta_sections:
            sections[index].insert(index+index_shift)
            index_shift += 1
    # Renumber all sections.
    doc_section_n = 0
    for section_n, section in enumerate(sections):
        section.inbook_section_id = section_n
        if section.section_type == 'document':
            section.inbook_document_id = doc_section_n
            doc_section_n += 1
    return sections

#
# Functions for loading files from edition texts.
#

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
        corrected_pertinence = False
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
                section.date = tuple_to_datetime(decision.date)
                corrected_date = True
            # Pertinence decisions.
            if decision.decision_type == 'pertinence' and fuzzy_match(decision.from_title, pages_paragraphs[0][1]):
                section.pertinence = decision.pertinence_status
                corrected_pertinence = True
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
            if not corrected_pertinence:
                section.pertinence = is_pertinent(section, config)
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

def editions_transfer_pause_data(parsed_edition, raw_edition):
    assert len(parsed_edition) == len(raw_edition)
    for parsed_section, raw_section in zip(parsed_edition, raw_edition):
        if parsed_section.section_type != 'document':
            continue
        transfer_pause_data(parsed_section, raw_section)

def section_paragraphs_to_tokens(sections):
    for section in sections:
        if section.section_type != 'document':
            continue
        for par_n, (pg, par) in enumerate(section.pages_paragraphs):
            tokens = re.split('\\s', par)
            tokens = [ParsedToken.from_str(t_str) for t_str in tokens if t_str.strip() != '']
            section.pages_paragraphs[par_n] = (pg, tokens)
    return sections
