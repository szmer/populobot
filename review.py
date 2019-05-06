import argparse
from queue import Queue
from cmd import Cmd
from copy import copy, deepcopy

from indexing_common import load_indexed
from manual_decision import DateDecision, MergeSectionDecision, SplitSectionDecision, PertinenceDecision

argparser = argparse.ArgumentParser(description='Review and correct source edition indexing performed by the loading script.')
argparser.add_argument('parsed_file_path')
argparser.add_argument('--output_file', '-o')

args = argparser.parse_args()

edition_sections = load_indexed(args.parsed_file_path)
current_section_n = 0
# Here we store decisions paired with states of edition_sections that preceded them.
undo_queue = Queue()
redo_queue = Queue()
# At the end, we just treat the undo queue as the source of all decisions made.

def saved_section_list(saved_section_n):
    new_list = copy(edition_sections)
    new_list[saved_section_n] = deepcopy(edition_sections[saved_section_n])
    return new_list

class ReviewShell(Cmd):
    prompt = '(review) '
    intro = ('Welcome to populobot review.\n'
            'Documents with asterisk are marked as nonpertinent.')

    def print_section(self, section_n):
        print('{}{} {}'.format(edition_sections[section_n].section_type.upper(),
            ('*' if edition_sections[section_n].section_type == 'document'
            and not edition_sections[section_n].pertinence else ''),
            edition_sections[section_n].pages_paragraphs[0][1][:100]))
        print('Dated: {}'.format(edition_sections[section_n].date))

    def commit_save(self, decision, sections_state):
        """Handle the undo and redo queues for the decision and sections
        state that was already saved by the caller."""
        undo_queue.put((decision, sections_state))
        global redo_queue
        redo_queue = Queue()

    def do_section(self, ignored_args):
        """Print basic information on the current section."""
        global current_section_n
        self.print_section(current_section_n)

    def do_pars(self, ignored_args):
        """Print numbered paragraph snippets from the current section."""
        global current_section_n
        for par_n, (scanpage, paragraph) in enumerate(edition_sections[current_section_n].pages_paragraphs):
            print('{}: "{}"'.format(par_n, paragraph[:100]))

    def do_near(self, ignored_args):
        """Preview nearest sections to the current one."""
        for section_n, section in enumerate(edition_sections):
            if abs(section_n - current_section_n) < 5:
                print('{} {}: {} {}'.format(
                    '*' if section_n == current_section_n else ' ',
                    section_n,
                    edition_sections[section_n].section_type.upper(),
                    edition_sections[section_n].pages_paragraphs[0][1][:40]))

    def do_jump(self, target_section_n):
        """Go to the supplied target_section_n."""
        target_section_n = int(target_section_n)
        if target_section_n < 0 or target_section_n >= len(edition_sections):
            print('Illegal section index.')
        else:
            global current_section_n
            current_section_n = target_section_n
            self.do_section('')

    def do_p(self, ignored_args):
        """Go to the previous section."""
        global current_section_n
        if current_section_n > 0:
            current_section_n -= 1
            self.do_section('')
        else:
            print('Already at the beginning of the edition.')

    def do_n(self, ignored_args):
        """Go to the next section."""
        global current_section_n
        if current_section_n < len(edition_sections) - 1:
            current_section_n += 1
            self.do_section('')
        else:
            print('Already at the end of the edition.')

    def do_undo(self, ignored_args):
        """Undo the last correction decision."""
        global edition_sections
        if not undo_queue.empty():
            undone_state = undo_queue.get()
            redo_queue.put((undone_state[0], edition_sections))
            # Revert to the remembered state.
            edition_sections = undone_state[1]
            print('Undone {}'.format(vars(undone_state[0])))
        else:
            print('Undo queue is empty')

    def do_redo(self, ignored_args):
        """Redo the last cancelled correction decision."""
        global edition_sections
        if not redo_queue.empty():
            redone_state = redo_queue.get()
            undo_queue.put((redone_state[0], edition_sections))
            # Revert to the remembered state.
            edition_sections = redone_state[1]
            print('Redone {}'.format(vars(redone_state[0])))
        else:
            print('Redo queue is empty')

    #
    # Applying correction decisions.
    #
    def do_pert(self, ignored_args):
        """Mark the current section as pertinent (works for documents)."""
        global current_section_n
        section = edition_sections[current_section_n]
        if section.section_type != 'document':
            print('Pertinence decisions are applicable only for document sections.')
            return
        if section.pertinence == True:
            print('The section is already marked as pertinent.')
            return
        sections_state = saved_section_list(current_section_n)
        decision = PertinenceDecision(True,
                section.pages_paragraphs[0][1],
                section.pages_paragraphs[0][0])
        section.pertinence = True
        self.commit_save(decision, sections_state)
        self.do_section('')

    def do_npert(self, ignored_args):
        """Mark the current section as nonpertinent (works for documents)."""
        global current_section_n
        section = edition_sections[current_section_n]
        if section.section_type != 'document':
            print('Pertinence decisions are applicable only for document sections.')
            return
        if section.pertinence == False:
            print('The section is already marked as nonpertinent.')
            return
        sections_state = saved_section_list(current_section_n)
        decision = PertinenceDecision(False,
                section.pages_paragraphs[0][1],
                section.pages_paragraphs[0][0])
        section.pertinence = False
        self.commit_save(decision, sections_state)
        self.do_section('')

    def do_date(self, newdate):
        """Manually assign a date to the current document. The date should be
        supplied as DD-MM-YYYY, without zeros."""
        global current_section_n
        formatted_date = tuple([int(elem) for elem in newdate.split('-')])
        sections_state = saved_section_list(current_section_n)
        section = edition_sections[current_section_n]
        section.date = formatted_date
        decision = DateDecision(formatted_date, section.title(), section.pages_paragraphs[0][0])
        self.commit_save(decision, sections_state)
        self.do_section('')

    def do_merge(self, ignored_args):
        """Merge the current section with the previous document section."""
        global current_section_n
        previous_document_n = False
        for section_n in reversed(range(current_section_n)):
            if edition_sections[section_n].section_type == 'document':
                previous_document_n = section_n
                break
        if previous_document_n:
            # We want to save the previous document section as the one that
            # will be actually modified.
            sections_state = saved_section_list(previous_document_n)
            section = edition_sections[current_section_n]
            decision = MergeSectionDecision(section.title(), section.pages_paragraphs[0][0],
                    edition_sections[previous_document_n].pages_paragraphs[-1][-80:],
                    section.pages_paragraphs[0][:80])
            edition_sections[previous_document_n].pages_paragraphs += edition_sections[current_section_n].pages_paragraphs
            del edition_sections[current_section_n]
            current_section_n = previous_document_n
            self.commit_save(decision, sections_state)
            self.do_section('')
        else:
            print('No previous document section to merge to.')

    def do_split(self, args):
        """Split the section on the paragraph_n, creating a new section of
        section_type (meta or document)."""
        paragraph_n, section_type = tuple(args.split())
        try:
            paragraph_n = int(paragraph_n)
        except ValueError:
            print('Invalid paragraph number.')
            return
        global current_section_n
        if paragraph_n >= len(edition_sections[current_section_n].pages_paragraphs):
            print('There is no paragraph numbered {}.'.format(paragraph_n))
            return
        if paragraph_n == 0:
            print('You cannot split on the first paragraph.')
            return
        if not section_type in ['meta', 'document']:
            print('Unknown section type {}.'.format(section_type))
            return
        sections_state = saved_section_list(current_section_n)
        section = edition_sections[current_section_n]
        decision = SplitSectionDecision(section.pages_paragraphs[0][1],
                section.pages_paragraphs[paragraph_n][0],
                section.pages_paragraphs[paragraph_n-1][1][-80:],
                section.pages_paragraphs[paragraph_n][1][:80],
                section_type)
        new_section = deepcopy(section)
        new_section.section_type = section_type
        new_section.pages_paragraphs = new_section.pages_paragraphs[paragraph_n:]
        new_section.guess_date()
        section.pages_paragraphs = section.pages_paragraphs[:paragraph_n]
        edition_sections.insert(current_section_n+1, new_section)
        current_section_n += 1
        self.commit_save(decision, sections_state)
        self.do_section('')

ReviewShell().cmdloop()
