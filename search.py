import argparse
from cmd import Cmd
import re
from termcolor import colored, cprint

from popbot_src.subset_getter import load_file_list
from popbot_src.parsed_token import ParsedToken

argparser = argparse.ArgumentParser(description='Search the corpus for phrases in context.')
argparser.add_argument('file_list_path')
args = argparser.parse_args()

all_sections = load_file_list(args.file_list_path)
parsed_section_pars = []
# Convert string paragraphs to list of ParsedToken objects.
for sec in all_sections:
    parsed_pages_paragraphs = []
    for pg, par in sec.pages_paragraphs:
        parsed_pages_paragraphs.append((pg, [ParsedToken.from_str(t) for t in par.strip().split()]))
    parsed_section_pars.append(parsed_pages_paragraphs)

class SearchShell(Cmd):
    prompt = '(search) '
    intro = 'Welcome to populobot search.'

    def do_lex(self, patterns):
        """Find phrases containing the given lexeme sequence and display them in context."""
        patterns = patterns.split()
        if len(patterns) == 0:
            print('No lexemes given.')
            return
        # Sort regexes and verbatim lexemes.
        for pa_i, pattern in enumerate(patterns):
            if pattern.startswith('RE:'):
                patterns[pa_i] = pattern[len('RE:'):]
            else:
                patterns[pa_i] = '^{}$'.format(pattern)
        matches_count = 0
        for sec_n, pages_paragraphs in enumerate(parsed_section_pars):
            for pg, tokens in pages_paragraphs:
                for t_i, token in enumerate(tokens):
                    if re.search(patterns[0], token.lemma):
                        # Check if the rest of tokens match.
                        for shift in range(1, len(patterns)):
                            if (t_i + shift >= len(tokens)
                               or not re.search(patterns[shift], tokens[t_i + shift].lemma)):
                                break
                        else:
                            forms = [t.form for t in tokens]
                            sec = all_sections[sec_n]
                            cprint('{} ({}), {}: file {}'.format(sec.deparsed_title(),
                                                                 sec.date.year if sec.date else '?',
                                                                 sec.book_title, pg),
                                   'blue')
                            matches_count += 1
                            print(' '.join(forms[:t_i]), colored(' '.join(forms[t_i:t_i+len(patterns)]), 'red'),
                                  ' '.join(forms[t_i+len(patterns):]))
        print('{} matches found.'.format(matches_count))

SearchShell().cmdloop()
