# The pagenum should reflect the actual order of pages (zero-based), not the filenames.
# The preceding and following fragments should be 80 chars in length.

class MergeSectionDecision():
    def __init__(self, decision_type, from_title, pagenum, preceding_fragm, following_fragm):
        self.decision_type = 'merge_sections'
        self.from_title = from_title
        self.pagenum = int(pagenum)
        self.preceding_fragm = preceding_fragm
        self.following_fragm = following_fragm

class SplitSectionDecision():
    def __init__(self, decision_type, from_title, pagenum, preceding_fragm, following_fragm,
            new_section_type, new_title):
        self.decision_type = 'merge_sections'
        self.from_title = from_title
        self.pagenum = int(pagenum)
        self.preceding_fragm = preceding_fragm
        self.following_fragm = following_fragm
        # In meta sections, headings (titles) of document sections that would be
        # empty are section titles with empty contents. New_title is set for
        # meta sections only in those cases. Otherwise these sections are untitled.
        #
        # If there is no new title in the correction, we are meant to treat the
        # current paragraph in text as the potential next one instead of a new title.
        self.new_title = new_title
        self.new_section_type = new_section_type

class DateDecision():
    def __init__(self, date, from_title, pagenum):
        self.decision_type = 'date'
        self.date = date
        self.from_title = from_title
        self.pagenum = int(pagenum)
