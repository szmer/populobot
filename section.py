import io

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

    @classmethod
    def new(cls, section_type, section_title, section_contents, section_id, document_id=False):
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
