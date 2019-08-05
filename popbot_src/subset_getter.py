from popbot_src.indexing_common import load_document_sections
from popbot_src.indexing_helpers import apply_decisions1, read_config_file, read_manual_decisions

def date_sortable_form(date):
    "This can be supplied as a 'key' to a sorting function"
    d, m, y = tuple([int(f) for f in date.split('-')])
    return y * 1000 + m * 100 + d

# TODO
standard_date_thresholds = []

def make_subset_generator(file_list_path, date_thresholds=standard_date_thresholds):
    fnames = []
    with open(file_list_path) as list_file:
        global fnames
        fnames = list_file.readlines()

    # Load sections.
    all_sections = []
    for file_row in fnames:
        file_fields = file_row.split()
        filename = file_fields[0]
        sections = load_document_sections(filename)
        if len(file_fields) > 1:
            manual_decisions = read_manual_decisions(file_fields[1])
            config = read_config_file(file_fields[2])
            sections = apply_decisions1(sections, manual_decisions, config)
        all_sections += sections

    # Index sections.
    section_index = dict()
    # we don't want to give single date subsets, they'll be grouped in ranges
    section_date_index = dict()
    all_dates = []
    for section in all_sections:
        if section.date:
            all_dates.append(section.date) # avoid False which we can't sort
        attrnames = ['book_title', 'convent_location', 'palatinate', 'date']
        for attr in attrnames:
            index = '{}//{}'.format(attr, getattr(section, attr))
            if getattr(section, attr) in section_index:
                if attr == 'date':
                    section_date_index[index].append(section)
                else:
                    section_index[index].append(section)
            else:
                if attr == 'date':
                    section_date_index[index] = [ section ]
                else:
                    section_index[index] = [ section ]

    # Make date ranges.
    all_dates.sort(key=date_sortable_form)
    threshold_n = 0
    daterange_index = 'daterange//' + date_thresholds[threshold_n]
    section_index[daterange_index] = []
    for date in all_dates:
        # If the threshold passed.
        if (threshold_n + 1 < len(date_thresholds)
                and date_sortable_form(date) >= date_sortable_form(date_thresholds[threshold_n+1])):
            threshold_n += 1
            daterange_index = 'daterange//' + date_thresholds[threshold_n]
            section_index[daterange_index] = []
        section_index[daterange_index] += section_date_index[date]

    for (index, sections) in section_index.items():
        yield index, sections
