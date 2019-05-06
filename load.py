import argparse, json, os, re
from collections import defaultdict
from load_helpers import heading_score, doc_beginning_score, is_meta_fragment, fuzzy_match

from section import Section
from manual_decision import MergeSectionDecision, SplitSectionDecision, DateDecision

argparser = argparse.ArgumentParser(description='Load and index an edition of sejmik resolutions from scanned pages.')
argparser.add_argument('config_file_path')
argparser.add_argument('--manual_decisions_file', '-m')

args = argparser.parse_args()

# Load the config
config = None
with open(args.config_file_path) as config_file:
    config = json.loads(config_file.read())

# Load the manual decisions.
manual_decisions = defaultdict(list) # page number -> a list of decisions
# TODO unsketch!
if args.manual_decisions_file:
    with open(args.manual_decisions_file) as decisions_file:
        for sth in decisions_file:
            date_dec = DateDecision(sth)
            section_dec = SplitSectionDecision(sth)
            section_dec = MergeSectionDecision(sth)
            manual_decisions[date_dec.pagenum].append(date_dec)
            manual_decisions[section_dec.pagenum].append(section_dec)

# Load all the files.
pages = [] # as lists of lines
for dirname, dirnames, filenames in os.walk(config['path']):
    filenames = sorted(filenames)
    for filename in filenames:
        if re.match('^'+config['prefix'], filename):
            file_number = int(re.search('\\d+', filename).group(0))
            with open(dirname + filename) as text_file:
                pages.append(text_file.read())

# Process content lines for files sequentially.
clear_document_data = { 'title': '' }
# (the current title is stored here in addition to the paragraph list)
current_document_data = clear_document_data
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
        commit_previous = False # we need to do that if we've encountered a heading
        new_title = False # we will store it here to set after commiting the previous one
        if is_meta_fragment(paragraph, config):
            section = Section.new(config, 'meta', [(page_n, paragraph)], len(sections))
            section.scan_pages = (page_n, page_n+1)
            # A meta section is one paragraph long and cannot be split, but it
            # can be merged.
            merged_with_previous = False
            for decision in page_decisions:
                # Merge decisions (it can be merged with the previous document).
                if (decision.decision_type == 'merge_sections' and latest_doc_section_n
                        and fuzzy_match(decision.from_title, '')
                        and fuzzy_match(decision.following_fragm, paragraph[:80])
                        and fuzzy_match(decision.preceding_fragm, sections[latest_doc_section_n].text[-80:])):
                    # Add both the title and the contents to the
                    # previous section.
                    additional_sections = sections[latest_doc_section_n].add_to_text(
                            current_document_paragraphs,
                            page_decisions, config, len(sections), current_document_id)
                    sections += additional_sections
                    current_document_id += len([sec for sec
                        in additional_sections if sec.section_type == 'document'])
                    merged_with_previous = True
            if not merged_with_previous:
                sections.append(section)
        else:
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
        # Commit the previous document, without what we decided to be a heading.
        if commit_previous:
            if len(current_document_paragraphs) > 1:
                section = Section.new(config, 'document',
                        [], # leave empty for now
                        len(sections),
                        document_id=current_document_id)

                # Apply corrections before adding the text and commiting
                # (split decisions will be applied then).
                corrected_date = False
                merged_with_previous = False
                for decision in page_decisions:
                    # Merge decisions.
                    if (decision.decision_type == 'merge_sections' and latest_doc_section_n
                            and fuzzy_match(decision.from_title, current_document_data['title'])
                            and fuzzy_match(decision.following_fragm, current_document_paragraphs[0][:80])
                            and fuzzy_match(decision.preceding_fragm,
                                sections[latest_doc_section_n].pages_paragraphs[-1][-80:])):
                        # Add both the title and the contents to the
                        # previous section.
                        additional_sections = sections[latest_doc_section_n].add_to_text(
                                current_document_paragraphs,
                                page_decisions, config, len(sections), current_document_id)
                        sections[latest_doc_section_n].scan_pages[1] = page_n # TODO what if splitted
                        sections += additional_sections
                        current_document_id += len([sec for sec
                            in additional_sections if sec.section_type == 'document'])
                        merged_with_previous = True
                    # Date decisions.
                    if decision.decision_type == 'date' and fuzzy_match(decision.from_title(), current_document_data['title']):
                        section.date = decision.date
                        corrected_date = True
                    # Pertinence decisions.
                    if decision.decision_type == 'pertinence' and fuzzy_match(decision.from_title, current_document_data['title']):
                        section.pertinence = decision.pertinence_status

                if not merged_with_previous:
                    # Finally add the text content.
                    additional_sections = section.add_to_text(
                            current_document_paragraphs,
                            page_decisions, config, len(sections), current_document_id)
                    sections += additional_sections
                    current_document_id += len([sec for sec
                        in additional_sections if sec.section_type == 'document'])
                    if not corrected_date:
                        section.guess_date()
                    latest_doc_section_n = len(sections)
                    sections.append(section)
                    current_document_id += 1
                current_document_paragraphs = [(page_n, new_title)]
            # If there is no document content, add it as a meta section.
            else:
                section = Section.new(config, 'meta', current_document_paragraphs, len(sections))
                sections.append(section)
            current_document_data = clear_document_data
            current_document_data['title'] = new_title
# If something remains in the document buffer, commit it.
if possible_heading:
    if config.ignore_page_ranges:
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
        print(row)
