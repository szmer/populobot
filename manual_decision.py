# The pagenum should reflect the actual order of pages (zero-based), not the filenames.
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

class SplitSectionDecision():
    def __init__(self, from_title, pagenum, preceding_fragm, following_fragm,
            new_section_type):
        self.decision_type = 'merge_sections'
        self.from_title = from_title
        self.pagenum = int(pagenum) # the pagenum where split happens
        self.preceding_fragm = preceding_fragm
        self.following_fragm = following_fragm
        self.new_section_type = new_section_type

class DateDecision():
    def __init__(self, date, from_title, pagenum):
        self.decision_type = 'date'
        self.date = date
        self.from_title = from_title
        self.pagenum = int(pagenum)
