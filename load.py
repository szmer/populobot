import json, os, re
from load_helpers import is_heading, is_meta_line
from sys import argv

if len(argv) != 3:
    print('USAGE: python3 load.py CONFIG_FILE')
    os.exit(-1)

config_file_path = argv[2]

# Load the config
config = None
with open(config_file_path) as config_file:
    config = json.loads(config_file.read())

# Section class template.
class Section():
    def __init__(self, section_type, section_title, section_contents, section_id, document_id=False):
        self.book_title = config['book_title']
        self.inbook_section_id = section_id
        self.inbook_document_id = document_id
        self.scan_pages = False
        self.book_pages = False
        self.section_title = section_title
        self.section_type = section_type
        self.date = False
        self.palatinate = config['palatinate']
        self.convent_location = config['convent_location']
        self.created_location = False
        self.author = config['default_convent_author']
        self.text = section_contents

# Load all the files.
pages = [] # as lists of lines
###line_lengths = []
for dirname, dirnames, filenames in os.walk(config['path']):
    filenames = sorted(filenames)
    for filename in filenames:
        if re.match('^'+config['prefix'], filename):
            file_number = int(filename[len(config['prefix']):])
            with open(filename) as text_file:
                page_lines = text_file.read().split('\n')
                pages.append(page_lines)
###
###                # Collect line lengths to figure out paragraph endings later.
###                for line in file_lines:
###                    if config['max_text_line_len'] and len(line) > config['max_text_line_len']:
###                        continue
###                    line_lenghts.append(len(line))
###
#### Inside paragraph line length. TODO make it work, placeholding for now
###in_paragraph_line_len = 
### NOTE for now we take it from config instead

# Process content lines for files sequentially.
current_section_type = 'document' # can be document or meta
current_paragraph_type = 'text' # can be text or heading
current_document_data = { 'title': '' }
current_document_section = ''
current_meta_section = ''
current_paragraph = ''
sections = []
current_document_id = 0 # section id is just len(sections)
for page_lines in pages:
    for line in page_lines:
        if current_paragraph == '':
            current_paragraph = line
        else:
            current_paragraph += ' ' + line

        # Meta sections detection (what is not dected as meta, will be document).
        if len(line) > config['max_nonmeta_line_len'] or is_meta_line(line, config):
            current_section_type = 'meta'

        # End paragraph - do the relevant thing with it.
        if line[-1] == '.' or len(line) < config['min_inparagraph_line_len']:
            # Add heading.
            if is_heading(current_paragraph, config):
                # We have a new heading/title - add the document section that just ended.
                if current_document_data['title'] != '': # not the start of the book
                    current_document_id += 1
                    section = Section('document', current_document_data['title'],
                                       current_document_section, current_document_id)
                    current_document_section = ''

                # Set the title for next document section.
                current_document_data['title'] = current_paragraph
            # Add paragraph to meta section content, and reset type to document.
            elif current_section_type == 'meta':
                if current_meta_section == '':
                    current_meta_section = current_paragraph
                else:
                    current_meta_section += '\\n' + current_paragraph
                # Be biased to reset section type to document.
                current_section_type = 'document'
            # Add paragraph to document section content, and commit meta section if needed.
            elif current_section_type == 'document':
                if current_document_section == '':
                    current_document_section = current_paragraph
                else:
                    current_document_section += '\\n' + current_paragraph
                # If there is something meta hanging around, commit it now.
                if current_meta_section != '':
                    # Create and append the meta section.
                    section = Section('meta', '', current_meta_section, len(sections))
                    sections.append(section)
                    current_meta_section = ''
            # Clear paragraph.
            current_paragraph = ''
    # End page - commit the meta section.
    if current_meta_section != '' or current_section_type == 'meta':
        # Add the last paragraph if necessary.
        if current_section_type == 'meta':
            if current_meta_section == '':
                current_meta_section = current_paragraph
            else:
                current_meta_section += '\\n' + current_paragraph
            # Clear paragraph.
            current_paragraph = ''
        # Create and append the meta section.
        section = Section('meta', '', current_meta_section, len(sections))
        sections.append(section)
        current_meta_section = ''
        # Always reset section type to document at the end of page.
        current_section_type = 'document'

# Commit whatever remains.
# (last document section)
if current_document_section != '':
    current_document_id += 1
    section = Section('document', current_document_data['title'],
                       current_document_section, current_document_id)
# (last meta section)
if current_meta_section != '':
    # Create and append the meta section.
    section = Section('meta', '', current_meta_section, len(sections))
    sections.append(section)

# Print collected sections as csv rows.
for section in sections:
    print(section.row_string())
