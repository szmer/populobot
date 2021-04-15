import os
import lxml.etree as ET

nsmap = {
        'xi': 'http://www.w3.org/2001/XInclude',
        'nkjp': 'http://www.nkjp.pl/ns/1.0',
        'xml': 'http://www.w3.org/XML/1998/namespace',
        None: 'http://www.tei-c.org/ns/1.0'
        }

def tei_segm_segment_elem(id, form, offset, after_pause, raw_parent_id):
    """
    Make a segment element for ann_segmentation.xml. Corresp_ attributes point to the raw paragraph
    element id and the substring inside it corresponding to the segment.
    """
    segment = ET.Element('seg', {
        '{'+nsmap['xml']+'}id': id,
        'corresp': 'text.xml#string-range({},{},{})'.format(raw_parent_id, offset,
            len(form))})
    if not after_pause:
        segment.attrib['{'+nsmap['nkjp']+'}nps'] = 'true' # no space before the token
    # Inform of the form for convenience.
    w = ET.SubElement(segment, 'w')
    w.text = form
    return segment

def tei_morphos_segment_elem(token_id_counter, position, after_pause):
    """
    Make a segment element for ann_morphosyntax.xml.
    """
    segment = ET.Element('seg', {
        '{'+nsmap['xml']+'}id': 'morph_1.{}-seg'.format(token_id_counter['tok_num']),
        'corresp': 'ann_segmentation.xml#segm_1.{}-seg'.format(token_id_counter['tok_num'])})
    fs = ET.SubElement(segment, 'fs', { 'type': 'morph' })
    if not after_pause: # no space before the token
        f = ET.SubElement(fs, 'f', { 'name': 'nps' })
        ET.SubElement(f, 'binary', { 'value': 'true' })
    f = ET.SubElement(fs, 'f', { 'name': 'orth' })
    text = ET.SubElement(f, 'string')
    text.text = position['orth']
    interps = ET.SubElement(fs, 'f', { 'name': 'interps' })
    previous_msd = False # reduce duplication by merging same lemmas and pos
    for interp_n, interp in enumerate(position['interps']):
        if (previous_msd # avoiding duplicate fs differing only in msd
                and position['interps'][interp_n-1]['base'] == interp['base']
                and position['interps'][interp_n-1]['ctag'] == interp['ctag']):
            # Avoid duplication on only msd differing.
            if previous_msd.tag == 'f':
                # delete the previous msd as a direct child
                previous_msd.remove(list(previous_msd.xpath('symbol'))[0])
                valt = ET.SubElement(previous_msd, 'vAlt')
                ET.SubElement(valt, 'symbol', { # re-add the previous msd
                    '{'+nsmap['xml']+'}id': 'morph_1.{}.{}.1-msd'.format(token_id_counter['tok_num'],
                        interp_n),
                    'value': position['interps'][interp_n-1]['msd']
                    })
                ET.SubElement(valt, 'symbol', {
                    '{'+nsmap['xml']+'}id': 'morph_1.{}.{}.1-msd'.format(token_id_counter['tok_num'],
                        interp_n+1),
                    'value': interp['msd']
                    })
                previous_msd = valt
            else:
                ET.SubElement(valt, 'symbol', { # the valt variable was created above
                    '{'+nsmap['xml']+'}id': 'morph_1.{}.{}.1-msd'.format(token_id_counter['tok_num'],
                        interp_n+1),
                    'value': interp['msd']
                    })
            continue
        interp_f_list = ET.SubElement(interps, 'fs', {
            '{'+nsmap['xml']+'}id': 'morph_1.{}.{}-lex'.format(token_id_counter['tok_num'],
                interp_n+1),
            'type': 'lex',
            })
        f = ET.SubElement(interp_f_list, 'f', { 'name': 'base' })
        lemma = ET.SubElement(f, 'string')
        lemma.text = interp['base']
        f = ET.SubElement(interp_f_list, 'f', { 'name': 'ctag' })
        ET.SubElement(f, 'symbol', {
            '{'+nsmap['xml']+'}id': 'morph_1.{}.{}.ctag'.format(token_id_counter['tok_num'],
                interp_n+1),
            'value': interp['ctag']
            })
        f = ET.SubElement(interp_f_list, 'f', { 'name': 'msd' })
        ET.SubElement(f, 'symbol', {
            '{'+nsmap['xml']+'}id': 'morph_1.{}.{}.1-msd'.format(token_id_counter['tok_num'],
                interp_n+1),
            'value': interp['msd']
            })
        previous_msd = f
    token_id_counter['tok_num'] += 1
    return segment

def tei_simple_choice_elem(position, after_pause, tokens_id_counter, raw_parent_id):
    choice = ET.Element('choice')
    for interp in position['interps']:
        seg = tei_segm_segment_elem(segment_id(tokens_id_counter), position['orth'], position['offset'],
                after_pause, raw_parent_id)
        choice.append(seg)
    return choice

def tei_parenthesis_choice_elem(position_options, after_pause, tokens_id_counter, raw_parent_id):
    choice = ET.Element('choice')
    for option in position_options:
        if len(option) > 1:
            paren = ET.SubElement(choice, '{'+nsmap['nkjp']+'}paren')
            for tok_n, token in enumerate(option):
                seg = tei_segm_segment_elem(segment_id(tokens_id_counter), token['orth'], token['offset'],
                        # is the token after a pause/space?
                        after_pause if tok_n == 0 # (the first token)
                        else (option[tok_n-1]['offset']+len(option[tok_n-1]['orth'])) != token['offset'],
                        raw_parent_id)
                paren.append(seg)
            choice.append(paren)
        else:
            seg = tei_segm_segment_elem(segment_id(tokens_id_counter), token['orth'], token['offset'],
                    after_pause, raw_parent_id)
            choice.append(seg)
    return choice

def tei_sentence_elem(id, break_page=False):
    """
    A <s> element meant to be added subelements (e.g. for ann_segmentation.xml)
    """
    sentence = ET.Element('s', {'{'+nsmap['xml']+'}id': id})
    if break_page:
        ET.SubElement(sentence, 'pb', {'n': str(break_page)})
    return sentence

def tei_raw_paragraph(id, text, break_page=False):
    paragraph = ET.Element('p', {'{'+nsmap['xml']+'}id': id})
    page_break = None
    if break_page:
        page_break = ET.SubElement(paragraph, 'pb', {'n': str(break_page)})
    if page_break is not None:
        page_break.tail = text # after the pb
    else:
        paragraph.text = text
    return paragraph

def tei_paragraph_elem(id, break_page=False):
    """
    A <p> element meant to be added subelements (e.g. for ann_segmentation.xml)
    """
    paragraph = ET.Element('p', {'{'+nsmap['xml']+'}id': id})
    if break_page:
        ET.SubElement(paragraph, 'pb', {'n': str(break_page)})
    return paragraph

def tei_raw_document(id, paragraphs, title=False, type=False):
    attrs_dict = {'{'+nsmap['xml']+'}id': id}
    if type:
        attrs_dict['type'] = type
    document = ET.Element('div', attrs_dict)
    if title:
        head = ET.SubElement(document, 'head', {'{'+nsmap['xml']+'}id': '{}-title'.format(id)})
        head.text = title
    for par in paragraphs:
        document.append(par)
    return document

def tei_raw_note(id, text):
    note =  ET.Element('note', {'{'+nsmap['xml']+'}id': id, 'type': 'meta-text'})
    note.text = text
    return note

def tei_empty_subcorpus(name=False, lang=False):
    tei_corp = ET.Element('teiCorpus', nsmap=nsmap)
    # TODO include the global header
    tei = ET.SubElement(tei_corp, 'TEI')
    ET.SubElement(tei, '{'+nsmap['xi']+'}include', {'href': 'header.xml'})
    attrs = {}
    if name:
        attrs['{'+nsmap['xml']+'}id'] = name + '_text'
    if lang:
        attrs['{'+nsmap['xml']+'}lang'] = lang
    text = ET.SubElement(tei, 'text', attrs)
    attrs = {}
    if name:
        attrs['{'+nsmap['xml']+'}id'] = name + '_body'
    body = ET.SubElement(text, 'body', attrs)
    return tei_corp, body

def tei_raw_corpus(corp_name, sections, page_num_shift=0, publication_info={}):
    """
    A list of pairs: (main XML of the document, the header XML).
    """
    doc_pairs = []
    # TODO we need to adjust the page numbers here with the ones in editions!
    previous_page = 0
    note_num = 1
    for sec in sections:
        par_num = 1
        tei_corp, body = tei_empty_subcorpus()
        # the document header
        header = ET.Element('teiHeader', nsmap=nsmap)
        title_stmt = ET.SubElement(header, 'titleStmt')
        header_title = ET.SubElement(title_stmt, 'title')
        source_desc = ET.SubElement(header, 'sourceDesc')
        bibl = ET.SubElement(source_desc, 'bibl', {'type': 'original'})
        if sec.date:
            date = ET.SubElement(bibl, 'date', {'when': sec.date.isoformat()})
            date.text = sec.date.isoformat()
        region = ET.SubElement(bibl, 'region')
        region.text = sections[0].convent_location
        author = ET.SubElement(bibl, 'author')
        author.text = sections[0].author
        ET.SubElement(header, 'revisionDesc')
        # information on the whole outer publication
        if publication_info:
            edition = ET.SubElement(source_desc, 'bibl', {'type': 'edition'})
            series_title = ET.SubElement(edition, 'title', {'level': 's'})
            series_title.text = sec.book_title
            editor_elem = ET.SubElement(edition, 'editor')
            editor_elem.text = publication_info['editor']
            pub_place = ET.SubElement(edition, 'pubPlace', {'role': 'place'})
            pub_place.text = publication_info['place']
            pub_year = ET.SubElement(edition, 'date', {'when': str(publication_info['year']) })
            pub_year.text = str(publication_info['year'])
            pages_scope = ET.SubElement(edition, 'biblScope', {'unit': 'page'})
            if sec.pages_paragraphs[0][0] != sec.pages_paragraphs[-1][0]:
                pages_scope.text = '{}-{}'.format(sec.pages_paragraphs[0][0]+page_num_shift,
                        sec.pages_paragraphs[-1][0]+page_num_shift)
            else:
                pages_scope.text = str(sec.pages_paragraphs[0][0]+page_num_shift)
        if sec.section_type == 'meta':
            # the header information
            header.attrib['{'+nsmap['xml']+'}id'] = 'note_{}'.format(note_num)
            header_title.text = 'TEI P5 encoded version of note {}'.format(note_num)
            # the local subcorpus information
            body.append(tei_raw_note('notebody_{}'.format(note_num),
                sec.pages_paragraphs[0][1]))
            note_num += 1
        if sec.section_type == 'document':
            title = sec.pages_paragraphs[0][1]
            # the header information
            header.attrib['{'+nsmap['xml']+'}id'] = '{}-{}'.format(corp_name,
                    sec.inbook_document_id)
            header_title.text = 'TEI P5 encoded version of "{}"'.format(title)
            bibl_title = ET.SubElement(bibl, 'title', {'level': 'a'})
            bibl_title.text = title
            # the local subcorpus information
            tei_pars = []
            for page, par in sec.pages_paragraphs[1:]:
                break_page = False
                if page != previous_page:
                    previous_page = page
                    break_page = page
                # NOTE We hardcode 1 in these ids, since each file contains one text
                tei_par = tei_raw_paragraph('txt_1.{}-ab'.format(par_num),
                        par, break_page=break_page+page_num_shift if break_page else 0)
                tei_pars.append(tei_par)
                par_num += 1
            doc = tei_raw_document('txt_{}-div'.format(sec.inbook_document_id),
                    tei_pars, title=title, type=
                    # TODO we need this to be more fine-grained
                    ('document-sejmik-resolution' if sec.pertinence else 'document-sejmik-other'))
            body.append(doc)
        doc_pairs.append((tei_corp, header))
    return doc_pairs

def segment_id(token_counter):
    token_counter['tok_num'] += 1
    return 'segm_1.{}-seg'.format(token_counter['tok_num'])

def tei_segmentation_sections(corp_name, pathed_sections):
    """
    Given an arbitrary corpus name as a string and parsed sections (page-number, paragraph tuples),
    generate a XML represantation for corpus' segmentation.
    """
    tei_corps = []

    for sec in pathed_sections:
        par_num = 1
        sent_num = 1
        token_id_counter = { 'tok_num': 0, 'corp_name': corp_name }
        tei_corp, body = tei_empty_subcorpus(name='segm', lang='pl')
        for local_par_n, (page, par) in enumerate(sec.pages_paragraphs):
            tei_par = tei_paragraph_elem('segm_{}-p'.format(par_num))
            if local_par_n == 0:
                raw_par_id = 'txt_{}-div-title'.format(sec.inbook_document_id)
            else:
                raw_par_id = 'txt_1.{}-ab'.format(par_num-1)
            ends = [] # end offsets of each token
            for sent in par:
                tei_sent = tei_sentence_elem('segm_{}.{}-s'.format(par_num, sent_num))
                tei_par.append(tei_sent)
                for pos_n, position in enumerate(sent):
                    real_token = position # if it's a list, we'll have to dig to the dicts
                    end = 0
                    if type(real_token) == dict:
                        offset = real_token['offset']
                        end = offset + len(real_token['orth'])
                    while type(real_token) != dict:
                        try:
                            offset = real_token[0]['offset']
                            end = offset + sum([len(segm['orth'] for segm in real_token)])
                        except TypeError:
                            pass
                        real_token = real_token[-1]
                    # is there a space before?
                    is_after_pause = True
                    if ends and ends[-1] == offset: # no intervening space between this and previous token
                        is_after_pause = False
                    ends.append(end)
                    if type(position) == dict:
                        tei_seg = tei_segm_segment_elem(segment_id(token_id_counter),
                                position['orth'], position['offset'], is_after_pause,
                                raw_par_id)
                        tei_sent.append(tei_seg)
                    else: # a list of alternative paths throught the sentence graph positions
                        tei_choice = tei_parenthesis_choice_elem(position, is_after_pause,
                                token_id_counter, raw_par_id)
                        tei_sent.append(tei_choice)
                sent_num += 1
            body.append(tei_par)
            par_num += 1
        tei_corps.append(tei_corp)
    return tei_corps

def tei_morphosyntax_sections(corp_name, pathed_sections):
    tei_corps = []

    #for sec, disamb_sec in zip(pathed_sections, parsed_sections):
    for sec in pathed_sections:
        par_num = 1
        sent_num = 1
        # here start from 1, because we increment after assigning the number
        token_id_counter = { 'tok_num': 1, 'corp_name': corp_name }
        tei_corp, body = tei_empty_subcorpus(name='morph', lang='pl')
        for par_num, (page, par) in enumerate(sec.pages_paragraphs):
            tei_par = tei_paragraph_elem('morph_{}-p'.format(par_num))
            ends = [] # end offsets of each token
            for sent in par:
                tei_sent = tei_sentence_elem('morph_{}.{}-s'.format(par_num, sent_num))
                tei_par.append(tei_sent)
                for pos_n, position in enumerate(sent):
                    real_token = position # if it's a list, we'll have to dig to the dicts
                    end = 0
                    if type(real_token) == dict:
                        offset = real_token['offset']
                        end = offset + len(real_token['orth'])
                    while type(real_token) != dict:
                        try:
                            offset = real_token[0]['offset']
                            end = offset + sum([len(segm['orth'] for segm in real_token)])
                        except TypeError:
                            pass
                        real_token = real_token[-1]
                    # is there a space before?
                    is_after_pause = True
                    if ends and ends[-1] == offset: # no intervening space between this and previous token
                        is_after_pause = False
                    ends.append(end)
                    if type(position) == dict:
                        tei_seg = tei_morphos_segment_elem(token_id_counter, position,
                                is_after_pause)
                        tei_sent.append(tei_seg)
                    else:
                        for path in position:
                            for tok_n, token in enumerate(path):
                                if tok_n == 0:
                                    tei_seg = tei_morphos_segment_elem(token_id_counter, token,
                                            is_after_pause)
                                else:
                                    tei_seg = tei_morphos_segment_elem(token_id_counter, token,
                                            path[tok_n-1]['offset']+len(path[tok_n-1]['orth'])
                                            != token['offset'])
                                tei_sent.append(tei_seg)
                sent_num += 1
            body.append(tei_par)
            par_num += 1
        tei_corps.append(tei_corp)
    return tei_corps

def write_tei_corpus(output_path, corp_name, sections, pathed_sections, page_num_shift=0,
        publication_info={}):
    output_path = '{}/{}'.format(output_path, corp_name.replace(' ', '_'))
    if not os.path.isdir(output_path):
        os.makedirs(output_path)
    doc_pairs = tei_raw_corpus(corp_name, sections, page_num_shift=page_num_shift, publication_info=publication_info)
    segm_sections = tei_segmentation_sections(corp_name, pathed_sections)
    morphos_sections = tei_morphosyntax_sections(corp_name, pathed_sections)
    for (raw_corp, header), segm_corp, morphos_corp in zip(doc_pairs, segm_sections, morphos_sections):
        dir_name = header.attrib['{'+nsmap['xml']+'}id']
        dir_path = '{}/{}'.format(output_path, dir_name)
        if not os.path.isdir(dir_path):
            os.mkdir(dir_path)
        with open('{}/text.xml'.format(dir_path), 'wb+') as text_file:
            tree = ET.ElementTree(raw_corp)
            tree.write(text_file, encoding='utf-8', xml_declaration=True, pretty_print=True)
        with open('{}/header.xml'.format(dir_path), 'wb+') as header_file:
            tree = ET.ElementTree(header)
            tree.write(header_file, encoding='utf-8', xml_declaration=True, pretty_print=True)
        with open('{}/ann_segmentation.xml'.format(dir_path), 'wb+') as segm_file:
            tree = ET.ElementTree(segm_corp)
            tree.write(segm_file, encoding='utf-8', xml_declaration=True, pretty_print=True)
        with open('{}/ann_morphosyntax.xml'.format(dir_path), 'wb+') as morphos_file:
            tree = ET.ElementTree(morphos_corp)
            tree.write(morphos_file, encoding='utf-8', xml_declaration=True, pretty_print=True)
