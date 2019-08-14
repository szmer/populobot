import argparse
import json

from popbot_src.indexing_common import load_edition

argparser = argparse.ArgumentParser(description='Load and index an edition of sejmik resolutions from scanned pages.')
argparser.add_argument('config_file_path')
argparser.add_argument('--manual_decisions_file', '-m', default=False)

args = argparser.parse_args()

# keep the config and section variables for easier debugging in interactive mode
with open(args.config_file_path) as config_file:
    config = json.load(config_file)
sections = load_edition(args.config_file_path, args.manual_decisions_file)
