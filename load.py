import json, os, re
from load_helpers import is_heading, is_meta_line
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
            if 'ignore_page_ranges' in config:
                for page_range in config['ignore_page_ranges']:
                    if file_number >= page_range[0] and file_number < page_range[1]:
                        continue
            with open(dirname + filename) as text_file:
                page_lines = text_file.read().split('\n')
                pages.append(page_lines)

# Process content lines for files sequentially.
current_section_type = 'document' # can be document or meta
current_paragraph_type = 'text' # can be text or heading
current_document_data = { 'title': '' }
current_document_section = ''
current_meta_section = ''
current_paragraph = '' # we accumulate lines here until a heading or short line
sections = []
current_document_id = 0
# section id is just len(sections)
previous_was_heading = False # indicates whether the last line was a heading
for page_lines in pages:
    for line in page_lines:
        line = line.strip()
        if current_paragraph == '':
            current_paragraph = line
        else:
            current_paragraph += ' ' + line

        # Meta sections detection (what is not detected as meta, will be document).
        # First, we determine whether the line is meta - if not, it may be heading or
        # be just a regular document fragment.
        if (len(line) > config['max_nonmeta_line_len'] or is_meta_line(line, config)):
            current_section_type = 'meta'
            a_heading = False
        else:
            a_heading = is_heading(current_paragraph, config)
###        if a_heading:
###            print(current_paragraph, ' is a heading')
###        else:
###            print(current_paragraph, ' not a heading')

        # End paragraph - do the relevant thing with it.
        if len(line) == 0 or (line[-1] == '.' or len(line) < config['min_inparagraph_line_len']):
            # Add heading.
            if a_heading:
                # We have a new heading/title - add the document section that just ended.
                ###print(current_document_section[:29], previous_was_heading, current_document_data['title'])
                if (not previous_was_heading) and current_document_data['title'] != '': # not the start of the book
                    current_document_id += 1
                    section = Section('document', current_document_data['title'],
                                       current_document_section.replace('- ', ''),
                                       len(sections),
                                       document_id=current_document_id)
                    sections.append(section)
                    current_document_data['title'] = ''
                    current_document_section = ''
                # Set the title for next document section.
                if previous_was_heading: # append to the previous part of the heading
                    current_document_data['title'] += '\\n' + current_paragraph
                else:
                    current_document_data['title'] = current_paragraph
                previous_was_heading = True
            else:
                previous_was_heading = False

            # Add paragraph to meta section content, and reset type to document.
            if (not a_heading) and current_section_type == 'meta':
                if current_meta_section == '':
                    current_meta_section = current_paragraph
                else:
                    current_meta_section += '\\n' + current_paragraph
                # Be biased to reset section type to document.
                current_section_type = 'document'
            # Add paragraph to document section content, and commit meta section if needed.
            elif (not a_heading) and current_section_type == 'document':
###                print('commiting on line', line)
                if current_document_section == '':
                    current_document_section = current_paragraph
                else:
                    current_document_section += '\\n' + current_paragraph
                # If there is something meta hanging around, commit it now.
                if current_meta_section != '':
                    # Create and append the meta section.
                    section = Section('meta', '', current_meta_section.replace('- ', ''), len(sections))
                    sections.append(section)
                    current_meta_section = ''
            # Clear paragraph.
            current_paragraph = ''
    # End of the page file - commit the meta section.
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
        section = Section('meta', '', current_meta_section.replace('- ', ''), len(sections))
        sections.append(section)
        current_meta_section = ''
        # Always reset section type to document at the end of page.
        current_section_type = 'document'

# Commit whatever remains.
# (last document section)
if current_document_section != '':
    current_document_id += 1
    section = Section('document', current_document_data['title'],
                       current_document_section.replace('- ', ''), current_document_id)
# (last meta section)
if current_meta_section != '':
    # Create and append the meta section.
    section = Section('meta', '', current_meta_section.replace('- ', ''), len(sections))
    sections.append(section)

# Print collected sections as csv rows.
for section in sections:
    print(section.row_string())
