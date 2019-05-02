import json, os, re
from load_helpers import heading_score, doc_beginning_score, is_meta_fragment
from sys import argv, exit

from section import Section

if len(argv) != 2:
    print('USAGE: python3 load.py CONFIG_FILE')
    exit(-1)

config_file_path = argv[1]

# Load the config
config = None
with open(config_file_path) as config_file:
    config = json.loads(config_file.read())


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
for page in pages:
    paragraphs = page.split('\n\n')
    for paragraph in paragraphs:
        commit_previous = False # we need to do that if we've encountered a heading
        new_title = False # we will store it here to set after commiting the previous one
        if is_meta_fragment(paragraph, config):
            section = Section.new(config, 'meta', '', paragraph, len(sections))
            sections.append(section)
        else:
            # If it's not meta, handle the case where there might have been a heading previosly.
            # Note that all document paragraphs pass through here, unless they were identified as a heading right away.
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
            if heading_score_estimation > 0.0:
                commit_previous = True
                new_title = paragraph
                possible_heading = False
            else:
                previous_heading_score = heading_score_estimation
                possible_heading = paragraph
        # Commit the previous document, without what we decided to be a heading.
        if commit_previous:
            if current_document_data['title'] != '':
                section = Section.new(config, 'document', current_document_data['title'],
                                   current_document_section,#.replace('- ', ''),
                                   len(sections),
                                   document_id=current_document_id)
                sections.append(section)
                current_document_section = ''
                current_document_id += 1
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
