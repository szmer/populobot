from random import shuffle

from popbot_src.indexing_common import load_document_sections
from popbot_src.indexing_helpers import apply_decisions1, read_config_file, read_manual_decisions

def date_sortable_form(date):
    "This can be supplied as a 'key' to a sorting function"
    d, m, y = tuple(date)
    return int(y) * 1000 + int(m) * 100 + int(d)

def section_indices(section, attrnames, date_ranges=[]):
    """Return all indices under which the section should be filed. If date_ranges are provided (as
    datetime objects), the date attribute is compared against them and appropriate ranges are also
    included."""
    indices = []
    for attr in attrnames:
        indices.append('{}__{}'.format(attr, getattr(section, attr)))
    for date_range in date_ranges:
        if section.date >= date_range[0] and section.date < date_range[1]:
            indices.append('date_range__' + '_'.join(list(date_range)))
    return indices

def weight_index(section_index, indexed_attrs, weighted_param, weighted_values, date_ranges=[]):
    weighted_section_index = dict()
    # Observed total string-lengths of all subcorpora.
    observed_lengths = [] # to be converted to a dict
    for value in weighted_values:
        index = '{}__{}'.format(weighted_param, value)
        if index in section_index:
            observed_lengths.append((value, sum([len(section.collapsed_text()) for section
                                          in section_index[index]])))
    observed_lengths = dict(observed_lengths)
    observed_total = sum([len for value, len in observed_lengths.items()])
    weight_total = sum([weight for value, weight in weighted_values.items()
                        if value in observed_lengths])

    # Find the value for which we have the least text in relation to what is needed. It will
    # be used for scaling down the whole corpus to the weights.
    smallest_coverage = 100
    for value, observed_weight in observed_lengths.items():
        # Here we divide the proportions/weights by totals to have normalized proportion ratio,
        # which we will need to compute the scaled total.
        coverage = ((observed_weight/observed_total) / (weighted_values[value]/weight_total))
        if coverage < smallest_coverage:
            smallest_coverage = coverage
    scaled_total = smallest_coverage * observed_total

    # Note that values without associated weights are ignored.
    for value, observed_weight in observed_lengths.items():
        value_index = '{}__{}'.format(weighted_param, value)
        weight = weighted_values[value]
        length_quota = weight/weight_total * scaled_total
        acquired_length = 0
        # TODO guarantee seed consistence
        section_ns = list(range(len(section_index[value_index])))
        shuffle(section_ns)
        for section_n in section_ns:
            if acquired_length >= length_quota:
                break
            section = section_index[value_index][section_n]
            indices = section_indices(section, indexed_attrs, date_ranges=date_ranges)
            acquired_length += len(section.collapsed_text())
            for index in indices:
                if index in weighted_section_index:
                    weighted_section_index[index].append(section)
                else:
                    weighted_section_index[index] = [ section ]
    return weighted_section_index

def make_subset_index(file_list_path, indexed_attrs, date_ranges=[], subcorpus_weightings=[]):
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
    for section in all_sections:
        indices = section_indices(section, indexed_attrs, date_ranges=date_ranges)
        for index in indices:
            if index in section_index:
                section_index[index].append(section)
            else:
                section_index[index] = [ section ]

    # Apply subcorpus weightings.
    for weighted_param, weighted_values in subcorpus_weightings.items():
        section_index = weight_index(section_index, indexed_attrs, weighted_param, weighted_values)

    return section_index.items()
