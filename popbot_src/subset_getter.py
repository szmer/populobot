from popbot_src.indexing_common import load_document_sections
from popbot_src.indexing_helpers import apply_decisions1, read_config_file, read_manual_decisions

def date_sortable_form(date):
    "This can be supplied as a 'key' to a sorting function"
    d, m, y = tuple(date)
    return int(y) * 1000 + int(m) * 100 + int(d)

def make_subset_index(file_list_path, date_ranges=[]):
    """Return a list of tuples: subset name, list of subset sections"""
    with open(file_list_path) as list_file:
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
        # Leave out non-document and non-pertinent sections.
        sections = [s for s in sections if s.section_type == 'document' and s.pertinence]
        all_sections += sections

    # Index sections.
    section_index = dict()
    section_index['ALL'] = all_sections
    # we don't want to give single date subsets, they'll be grouped in ranges
    section_date_index = dict()
    all_dates = []
    for section in all_sections:
        if section.date:
            all_dates.append(section.date) # avoid False which we can't sort
            if section.date in section_date_index:
                section_date_index[section.date].append(section)
            else:
                section_date_index[section.date] = [ section ]
        attrnames = ['book_title', 'convent_location', 'palatinate']
        for attr in attrnames:
            index = '{}__{}'.format(attr, getattr(section, attr))
            if index in section_index:
                section_index[index].append(section)
            else:
                section_index[index] = [ section ]

    # Make date ranges.
    all_dates.sort(key=date_sortable_form)
    sortable_ranges = [(date_sortable_form(dr[0].split('-')),
        date_sortable_form(dr[1].split('-'))) for dr in date_ranges]
    for date in all_dates:
        sortable_date = date_sortable_form(date)
        for range_n, date_range in enumerate(sortable_ranges):
            if sortable_date >= date_range[0] and sortable_date <= date_range[1]:
                daterange_index = 'daterange__' + '_'.join(list(date_ranges[range_n]))
                if not daterange_index in section_index:
                    section_index[daterange_index] = []
                section_index[daterange_index] += section_date_index[date]

    return section_index.items()
