from popbot_src.indexing_common import load_document_sections
from popbot_src.indexing_helpers import apply_decisions1, read_config_file, read_manual_decisions

def date_sortable_form(date):
    "This can be supplied as a 'key' to a sorting function"
    d, m, y = tuple(date)
    return int(y) * 1000 + int(m) * 100 + int(d)

# TODO
standard_date_ranges = [
# Reigns.
('1-4-1548', '7-7-1572'), ('8-7-1572',  '1-5-1575'), ('2-5-1575', '12-12-1586'), ('13-12-1586',  '30-4-1632'), ('1-5-1632', '20-4-1648'), ('21-4-1648',  '16-9-1668'), ('17-9-1668', '10-11-1673'), ('11-11-1673', '17-6-1696'),
# Additional ranges.
('12-12-1586', '26-2-1609'), ('27-2-1609', '30-4-1632'), ('20-4-1648', '18-7-1656'), ('19-7-1656', '16-9-1668'), ('11-11-1673', '12-9-1683'), ('13-9-1683', '17-6-1696'),
]

def make_subset_index(file_list_path, date_ranges=standard_date_ranges):
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
