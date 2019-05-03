# The pagenum should reflect the actual order of pages (zero-based), not the filenames.

class SectionDecision():
    def __init__(self, decision_type, title, pagenum, preceding_fragm, subsequent_fragm):
        self.decision_type = decision_type # 'split_section' or 'merge_section'
        self.title = title
        self.pagenum = int(pagenum)
        self.preceding_fragm = preceding_fragm
        self.subsequent_fragm = subsequent_fragm

class DateDecision():
    def __init__(self, date, title, pagenum):
        self.decision_type = 'date'
        self.date = date
        self.title = title
        self.pagenum = int(pagenum)
