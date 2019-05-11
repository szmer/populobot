import argparse

from popbot_src.indexing_common import load_edition

argparser = argparse.ArgumentParser(description='Load and index an edition of sejmik resolutions from scanned pages.')
argparser.add_argument('config_file_path')
argparser.add_argument('--manual_decisions_file', '-m')


if __name__ == '__main__':
    args = argparser.parse_args()
    load_edition(args.config_file_path, args.manual_decisions_file)
