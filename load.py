import json, os, re
from load_helpers import is_heading, is_meta_fragment
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
current_document_data = { 'title': '' }
# We accumulate lines here until a heading or short line:
current_document_section = '' 
sections = []
current_document_id = 0
# section id is just len(sections)
for page in pages:
    paragraphs = page.split('\n\n')
    for paragraph in paragraphs:
        if is_meta_fragment(paragraph, config):
            section = Section.new(config, 'meta', '', paragraph, len(sections))
            sections.append(section)
        elif is_heading(paragraph, config):
            # Commit the previous document.
            if current_document_section != '':
                section = Section.new(config, 'document', current_document_data['title'],
                                   current_document_section,#.replace('- ', ''),
                                   len(sections),
                                   document_id=current_document_id)
                sections.append(section)
                current_document_section = ''
                current_document_id += 1
            current_document_data['title'] = paragraph
        else:
            if current_document_section != '':
                current_document_section += '\\n\\n' + paragraph
            else:
                current_document_section = paragraph
# If something remains in the document buffer, commit it.
if current_document_section != '':
    section = Section.new(config, 'document', current_document_data['title'],
                       current_document_section,#.replace('- ', ''),
                       len(sections),
                       document_id=current_document_id)
    sections.append(section)

# Print collected sections as csv rows.
for section in sections:
    print(section.row_string())
