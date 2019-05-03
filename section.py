import csv, io
from load_helpers import extract_dates

# Section class template.
class Section():
    def __init__(self):
        pass

    def row_string(self):
        string_output = io.StringIO()
        csv_writer = csv.writer(string_output, quoting=csv.QUOTE_NONNUMERIC)
        csv_writer.writerow([
            self.book_title,
            self.inbook_section_id,
            self.inbook_document_id,
            self.scan_pages,
            self.book_pages,
            self.section_title,
            self.section_type,
            self.date,
            self.palatinate,
            self.convent_location,
            self.created_location,
            self.author,
            self.text
            ])
        return string_output.getvalue().strip()

    def guess_date(self):
        """Given the own title and document content, try to guess the date on which the document was created. Return the date that was chosen or False, if none was."""
        # First, try to return the earliest (full) date from the title.
        title_dates = extract_dates(self.section_title)
        sorted_dates = sorted([(d, m, y) for (d, m, y) in title_dates if y <= 1795], key=lambda x: x[2])
        if len(sorted_dates) > 0:
            self.date = sorted_dates[0]
            return self.date
        # If the title yields nothing, try the content - the first date that appears in the document.
        content_dates = extract_dates(self.text)
        sorted_dates = [(d, m, y) for (d, m, y) in content_dates if y <= 1795]
        if len(sorted_dates) > 0:
            self.date = sorted_dates[0]
            return self.date
        return False

    @classmethod
    def new(cls, config, section_type, section_title, section_contents, section_id, document_id=False):
        self = cls()
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
        return self

    @classmethod
    def from_csv_row(cls, row):
        self = cls()
        self.book_title = row[0]
        self.inbook_section_id = row[1]
        self.inbook_document_id = row[2]
        self.scan_pages = row[3]
        self.book_pages = row[4]
        self.section_title = row[5]
        self.section_type = row[6]
        self.date = row[7]
        self.palatinate = row[8]
        self.convent_location = row[9]
        self.created_location = row[10]
        self.author = row[11]
        self.text = row[12]
        return self
