import argparse
from contextlib import redirect_stdout
from io import StringIO 
import json

from popbot_src.load_helpers import is_meta_fragment
from popbot_src.indexing_common import load_indexed

argparser = argparse.ArgumentParser()
argparser.add_argument('config_file_path', help='The config file describing where to find the corpus'
        ' and its metadata.')
argparser.add_argument('raw_csv_path', help='The csv file containing the loaded edition with no'
        ' further processing.')

args = argparser.parse_args()

with open(args.raw_csv_path) as sections_file:
    edition_sections = load_indexed(sections_file)
with open(args.config_file_path) as config_file:
    config = json.load(config_file)

# Print the HTML.
print('<html><head></head><body>')
for sec in edition_sections:
    if sec.section_type == 'meta':
        content = sec.pages_paragraphs[0][1].replace('\n', '<br>')
        print(f'<p style="background-color: moccasin; font-family: monospace">{content}</p>')
        output = StringIO()
        with redirect_stdout(output):
            is_meta_fragment(sec.pages_paragraphs[0][1], config, verbose=True)
        print(f'<p style="background-color: moccasin"><em>{output.getvalue()}</em></p>')
    else:
        print(f'<h4>{sec.title(config)}</h4>')
        for pg, par in sec.pages_paragraphs:
            content = par.replace('\n', '<br>')
            print(f'<p>{content}</p>')
print('</body></html>')
