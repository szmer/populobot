import argparse

argparser = argparse.ArgumentParser(description='Correct a parsed (with Morfeusz&Conraft) csv file, using a dictionary generated with extract_dictionary.py and PyLucene spellchecking.')
argparser.add_argument('indexed_file_path')
argparser.add_argument('dictionary_file')

args = argparser.parse_args()
