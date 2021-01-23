import csv
import copy
from logging import info
import os
import pexpect
import re
import yaml

from morfeusz2 import Morfeusz

from popbot_src.parsed_token import ParsedToken
from popbot_src.MAGIC import Analyse

def stringify_value(value):
    if value != 0 and not value:
        return ''
    return str(value)

def merge_morfeusz_variants(morfeusz_output, stringify_values=True):
    """
    With output from the Morfeusz Python binding, transform the tuples of (start_node, end_node, (interp...))
    into lists of nodes of [(start_node, end_node, interp...), ...], merging variants of the same
    start-end position into one list each.
    """
    positions_lists = dict() # start_end -> ready lists
    for node_n, node in enumerate(morfeusz_output):
        key = '{}_{}'.format(node[0], node[1])
        if not key in positions_lists:
            positions_lists[key] = []
        variant_list = list((node[0], node[1]) + node[2]) # form one list
        if stringify_values:
            variant_list = [stringify_value(val) for val in variant_list]
        positions_lists[key].append(variant_list)

    def position_sorter(key):
        start, end = tuple(key.split('_'))
        return int(start)*1000 + int(end)
    return [item[1] for item in sorted(positions_lists.items(), key=lambda item: position_sorter(item[0]))]

def split_morfeusz_sents(morfeusz_nodes, verbose=False):
    """Given an output from parse_morfeusz_output, return it as a list of sentences."""
    sent_boundaries = [0]
    previous_brev = False
    for (node_n, node) in enumerate(morfeusz_nodes):
        current_brev = False
        for variant in node:
            if 'brev' in variant[4]:
                previous_brev = True
                current_brev = True
            if variant[2] == '.' and not previous_brev:
                sent_boundaries.append(node_n+1)
        if not current_brev:
            previous_brev = False
    sent_boundaries.append(len(morfeusz_nodes))
    if verbose:
        print('sentence boundaries', sent_boundaries)
    sents = []
    for (bnd_n, bnd) in enumerate(sent_boundaries[1:]):
        sents.append(morfeusz_nodes[sent_boundaries[bnd_n]:bnd]) # bnd_n is effectively bnd_n-1, because of skipping first element
    sents = [s for s in sents if len(s) > 0]
    return sents

def write_dag_from_morfeusz(path, morfeusz_nodes, append_sentence=False):
    """Write the Morfeusz output graph (DAG) to a file, where it can be read from by Concraft"""
    open_settings = 'a' if append_sentence else 'w+'
    with open(path, open_settings, encoding='utf-8') as out:
        writer = csv.writer(out, dialect='excel', delimiter='\t')
        for (node_n, node) in enumerate(morfeusz_nodes):
            for variant in node:
                if node_n < (len(morfeusz_nodes) - 1):
                    concraft_columns = [str(1/len(node)), '', '', '']
                else: # add end of sentence tag
                    concraft_columns = [str(1/len(node)), '', 'eos', '']
                writer.writerow(variant + concraft_columns)
        print('', file=out) # newline

def parse_with_concraft(concraft_model_path, input_path):
    concraft = pexpect.spawn('concraft-pl tag -i {} {}'.format(input_path, concraft_model_path))
    concraft.delaybeforesend = None
    pexp_result = concraft.expect([pexpect.EOF, pexpect.TIMEOUT])
    if pexp_result != 0:
        raise RuntimeError('there was a Concraft timeout: {}'.format(concraft.before))
    concraft_interp = concraft.before.decode()
    if 'concraft-pl:' in concraft_interp:
        raise RuntimeError('there was a Concraft error: {}'.format(concraft_interp))
    sents = []
    current_sent_tokens = []
    to_map, from_map = [], dict() # pairs (node/token, to_position), (from values) -> (tokens there)
    # Store the already disambiguated paths to avoid repetitions in output.
    decided_paths = []
    lines = concraft_interp.split('\n')
    lines_fields = [line.split('\t') for line in lines]
    sent_start_index = min([int(fields[0]) for fields in lines_fields if len(fields) == 12])
    for line_n, fields in enumerate(lines_fields):

        if len(lines[line_n].strip()) == 0: # end of sentence
            for token, to_position in to_map:
                if to_position in from_map: # isn't true at the end of sentence
                    token.forward_paths = from_map[to_position]
            sents.append(current_sent_tokens)
            current_sent_tokens = []
            to_map, from_map = [], dict()
            # Update the start index.
            if len(lines_fields[line_n+1:]) > 1:
                sent_start_index = min([int(fields[0]) for fields
                    in lines_fields[line_n+1:] if len(fields) == 12])
            continue

        if len(fields) != 12:
            raise RuntimeError('Incorrect number of columns in Concraft output - {}, not 12:'
                    ' {}'.format(len(fields), lines[line_n]))
        if str(fields[0:2]) in decided_paths or not re.search('disamb\\r$', lines[line_n]):
            continue
        token = ParsedToken(fields[2], fields[3], fields[4].split(':'), # split the interp into a list of tags
                position=int(fields[0]))
        current_sent_tokens.append(token)

        from_index = fields[0]
        to_index = fields[1]
        to_map.append((token, to_index))
        if not from_index in from_map:
            from_map[from_index] = []
        from_map[from_index].append(token)
        if int(from_index) == sent_start_index:
            token.sentence_starting = True

        decided_paths.append(str(fields[0:2]))

    if len(sents) != 0 and not sents[-1]: # remove the last empty "sentence" if present
        sents = sents[:-1]
    return sents

def tokens_paths(sents_str, base_config=False):
    """
    Return sentences as lists of token dictionaries extracted from the Morfeusz analysis. These dictionaries
    should also contain numbers of the tokens' positions in the sentence's direct acyclic graph.
    """
    if sents_str.strip() == '':
        return []
        ##raise ValueError('called parse_sentences on empty string')

    if not base_config:
        # Load the configuration.
        with open('config.yml') as base_config_file:
            base_config = yaml.load(base_config_file, Loader=yaml.Loader)

    # Prepare the Morfeusz process.
    morfeusz_analyzer = Morfeusz(dict_path=base_config['morfeusz_model_dir'],
            dict_name=base_config['morfeusz_model'],
            generate=False)

    path_analyzer = Analyse(base_config['morfeusz_model_dir'], base_config['morfeusz_model'])
    pathed_sentences = []

    parsed_boundary = 0 # track where we left the parsing after the previous chunk
    chunk_size = 2500#200*115
    while len(sents_str) != parsed_boundary:
        previous_parsed_boundary = parsed_boundary
        parsed_boundary = sents_str[:parsed_boundary+chunk_size].rfind(' ')
        if parsed_boundary == -1 or previous_parsed_boundary+chunk_size >= len(sents_str):
            parsed_boundary = len(sents_str)
        str_chunk = sents_str[previous_parsed_boundary:parsed_boundary]

        parsed_nodes = morfeusz_analyzer.analyse(str_chunk)
        parsed_nodes = merge_morfeusz_variants(parsed_nodes)
        morfeusz_sentences = split_morfeusz_sents(parsed_nodes)
        for sent_n, morf_sent in enumerate(morfeusz_sentences):
            if sent_n == 0:
                write_dag_from_morfeusz('MORFEUSZ_CONCRAFT_TEMP', morf_sent)
            else:
                write_dag_from_morfeusz('MORFEUSZ_CONCRAFT_TEMP', morf_sent, append_sentence=True)
        # Get a list of token postions with their interps.
        tokens_interps = path_analyzer.text_analyse('MORFEUSZ_CONCRAFT_TEMP', sents_str,
                start_offset=previous_parsed_boundary)
        # Extract sentences from the tokens_interps.
        sent_counter = 0
        sent_start = 0
        for tok_n, token in enumerate(tokens_interps):
            real_token = token # extract some real token from the dictionary of alternate interps
            while type(real_token) != dict:
                real_token = real_token[0]
            if tok_n == len(tokens_interps) or real_token['end'] == int(morfeusz_sentences[sent_counter][-1][0][1]):
                pathed_sentences.append(tokens_interps[sent_start:tok_n+1])
                sent_start = tok_n+1
                sent_counter += 1
        os.remove('MORFEUSZ_CONCRAFT_TEMP')

    return pathed_sentences

def parse_sentences(sents_str, verbose=False, category_sigils=True, base_config=False):
    """
    Use Morfeusz and Concraft to obtain the sentences as lists of ParsedToken objects. The
    base_config option can be used to provide a dictionary with morfeusz_model_dir, morfeusz_model
    and concraft_models providing appropriate paths for models for these programs.
    """
    if sents_str.strip() == '':
        raise ValueError('called parse_sentences on empty string')

    if not base_config:
        # Load the configuration.
        with open('config.yml') as base_config_file:
            base_config = yaml.load(base_config_file, Loader=yaml.Loader)

    # Prepare the Morfeusz process.
    morfeusz_analyzer = Morfeusz(dict_path=base_config['morfeusz_model_dir'],
            dict_name=base_config['morfeusz_model'],
            generate=False)

    parsed_sents = []
    parsed_boundary = 0 # track where we left the parsing after the previous chunk
    chunk_size = 2500#200*115
    while len(sents_str) != parsed_boundary:
        previous_parsed_boundary = parsed_boundary
        parsed_boundary = sents_str[:parsed_boundary+chunk_size].rfind(' ')
        if parsed_boundary == -1 or previous_parsed_boundary+chunk_size >= len(sents_str):
            parsed_boundary = len(sents_str)
        str_chunk = sents_str[previous_parsed_boundary:parsed_boundary]

        parsed_nodes = morfeusz_analyzer.analyse(str_chunk)
        if verbose:
            print(len(parsed_nodes), 'parsed nodes')

        parsed_nodes = merge_morfeusz_variants(parsed_nodes)
        morfeusz_sentences = split_morfeusz_sents(parsed_nodes, verbose=verbose)
        if verbose:
            print('Morfeusz sentences,', len(morfeusz_sentences), ':', morfeusz_sentences)
        for sent_n, morf_sent in enumerate(morfeusz_sentences):
            if sent_n == 0:
                write_dag_from_morfeusz('MORFEUSZ_CONCRAFT_TEMP', morf_sent)
            else:
                write_dag_from_morfeusz('MORFEUSZ_CONCRAFT_TEMP', morf_sent, append_sentence=True)
        parsed_sents += parse_with_concraft(base_config['concraft_model'], 'MORFEUSZ_CONCRAFT_TEMP')
        os.remove('MORFEUSZ_CONCRAFT_TEMP')

    return parsed_sents

def parsed_sections(raw_sections):
    result_sections = []
    for sec_n, sec in enumerate(raw_sections):
        for x in range(10):
            if (sec_n >= ((len(raw_sections) / 10) * x)
                    and (sec_n-1) < ((len(raw_sections) / 10) * x)):
                info('Done {}% of parsing.'.format(x*10))
        new_sec = copy.deepcopy(sec)
        for par_n, (page, paragraph) in enumerate(new_sec.pages_paragraphs):
            new_sec.pages_paragraphs[par_n] = (page, parse_sentences(paragraph))
        result_sections.append(new_sec)
    return result_sections

def pathed_sections(raw_sections):
    result_sections = []
    for sec_n, sec in enumerate(raw_sections):
        for x in range(10):
            if (sec_n >= ((len(raw_sections) / 10) * x)
                    and (sec_n-1) < ((len(raw_sections) / 10) * x)):
                info('Done {}% of parsing.'.format(x*10))
        new_sec = copy.deepcopy(sec)
        for par_n, (page, paragraph) in enumerate(new_sec.pages_paragraphs):
            new_sec.pages_paragraphs[par_n] = (page, tokens_paths(paragraph))
        result_sections.append(new_sec)
    return result_sections
