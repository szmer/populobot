import copy
from logging import info
import os
import pexpect
import re
import yaml

from popbot_src.parsed_token import ParsedToken
from popbot_src.MAGIC import Analyse

def parse_morfeusz_output(morfeusz_str):
    """Given the output from console printed by Morfeusz, parse it into lists of
    lists of possible interpretations for each recognized node."""
    # replace unwieldy special characters to make parsing reliable
    morfeusz_str = re.sub(',,', ',MORFEUSZ_COMMA', morfeusz_str)
    morfeusz_str = re.sub('\\.,', 'MORFEUSZ_DOT,', morfeusz_str)

    sections = morfeusz_str.split(']\r\n[') # pexpect uses \r\n style newlines
    sections[0] = sections[0].strip()[1:] # remove the first and last bracket
    sections[-1] = sections[-1].strip()[:-1]

    parsed_sections = []
    for sec in sections: # (per graph path, which can have some alternatives inside)
        nodes = [node.split(',') for node in sec.split('\n')]
        parsed_nodes = []
        for (node_n, items) in enumerate(nodes): # 'natively-printed' Morfeusz options for this graph path
            clean_items = [re.sub('^_$', '', item.strip().strip('[]').replace('MORFEUSZ_COMMA', ','))
                                    for item in items]
            clean_items[2] = clean_items[2].replace('MORFEUSZ_DOT', '.') # form and lemma
            clean_items[3] = clean_items[3].replace('MORFEUSZ_DOT', '.')
            if len(clean_items) > 7: # some wild commas, just fake the node with something inoffensive
                clean_items = clean_items[0:2] + ['_', '_', 'ign', '', '']
            assembled_alternatives = []
            for (pos_n, alts) in enumerate(clean_items[4].split(':')):
                new_alternatives = []
                alts = alts.split('.')
                for alt in alts:
                    if pos_n == 0:
                        new_alternatives.append(alt)
                    else:
                        for prev_alt in assembled_alternatives:
                            new_alternatives.append(prev_alt+':'+alt)
                assembled_alternatives = new_alternatives
            for tag in assembled_alternatives:
                parsed_nodes.append(clean_items[:4] + [ tag ] + clean_items[5:])
        parsed_sections.append(parsed_nodes)
    return parsed_sections

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
        for (node_n, node) in enumerate(morfeusz_nodes):
            for variant in node:
                if node_n < (len(morfeusz_nodes) - 1):
                    concraft_columns = [str(1/len(node)), '', '', '']
                else: # add end of sentence tag
                    concraft_columns = [str(1/len(node)), '', 'eos', '']
                print('\t'.join(variant + concraft_columns), file=out)
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

def morfeusz_analysis(morfeusz_process, text):
    # Square brackets can mess up parse detection in output. Quote chars need to be escaped.
    text = text.replace('\n', ' ').replace('[', '🧐').replace(']', '🥸').replace('"', '\\"').replace('\'', '\\\'')
    # The $'...' syntax uses escape sequences.
    morfeusz_process.send('{} KONIECKONIEC\n'.format(text))
    pexp_result = morfeusz_process.expect(['\r\n\\[\\d+,\\d+,KONIECKONIEC,KONIECKONIEC,ign,_,_\\]\r\n',
        pexpect.EOF, pexpect.TIMEOUT], timeout=10*60)
    if pexp_result != 0 and pexp_result != 2: # 2 is "misuse of Shell builtins"
        raise RuntimeError('there was a Morfeusz error (exit code {}): {}'.format(pexp_result, morfeusz_process.before))
    morfeusz_interp = morfeusz_process.before.decode().strip() # encode from bytes into str, strip whitespace
    morfeusz_interp = morfeusz_interp[morfeusz_interp.index('['):].replace('🧐', '[').replace('🥸', ']')
    return morfeusz_interp

def tokens_paths(sents_str, base_config=False):
    """
    Return sentences as lists of token dictionaries extracted from the Morfeusz analysis. These dictionaries
    should also contain numbers of the tokens' positions in the sentence's direct acyclic graph.
    """
    if sents_str.strip() == '':
        raise ValueError('called parse_sentences on empty string')

    if not base_config:
        # Load the configuration.
        with open('config.yml') as base_config_file:
            base_config = yaml.load(base_config_file, Loader=yaml.Loader)

    # Prepare the Morfeusz process.
    morfeusz_analyzer = pexpect.spawn('morfeusz_analyzer --dict-dir {} -d {}'.format(
        base_config['morfeusz_model_dir'], base_config['morfeusz_model']))
    morfeusz_analyzer.delaybeforesend = None # don't make sending horrifyingly slow
    pexp_result = morfeusz_analyzer.expect(['Using dictionary: [^\\n]*$', pexpect.EOF, pexpect.TIMEOUT])
    if pexp_result != 0:
        raise RuntimeError('cannot run morfeusz_analyzer properly')

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

        morfeusz_interp = morfeusz_analysis(morfeusz_analyzer, str_chunk)
        parsed_nodes = parse_morfeusz_output(morfeusz_interp)

        morfeusz_sentences = split_morfeusz_sents(parsed_nodes)
        for sent_n, morf_sent in enumerate(morfeusz_sentences):
            if sent_n == 0:
                write_dag_from_morfeusz('MORFEUSZ_CONCRAFT_TEMP', morf_sent)
            else:
                write_dag_from_morfeusz('MORFEUSZ_CONCRAFT_TEMP', morf_sent, append_sentence=True)
        # Get a list of token postions with their interps.
        tokens_interps = path_analyzer.text_analyse('MORFEUSZ_CONCRAFT_TEMP', sents_str)
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
    morfeusz_analyzer = pexpect.spawn('morfeusz_analyzer --dict-dir {} -d {}'.format(
        base_config['morfeusz_model_dir'], base_config['morfeusz_model']))
    pexp_result = morfeusz_analyzer.expect(['Using dictionary: [^\\n]*$', pexpect.EOF, pexpect.TIMEOUT])
    if pexp_result != 0:
        raise RuntimeError('cannot run morfeusz_analyzer properly')

    parsed_sents = []
    parsed_boundary = 0 # track where we left the parsing after the previous chunk
    chunk_size = 2500#200*115
    while len(sents_str) != parsed_boundary:
        previous_parsed_boundary = parsed_boundary
        parsed_boundary = sents_str[:parsed_boundary+chunk_size].rfind(' ')
        if parsed_boundary == -1 or previous_parsed_boundary+chunk_size >= len(sents_str):
            parsed_boundary = len(sents_str)
        str_chunk = sents_str[previous_parsed_boundary:parsed_boundary]

        morfeusz_interp = morfeusz_analysis(morfeusz_analyzer, str_chunk)
        if verbose:
            print('Morfeusz interp is', morfeusz_interp)
        parsed_nodes = parse_morfeusz_output(morfeusz_interp)
        if verbose:
            print(len(parsed_nodes), 'parsed nodes')

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
