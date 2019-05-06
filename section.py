import csv, io
from load_helpers import extract_dates, fuzzy_match

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
                paragraph
                ])
            rows.append(string_output.getvalue().strip())
        return rows

    def collapsed_text(self):
        return '\n\n'.join([par for (pg, par) in self.pages_paragraphs[1:]])

    def title(self):
        if len(self.pages_paragraphs) > 0:
            return self.pages_paragraphs[0]
        else:
            return ''

    def add_to_text(self, new_pages_paragraphs, page_decisions, config, section_n, document_n):
        """Add the new_text to section text. If there are new sections splitted, they are returned as a list."""
        additional_sections = []
        split_decisions = [corr for corr in page_decisions if corr.decision_type=='split_sections']
        # Add own last paragraph for context checking.
        pages_paragraphs = (self.pages_paragraphs[-1:] if len(self.pages_paragraphs) > 0 else [(0, '')]) + new_pages_paragraphs
        split = False # indicates whether we need to place next parags in additional sections
        current_section_n = section_n
        current_document_n = document_n
        for parag_n, (scan_page, paragraph) in enumerate(pages_paragraphs):
            # We need the first paragraph only for checking the end of existing text.
            if parag_n == 0:
                continue
            if parag_n + 1 < len(pages_paragraphs):
                for corr in split_decisions:
                    if (fuzzy_match(corr.from_title, self.pages_paragraphs[0][1])
                            and fuzzy_match(corr.preceding_fragm, pages_paragraphs[parag_n-1][1][-80:])
                            and fuzzy_match(corr.following_fragm, paragraph)):
                        if corr.new_section_type == 'document':
                            new_section = Section.new(config, 'document',
                                    [(scan_page, paragraph)],
                                    current_section_n,
                                    document_id=current_document_n)
                            current_document_n += 1
                        elif corr.new_section_type == 'meta':
                            new_section = Section.new(config, 'meta',
                                    [(scan_page, paragraph)],
                                    current_section_n)
                        else:
                            raise NotImplementedError('requested section split with unknown section'
                                    ' type {}'.format(corr.new_section_type))
                        current_section_n += 1
                        additional_sections.append(new_section)
                        split = True
            if split:
                additional_sections[-1].pages_paragraphs.append((scan_page, paragraph))
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
    def new(cls, config, section_type, section_content, section_id, document_id=False):
        self = cls()
        self.book_title = config['book_title']
        self.inbook_section_id = section_id
        self.inbook_document_id = document_id
        self.section_type = section_type
        self.date = False
        self.palatinate = config['palatinate']
        self.convent_location = config['convent_location']
        self.created_location = False
        self.author = config['default_convent_author']
        # This is expected to be a list of pairs (scanpage_num, paragraph).
        self.pages_paragraphs = section_content
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
        return self

    def append_csv_row(self, row):
        """Returns True if successful, False if the row doesn't belong to the section."""
        if row[1] == self.inbook_section_id:
            self.pages_paragraphs.append((int(row[3]), row[10]))
            return True
        return False
