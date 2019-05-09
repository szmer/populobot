import csv
from popbot_src.section import Section

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
