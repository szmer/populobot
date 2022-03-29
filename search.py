import argparse
from cmd import Cmd
import re
from termcolor import colored, cprint

from popbot_src.subset_getter import load_file_list
from popbot_src.parsed_token import ParsedToken
from popbot_src.section import tuple_to_datetime

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
        """Find phrases containing the given lexeme sequence and display them in context. You can also provide a regular expression with an RE: mark."""
        patterns = patterns.split()
        date_range = [pat for pat in patterns if pat.startswith('DR:')]
        patterns = [pat for pat in patterns if not pat.startswith('DR:')]
        if len(patterns) == 0:
            print('No lexemes given.')
            return
        # Unpack the date range if present.
        if date_range:
            if len(date_range) > 1:
                print('More than one date range given.')
                return
            try:
                date_range = [tuple_to_datetime(d.split('-')) for d in date_range[0].split(':')[1:]]
                assert len(date_range) == 2
            except:
                print('Cannot parse the date range.')
                return
        # Sort regexes and verbatim lexemes.
        for pa_i, pattern in enumerate(patterns):
            if pattern.startswith('RE:'):
                patterns[pa_i] = pattern[len('RE:'):]
            else:
                patterns[pa_i] = '^{}$'.format(pattern)
        matches_count = 0
        for sec_n, pages_paragraphs in enumerate(parsed_section_pars):
            if date_range and (not all_sections[sec_n].date
                               or all_sections[sec_n].date < date_range[0]
                               or all_sections[sec_n].date >= date_range[1]):
                continue
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
