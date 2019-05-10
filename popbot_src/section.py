import csv, io
from popbot_src.load_helpers import extract_dates, fuzzy_match

# Section class template.
class Section():
    def row_strings(self):
        rows = []
        for scan_page, paragraph in self.pages_paragraphs:
            string_output = io.StringIO()
            csv_writer = csv.writer(string_output, quoting=csv.QUOTE_NONNUMERIC)
            csv_writer.writerow([
                self.book_title,
                self.inbook_section_id,
                self.inbook_document_id,
                scan_page,
                self.section_type,
                self.date,
                self.palatinate,
                self.convent_location,
                self.created_location,
                self.author,
                paragraph,
                self.pertinence
                ])
            rows.append(string_output.getvalue().strip())
        return rows

    def collapsed_text(self):
        return '\n\n'.join([par for (pg, par) in self.pages_paragraphs[1:]])

    def title(self):
        if len(self.pages_paragraphs) > 0:
            return self.pages_paragraphs[0][1]
        else:
            return ''

    def start_page(self):
        return self.pages_paragraphs[0][0]

    def end_page(self):
        return self.pages_paragraphs[-1][0]

    def join_to_list(self, sections_list):
        self.inbook_section_id = len(sections_list)
        sections_list.append(self)

    def add_to_text(self, new_pages_paragraphs, manual_decisions, meta_sections_buffer, config, document_n):
        """Add the new_text to section text. If there are new sections splitted,
        they are returned as a list. The dictionary of all manual decisions
        should be supplied as an argument."""
        additional_sections = []
        split_decisions = []
        for page_n in set([page_n for (page_n, par) in new_pages_paragraphs]):
            for decision in manual_decisions[page_n]:
                if decision.decision_type=='split_sections':
                    split_decisions.append(decision)
        # Add own last paragraph for context checking.
        pages_paragraphs = (self.pages_paragraphs[-1:] if len(self.pages_paragraphs) > 0 else [(0, '')]) + new_pages_paragraphs
        split = False # indicates whether we need to place next parags in additional sections
        current_document_n = document_n
        # After a split, we want to keep adding to the recent document section, but not any meta one.
        recipient_document_n = 0
        for parag_n, (scan_page, paragraph) in enumerate(pages_paragraphs):
            # We need the first paragraph only for checking the end of existing text.
            if parag_n == 0:
                continue
            for decision in split_decisions:
                if fuzzy_match(decision.following_fragm, paragraph[:80]):
                    new_doc = False
                    if decision.new_section_type == 'document':
                        new_section = Section.new(config, 'document',
                                [(scan_page, paragraph)],
                                document_id=current_document_n)
                        current_document_n += 1
                        recipient_document_n = len(additional_sections)
                        split = True
                        new_doc = True
                    elif decision.new_section_type == 'meta':
                        new_section = Section.new(config, 'meta',
                                [(scan_page, paragraph)])
                    else:
                        raise NotImplementedError('requested section split with unknown section'
                                ' type {}'.format(decision.new_section_type))
                    # Check if there is a title form decision for this new section.
                    for page_decision in manual_decisions[new_section.pages_paragraphs[0][0]]:
                        if (page_decision.decision_type == 'title_form'
                                and fuzzy_match(new_section.pages_paragraphs[0][1], page_decision.from_title)):
                            new_section.pages_paragraphs[0] = (new_section.pages_paragraphs[0][0],
                                    page_decision.to_title)
                    if new_doc:
                        additional_sections.append(new_section)
                        additional_sections += meta_sections_buffer
                        meta_sections_buffer = []
                    else:
                        meta_sections_buffer.append(new_section)
                    break
            # (if we did not break on a split decision)
            else:
                if split:
                    additional_sections[recipient_document_n].pages_paragraphs.append((scan_page, paragraph))
                else:
                    self.pages_paragraphs.append((scan_page, paragraph))
        return additional_sections

    def guess_date(self):
        """Given the own title and document content, try to guess the date on which the document was created. Return the date that was chosen or False, if none was."""
        # First, try to return the earliest (full) date from the title.
        title_dates = extract_dates(self.pages_paragraphs[0][1])
        sorted_dates = sorted([(d, m, y) for (d, m, y) in title_dates if y <= 1795], key=lambda x: x[2])
        if len(sorted_dates) > 0:
            self.date = sorted_dates[0]
            return self.date
        # If the title yields nothing, try the content - the first date that appears in the document.
        content_dates = extract_dates(self.collapsed_text())
        sorted_dates = [(d, m, y) for (d, m, y) in content_dates if y <= 1795]
        if len(sorted_dates) > 0:
            self.date = sorted_dates[0]
            return self.date
        return False

    def __init__(self):
        pass

    @classmethod
    def new(cls, config, section_type, section_content, document_id=False, pertinence='default'):
        self = cls()
        self.book_title = config['book_title']
        self.inbook_section_id = False # not included in any yet
        self.inbook_document_id = document_id
        self.section_type = section_type
        self.date = False
        self.palatinate = config['palatinate']
        self.convent_location = config['convent_location']
        self.created_location = False
        self.author = config['default_convent_author']
        # This is expected to be a list of pairs (scanpage_num, paragraph).
        self.pages_paragraphs = section_content
        if pertinence == 'default':
            if section_type == 'document':
                self.pertinence = True
            else:
                self.pertinence = False
        else:
            self.pertinence = pertinence
#        if section_id == 23:
#            fail()
        return self

    @classmethod
    def from_csv_row(cls, row):
        self = cls()
        self.book_title = row[0]
        self.inbook_section_id = row[1]
        self.inbook_document_id = row[2]
        #self.scan_page #= #row[3]
        #self.book_page #= #row[4]
        self.section_type = row[4]
        self.date = row[5]
        self.palatinate = row[6]
        self.convent_location = row[7]
        self.created_location = row[8]
        self.author = row[9]
        self.pages_paragraphs = [(int(row[3]), row[10])]
        self.pertinence = (row[11] == 'True')
        return self

    def append_csv_row(self, row):
        """Returns True if successful, False if the row doesn't belong to the section."""
        if row[1] == self.inbook_section_id:
            self.pages_paragraphs.append((int(row[3]), row[10]))
            return True
        return False
