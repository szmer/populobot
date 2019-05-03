import argparse, json, os, re
from collections import defaultdict
from load_helpers import heading_score, doc_beginning_score, is_meta_fragment, fuzzy_match

from section import Section
from manual_decision import SectionDecision, DateDecision

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
            section_dec = SectionDecision(sth)
            manual_decisions[date_dec.pagenum].append(date_dec)
            manual_decisions[section_dec.pagenum].append(section_dec)

# Load all the files.
pages = [] # as lists of lines
for dirname, dirnames, filenames in os.walk(config['path']):
    filenames = sorted(filenames)
    for filename in filenames:
        if re.match('^'+config['prefix'], filename):
            file_number = int(re.search('\\d+', filename).group(0))
            ignored = False
            if 'ignore_page_ranges' in config:
                for page_range in config['ignore_page_ranges']:
                    if file_number >= page_range[0] and file_number < page_range[1]:
                        ignored = True
            if not ignored:
                with open(dirname + filename) as text_file:
                    pages.append(text_file.read())

# Process content lines for files sequentially.
clear_document_data = { 'title': '' }
current_document_data = clear_document_data
# We accumulate lines here until a heading or short line:
current_document_section = '' 
sections = []
current_document_id = 0
# Section id is just len(sections).
previous_heading_score = 0 # we keep it so it can be improved by beginning paragraph detection.
possible_heading = False
for page_n, page in enumerate(pages):
    paragraphs = page.split('\n\n')
    page_decisions = manual_decisions[page_n]
    for paragraph in paragraphs:
        commit_previous = False # we need to do that if we've encountered a heading
        new_title = False # we will store it here to set after commiting the previous one
        if is_meta_fragment(paragraph, config):
            section = Section.new(config, 'meta', '', paragraph, len(sections))
            sections.append(section)
        else:
            # If it's not meta, handle the case where there might have been a heading previosly.
            # Note that all document paragraphs pass through here
            if possible_heading:
                if previous_heading_score + doc_beginning_score(paragraph, config) > 0:
                    commit_previous = True
                    new_title = possible_heading
                # If there's no chance for a heading, add it to the current document section.
                else:
                    if current_document_section != '':
                        current_document_section += '\\n\\n' + possible_heading
                    else:
                        current_document_section = possible_heading
                possible_heading = False
            heading_score_estimation = heading_score(paragraph, config)
            previous_heading_score = heading_score_estimation
            possible_heading = paragraph
        # Commit the previous document, without what we decided to be a heading.
        if commit_previous:
            if current_document_data['title'] != '':
                if current_document_section != '':
                    section = Section.new(config, 'document', current_document_data['title'],
                                       current_document_section,#.replace('- ', ''),
                                       len(sections),
                                       document_id=current_document_id)
                    corrected_date = False
                    for decision in page_decisions:
                        if decision.decision_type == 'date' and fuzzy_match(decision.from_title(), current_document_data['title']):
                            section.date = decision.date
                            corrected_date = True
                    if not corrected_date:
                        section.guess_date()
                    sections.append(section)
                    current_document_section = ''
                    current_document_id += 1
                # If there is no document content, add it as a meta section.
                else:
                    section = Section.new(config, 'meta', current_document_data['title'], '', len(sections))
                    sections.append(section)
                current_document_data = clear_document_data
            current_document_data['title'] = new_title
# If something remains in the document buffer, commit it.
if possible_heading:
    if current_document_section != '':
        current_document_section += '\\n\\n' + paragraph
    else:
        current_document_section = paragraph
if current_document_section != '':
    section = Section.new(config, 'document', current_document_data['title'],
                       current_document_section,#.replace('- ', ''),
                       len(sections),
                       document_id=current_document_id)
    sections.append(section)

# Print collected sections as csv rows.
for section in sections:
    print(section.row_string())
