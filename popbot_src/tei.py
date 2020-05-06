import os
import lxml.etree as ET

from popbot_src.parsed_token import ParsedToken

nsmap = {
        'xi': 'http://www.w3.org/2001/XInclude',
        'nkjp': 'http://www.nkjp.pl/ns/1.0',
        'xml': 'http://www.w3.org/XML/1998/namespace',
        None: 'http://www.tei-c.org/ns/1.0'
        }

def tei_segment_elem(id, token : ParsedToken, raw_parent_id):
    """
    Make a segment element for ann_segmentation.xml. Corresp_ attributes point to the raw paragraph
    element id and the substring inside it corresponding to the segment.
    """
    segment = ET.Element('seg', {
        '{'+nsmap['xml']+'}id': id,
        'corresp': 'text.xml#string-range({},{},{})'.format(raw_parent_id, token.corresp_index,
            len(token.form))})
    if not token.pause:
        segment.attr['{'+nsmap['nkjp']+'}nps'] = 'true' # no space before the token
    # Inform of the form for convenience.
    w = ET.SubElement(segment, 'w')
    w.text = token.form
    return segment

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

def tei_empty_subcorpus():
    tei_corp = ET.Element('teiCorpus', nsmap=nsmap)
    # TODO include the global header
    tei = ET.SubElement(tei_corp, 'TEI')
    ET.SubElement(tei, '{'+nsmap['xi']+'}include', {'href': 'header.xml'})
    text = ET.SubElement(tei, 'text')
    body = ET.SubElement(text, 'body')
    return tei_corp, body

def tei_raw_corpus(corp_name, sections):
    """
    A list of pairs: (main XML of the document, the header XML).
    """
    doc_pairs = []
    note_num = 0
    par_num = 0
    # TODO we need to adjust the page numbers here with the ones in editions!
    previous_page = 0
    for sec in sections:
        tei_corp, body = tei_empty_subcorpus()
        # the document header
        header = ET.Element('teiHeader', nsmap=nsmap)
        title_stmt = ET.SubElement(header, 'titleStmt')
        header_title = ET.SubElement(title_stmt, 'title')
        # TODO publicationStmt - subcorpus, availability, license
        source_desc = ET.SubElement(header, 'sourceDesc')
        bibl = ET.SubElement(source_desc, 'bibl', {'type': 'original'})
        pages_scope = ET.SubElement(bibl, 'biblScope', {'unit': 'page'})
        pages_scope.text = '{}-{}'.format(sec.pages_paragraphs[0][0], sec.pages_paragraphs[-1][0])
        if sec.date:
            date = ET.SubElement(bibl, 'date', {'when': sec.date.isoformat()})
            date.text = sec.date.isoformat()
        region = ET.SubElement(bibl, 'region')
        region.text = sections[0].palatinate
        author = ET.SubElement(bibl, 'author')
        author.text = sections[0].author
        ET.SubElement(header, 'revisionDesc')
        # TODO the remaining biblio information - from config?
        if sec.section_type == 'meta':
            # the header information
            header.attrib['{'+nsmap['xml']+'}id'] = '{}-note-{}'.format(corp_name, note_num)
            header_title.text = 'TEI P5 encoded version of note no {}'.format(note_num)
            # the local subcorpus information
            body.append(tei_raw_note('{}-notebody-{}'.format(corp_name, note_num),
                sec.pages_paragraphs[0][1]))
            note_num += 1
        if sec.section_type == 'document':
            title = sec.pages_paragraphs[0][1]
            # the header information
            header.attrib['{'+nsmap['xml']+'}id'] = '{}-doc-{}'.format(corp_name,
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
                tei_par = tei_raw_paragraph('{}-par-{}'.format(corp_name, par_num),
                        par, break_page=break_page)
                tei_pars.append(tei_par)
                par_num += 1
            doc = tei_raw_document('{}-doc-{}'.format(corp_name, sec.inbook_document_id),
                    tei_pars, title=title, type=
                    # TODO we need this to be more fine-grained
                    ('document-sejmik-resolution' if sec.pertinence else 'document-other'))
            body.append(doc)
        doc_pairs.append((tei_corp, header))
    return doc_pairs

def tei_segmentation_sections(corp_name, parsed_sections):
    tei_corps = []
    par_num = 0
    segm_num = 0
    for sec in parsed_sections:
        tei_corp, body = tei_empty_subcorpus()
        # NOTE no segmentation data for "meta" note sections
        if sec.section_type == 'document':
            tei_pars = []
            for page, par in sec.pages_paragraphs[1:]:
                # NOTE currently ignoring page breaks?
                tei_par = tei_paragraph_elem('{}-segm-par-{}'.format(corp_name, par_num))
                raw_par_id = '{}-par-{}'.format(corp_name, par_num)
                # NOTE we currently treat the whole paragraph as one sentence.
                tei_sent = tei_sentence_elem('{}-segm-sent-{}'.format(corp_name, par_num))
                tei_par.append(tei_sent)
                for token in par:
                    tei_seg = tei_segment_elem('{}-segm-seg-{}'.format(corp_name, segm_num),
                            token, raw_par_id)
                    tei_sent.append(tei_seg)
                    segm_num += 1
                tei_pars.append(tei_par)
                par_num += 1
        tei_corps.append(tei_corp)
    return tei_corps

def write_tei_corpus(output_path, corp_name, sections, parsed_sections):
    output_path = '{}/{}'.format(output_path, corp_name.replace(' ', '_'))
    if not os.path.isdir(output_path):
        os.makedirs(output_path)
    doc_pairs = tei_raw_corpus(corp_name, sections)
    segm_sections = tei_segmentation_sections(corp_name, parsed_sections)
    for (raw_corp, header), segm_corp in zip(doc_pairs, segm_sections):
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
