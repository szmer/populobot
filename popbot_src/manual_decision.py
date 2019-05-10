# The pagenum should reflect the actual order of pages (zero-based), not the filenames.
# For merges, dates, pertinences, it should be the last page of the section
# (where it will be commited by the loader).
#
# The preceding and following fragments should be at most 80 chars in length,
# taking only the immediately adjacent paragraphs.

class MergeSectionDecision():
    def __init__(self, from_title, pagenum, preceding_fragm, following_fragm):
        self.decision_type = 'merge_sections'
        # Any section can be merged, but always with the previous document section.
        self.from_title = from_title
        self.pagenum = int(pagenum) # the pagenum where merge happens
        self.preceding_fragm = preceding_fragm
        self.following_fragm = following_fragm

# NOTE splitting out a meta section does this only to one paragraph.
class SplitSectionDecision():
    def __init__(self, pagenum, following_fragm, new_section_type):
        self.decision_type = 'split_sections'
        self.pagenum = int(pagenum) # the pagenum where split happens
        self.following_fragm = following_fragm
        self.new_section_type = new_section_type

class DateDecision():
    def __init__(self, date, from_title, pagenum):
        self.decision_type = 'date'
        self.date = date
        self.from_title = from_title
        self.pagenum = int(pagenum)

class TypeDecision():
    def __init__(self, section_type, from_title, pagenum):
        self.decision_type = 'type'
        self.section_type = section_type
        self.from_title = from_title
        self.pagenum = int(pagenum)

class PertinenceDecision():
    def __init__(self, pertinence_status, from_title, pagenum):
        self.decision_type = 'pertinence'
        self.from_title = from_title
        self.pagenum = int(pagenum)
        self.pertinence_status = pertinence_status

class TitleFormDecision():
    def __init__(self, to_title, from_title, pagenum):
        self.decision_type = 'title_form'
        self.to_title = to_title
        self.from_title = from_title
        self.pagenum = int(pagenum)
