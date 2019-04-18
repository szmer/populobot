import argparse, csv, json
from math import sqrt

from section import Section

argparser = argparse.ArgumentParser(description='Score quality of document indexing.')
argparser.add_argument('--print-titles', '-t', action='store_true')
argparser.add_argument('config_path')
argparser.add_argument('csv_path')

args = argparser.parse_args()

# Load the config
config = None
with open(args.config_path) as config_file:
    config = json.loads(config_file.read())

# Load document sections from the csv
document_sections = []
with open(args.csv_path) as csv_file:
    csv_reader = csv.reader(csv_file)
    for row in csv_reader:
        section = Section.from_csv_row(row)
        if section.section_type == 'document':
            if args.print_titles:
                print(section.section_title)
            document_sections.append(section)

# Collect document lengths from both sources.
true_document_lengths = []
prev_pagenum = config['dev__true_document_pages'][0]
for pagenum in config['dev__true_document_pages'][1:]:
    true_document_lengths.append(pagenum-prev_pagenum+1)
    prev_pagenum = pagenum
csv_document_lengths = [len(sec.text) for sec in document_sections]

# Scale the indexed lengths as we would be distributing pages from the original index.
scaled_document_lengths = [l / sum(csv_document_lengths) * sum(true_document_lengths)
        for l in csv_document_lengths]

# Option 1: We indexed exactly as many documents as the truth.
# Computing the distance is straightforward.
if len(csv_document_lengths) == len(true_document_lengths):
    distance = 0
    for li, length in enumerate(true_document_lengths):
        distance += (length - scaled_document_lengths[li])**2
    distance = sqrt(distance)
# Option 2: Our indexed csv has more documents than the truth.
# Greedily alignments (merging documents) minimizing euclidean distance between length sequences.
elif len(scaled_document_lengths) > len(true_document_lengths):
    forward_alignment = [ scaled_document_lengths[0] ]
    current_orig_index = 0
    for li, length in enumerate(scaled_document_lengths[1:]):
        # We need to have enough documents left to cover everything; if it is true, merge documents if this produces some distance reduction.
        if (current_orig_index == len(true_document_lengths)-1
                or ((len(scaled_document_lengths)-li) > len(true_document_lengths)-current_orig_index
                and ((forward_alignment[-1]+length-true_document_lengths[current_orig_index])**2 
                < (forward_alignment[-1]-true_document_lengths[current_orig_index])**2))):
            forward_alignment[-1] += length
        else:
            forward_alignment.append(length)
            current_orig_index += 1
    forward_alignment_distance = 0
    for li, length in enumerate(true_document_lengths):
        forward_alignment_distance += (length - forward_alignment[li])**2
    forward_alignment_distance = sqrt(forward_alignment_distance)

    backward_alignment = [ scaled_document_lengths[-1] ]
    current_orig_index = len(true_document_lengths) - 1
    for li, length in enumerate(reversed(scaled_document_lengths[:-1])):
        # We need to have enough documents left to cover everything; if it is true, merge documents if this produces some distance reduction. Also we must only merge when we are down to the first true page.
        if (((len(scaled_document_lengths)-li-1) > current_orig_index
                and (backward_alignment[-1]+length-true_document_lengths[current_orig_index])**2 
                < (backward_alignment[-1]-true_document_lengths[current_orig_index])**2)
                or current_orig_index == 0):
            backward_alignment[-1] += length
        else:
            backward_alignment.append(length)
            current_orig_index -= 1
    backward_alignment_distance = 0
    backward_alignment.reverse()
    for li, length in enumerate(true_document_lengths):
        backward_alignment_distance += (length - backward_alignment[li])**2
    backward_alignment_distance = sqrt(backward_alignment_distance)

    distance = min([forward_alignment_distance, backward_alignment_distance])
# Option 3: Our indexed csv has fewer documents than the truth.
elif len(scaled_document_lengths)*2 > len(true_document_lengths):
    forward_alignment = [ ]
    current_orig_index = 0
    for li, length in enumerate(scaled_document_lengths):
        if current_orig_index+1 < len(true_document_lengths) and li+1 < len(scaled_document_lengths):
            current_ngb_distances = ((length-true_document_lengths[current_orig_index])**2
                    + (scaled_document_lengths[li+1] + true_document_lengths[current_orig_index+1])**2)
            ngb_proportion = true_document_lengths[current_orig_index] / sum(true_document_lengths[current_orig_index:current_orig_index+2])
            split_ngb_distances = ((ngb_proportion*length-true_document_lengths[current_orig_index])**2
                    + ((1-ngb_proportion)*length-true_document_lengths[current_orig_index+1])**2)
            # We are forced to split if there is less remaining indexed sections (x2 if we'd split them all) than there is remaining true ones.
            # On the other hand, we must stop splitting if there is no room left for that in accomodating the remaining portion of true pages.
            if (split_ngb_distances < current_ngb_distances or (len(scaled_document_lengths) - li)*2 <= len(true_document_lengths) - current_orig_index) and len(true_document_lengths) - current_orig_index > (len(scaled_document_lengths) - li):
                forward_alignment += [ngb_proportion*length, (1-ngb_proportion)*length]
                current_orig_index += 2
            else:
                forward_alignment.append(length)
                current_orig_index += 1
        else:
            forward_alignment.append(length)
            if current_orig_index+1 != len(true_document_lengths) or li+1 != len(scaled_document_lengths):
                raise RuntimeError('bad forward alignment of shorter page index (there is an error in algorithm)')
    forward_alignment_distance = 0
    for li, length in enumerate(true_document_lengths):
        forward_alignment_distance += (length - forward_alignment[li])**2
    forward_alignment_distance = sqrt(forward_alignment_distance)

    backward_alignment = [ ]
    current_orig_index = len(true_document_lengths)-1
    for li, length in enumerate(reversed(scaled_document_lengths)):
        if current_orig_index != 0 and li+1 < len(scaled_document_lengths):
            current_ngb_distances = ((length-true_document_lengths[current_orig_index])**2
                    + (scaled_document_lengths[li+1] + true_document_lengths[current_orig_index-1])**2)
            ngb_proportion = true_document_lengths[current_orig_index] / sum(true_document_lengths[current_orig_index-1:current_orig_index+1])
            split_ngb_distances = ((ngb_proportion*length-true_document_lengths[current_orig_index])**2
                    + ((1-ngb_proportion)*length-true_document_lengths[current_orig_index-1])**2)
            # We are forced to split if there is less remaining indexed sections (x2 if we'd split them all) than there is remaining true ones.
            # On the other hand, we must stop splitting if there is no room left for that in accomodating the remaining portion of true pages.
            if (split_ngb_distances < current_ngb_distances or (len(scaled_document_lengths)-li)*2 <= current_orig_index) and current_orig_index > len(scaled_document_lengths) - li - 1:
                backward_alignment += [ngb_proportion*length, (1-ngb_proportion)*length]
                current_orig_index -= 2
            else:
                backward_alignment.append(length)
                current_orig_index -= 1
        else:
            backward_alignment.append(length)
            if current_orig_index != 0 or li+1 != len(scaled_document_lengths):
                raise RuntimeError('bad backward alignment of shorter page index (there is an error in algorithm)')
    backward_alignment.reverse()
    backward_alignment_distance = 0
    for li, length in enumerate(true_document_lengths):
        backward_alignment_distance += (length - backward_alignment[li])**2
    backward_alignment_distance = sqrt(backward_alignment_distance)

    distance = min([forward_alignment_distance, backward_alignment_distance])
else:
    raise NotImplementedError('the case with >2x fewer documents than truth is not implemented')

# Print the final score.
difference = abs(len(true_document_lengths)-len(scaled_document_lengths))
proportion = (len(scaled_document_lengths)-len(true_document_lengths))/len(true_document_lengths)
print('Lengths distance / document count difference / total score')
print('{:.3f} {}({:.3f}) {:.3f}'.format(distance, difference, proportion, distance+difference))
