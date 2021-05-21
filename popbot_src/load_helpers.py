import datetime
import doctest
import re
import roman

MONTHS = '(stycze?[nń])|(luty?)|(marz?e?c)|(kwie[tc]i?e?[nń])|(maj)|(czerwi?e?c)|(lipi?e?c)|(sierpi?e?[nń])|(wrze[sś]i?e?[nń])|(październik)|(listopad)|(grudz?i?e?[nń])|([ji]anuar)|(februar)|(mart)|(april)|(mai)|([ji]u[nl]i)|(august)|(septemb)|(octob)|(decemb)'

meta_signs = [ # characteristic elements for a meta section
            # page range at the end
            re.compile('\\d+[-—]'),
            re.compile('[-—]\\d+'),
            # "Rękopis"
            re.compile('^.?.?Rp\\.'),
            # "mowa o"
            re.compile(' mowa o ', flags=re.IGNORECASE),
            # evident footnote
            re.compile('^[\\WiIvVxX]{1,3} [^\\\\]{1,40}$'),
            # number range
            re.compile('[0-9]-[0-9]'),
            # anachronistic vocabulary
            re.compile('(wsp[oöó0][lł)|(]czesn)|(De[oc]r\\.)|(Vol\\.)|(Vol.? leg)|(VL\\.)|(Dr\\.)|(Fasc\\.)|([fF]ol\\.)|(Hal\\. Rel\\.)|(Castr\\. Hal\\.)|(Hal\\. Laud\\.)|(Cop\\. Castr\\.)|(Lauda Dobrinensia)|(Monit\\.? Comit\\.? Pol\\.?)|( z?ob\\.)|( str\\.)|(mowa tu)|(rkp\\.)|(rękopis)|jak to utrzymy', flags=re.IGNORECASE)
        ]

# Characteristic elements in a heading. Those of second order get -1 if there is no first order signs.
resolution_titles = [re.compile(s) for s in ['Artyk', 'Articuli', 'Postanowien', 'Uchwał[ay]', 'Deklarac', 'Laudu?m?a?', 'Konfedera', 'Instru[kc]', 'Kwit\\s', 'Pokwitowan']]
other_titles = [re.compile(s) for s in ['Uniwersa[lł]', 'Wezwanie', 'Mandat', 'Legac[yj]', 'Deputac[yj]', 'Pełnomocnic', 'Poselstwo', 'App?robac[yj]a', 'Odpowiedź', 'List', 'Mowa', 'Wotum', 'Zdanie', 'Pokazowan', 'Okazowan', 'Popis', 'Manifest', 'Protest', 'Reprotest', 'Reskrypt', 'Uniwersał', 'Actum', 'Zjazd', 'D[iy]ar[iy]usz', 'Relac', 'Zapisk', 'Sejmik', 'Zebranie', 'Continuatio', 'Limitatio', 'Literae', 'Zebrani', 'Zaświadczenie', 'Stwierdzenie', 'Att?estac', 'Zagajen', 'Upomnien', 'Szlachta', 'Ziemian', 'Sejmik', 'Kasztel', 'S[ąę]d', 'Chor', 'Podkomo', 'Taxa']]
heading_signs_1ord = (
    # square brackets used to number sections in editions
    [re.compile('^\\[.*\\]')]
    +
    # titles - each of those will count as one occurence of a sign
    resolution_titles + other_titles)

heading_signs_2ord = ([
    re.compile('\\d+'),
    # numbers put in words
    re.compile('(pierwsz)|(drug)|(wt[oó]r)|(dwa)|(trz[ae][cd]z?)|(czwart)|(czter)|(pi[ąę][tc])|(sz[óe][śs][tć])|(si[eó]de?m)|([oó][sś]i?e?m)|(dziewi[ęą][tć])|(dzie[sś]i?[ęą][tcć])|(na[śs][tć])|(st[oa])|(setn?)|(tysi[ęą]c)|(prim)|(secund)|(terti)|(quart)|(quint)|(se[xg])|(vice)|(esim)|(cent)|(mille)|( [xXvViIl]{1,3} )'
        # numbering - also days, years
        + '|\\d+'
        # months
        + '|' + MONTHS)]
    +
    # types of documents/assemblies
    [re.compile(s, flags=re.IGNORECASE) for s in ['przedsejmo', 'konwokacyj', 'deput', 'zwołuj', 'kwituj', 'wyboru', 'elekc[jy]', 'wzywa', 'ruszenia', 'posłom', 'skład', 'zwołu']]
    +
    # instances issuing documents
    [re.compile(s, flags=re.IGNORECASE) for s in ['sejmiku', 'conventus', 'palatinatu', 'przedsejmo', 'konwokacyj', 'deput', 'województwa', 'ziemi', 'księstw', 'rycerstw', 'szlachty', 'ziemian']])

# The number of antisigns in a given fragment is subtracted from the number of signs.
heading_antisigns = ([
    re.compile('\\D0+'), # isolated zeros are bogus
    ]
    +
    # some verb endings
    [re.compile(s) for s in ['[ae]my[,\\.\\s]', '[aeyi]ć[,\\.\\s]', '[iyaeąę]ł[ay]?[,\\.\\s]', '[iae[iaeąę]]li?[,\\.\\s]', '[sś]my[,\\.\\s]', 'ąc[aey]?[mj]?u?[,\\.\\s]', '[aoe]n[yieaą][jm]?[,\\.\\s]']]
    +
    # other out of place vocabulary
    [re.compile(s, flags=re.IGNORECASE) for s in ['\\smy\\s', 'ichm', 'jmp', 'jkr', '\\smość', '\\smci', '\\span(a|u|(em))?\\s', 'Dr\\.?\\s', '\\sby[lł]', 'działo', 'brak', 'miasto', '\\saby\\s', '\\siż\\s', '\\sże\\s', 'początk', 'pamięci', 'panow', '\\stu(taj)?\\s', 'tzn', 'tj', 'według', 'wedle', 'obacz', '\\sakta\\s', 'mowa tu\\s', 'p[\\.,] \\d', 'obtulit', 'feria', 'festum', 'decretor', 'poborca', 'naprzód', 'dokumentacja', 'literatura', 'wierzytelna', ' s\\. ', 'nieprawy', 'działo s']])

ocr_corrections = {
        'lnstru': 'Instru',
        'rn ': 'm ',
        'ćm ': 'em ',
        'ćj ': 'ej ',
        'wv': 'w',
        '^ ?@': '§',
        '^ ?%': '§',
        '^ ?&': '§',
        '^ ?ś ': '§ ',
        '^ ?g ': '§ ',
        ' lmc': ' Imc',
        ' ct ': ' et '
        }

def ocr_corrected(paragraph):
    for patt, corr in ocr_corrections.items():
        paragraph = re.sub(patt, corr, paragraph)
    return paragraph

# Meta section detection.
def is_meta_fragment(fragment, config, verbose=False):
    if len(fragment) < 9:
        if verbose:
            print('Too few characters in {}'.format(fragment))
        return True
    if any([(len(line) > config['max_nonmeta_line_len']) for line in fragment.split('\n')]):
        if verbose:
            print('There is a line that is too long in fragment {}'.format(fragment))
        return True
    if len(fragment) < 800:
        for sign in meta_signs:
            if sign.search(fragment):
                if verbose:
                    print('Found {} in {}'.format(sign, fragment))
                return True
    # If a large part of the fragment of non-alphabetic (re.sub removes alphabetics for the check)
    if len(fragment) > 0 and len(re.sub('[^\\W0-9]', '', fragment)) / len(fragment) >= 0.65:
        if verbose:
            print('Too much non-alphabetic in {}'.format(fragment))
        return True
    # If almost a majority of the fragment's tokens are very short (happens in footnotes)
    tokens = [t for t in re.split('\\s', fragment) if len(t) > 0]
    if len(tokens) >= 4 and len([t for t in tokens if len(t) <= 2]) > 0.48 * len(tokens):
        if verbose:
            print('Very short tokens in {}'.format(fragment))
        return True
    # If there are fully uppercase words.
    if len(tokens) < 10:
        for t in tokens:
            if len(t) > 3 and re.sub('[IVXCLM]', '', t) != t and t == t.upper() and t != t.lower():
                if verbose:
                    print('Fully capitalized {} in {}'.format(t, fragment))
                return True
    # If the majority of words are capitalized or numbers, or non-alphanumeric.
    titles_presence = any([True
        for s in resolution_titles+other_titles+[re.compile('[kK]ról [pP]ols'), re.compile('^We? ')]
        if s.search(fragment)])
    if not titles_presence and len(tokens) >= 3:
        capit_or_num_count = (
                len([t for t in tokens if (t[0] != t[0].lower()) or (re.search('[\\W0-9]', t))])
        )
        if capit_or_num_count > 0.85 * len(tokens):
            if verbose:
                print('Almost all capitalized or numbers in {}'.format(fragment))
            return True
        if capit_or_num_count > 0.65 * len(tokens):
            # Be more liberal if may be a section.
            signs_1ord = [s.search(fragment) for s in heading_signs_1ord]
            if len(signs_1ord) <= 1:
                if verbose:
                    print('Majority capitalized or numbers in {}'.format(fragment))
                return True
    # If there are many footnote point-like places.
    # (look also for footnotes looking like this: "a )" - it's the second sub-pattern before the
    # ending paren)
    if len(fragment) < 380 and len(list(re.findall('(((^| ).)|(. ))\\)', fragment))) >= 2:
        if verbose:
            print('Too many footnote point-like places in {}'.format(fragment))
        return True
    # If there is very few kinds of characters used
    if len(fragment) in range(2, 17) and len(set(fragment.lower())) <= max(2, len(fragment) / 3):
        if verbose:
            print('Few character types in {}'.format(fragment))
        return True
    # If large percentage of tokens is abbreviated
    if len(re.findall('\\b[A-Za-z]{1,5}\\.', fragment)) > (len(fragment.split(' ')) * 0.33):
        if verbose:
            print('Too many tokens are abbreviations in {}'.format(fragment))
        return True
    return False

# Headings detection.
def heading_score(paragraph, config, length_discount=70, verbose=False):
    """
    Compute a score estimating how likely the paragraph is to be a heading. Generally fragments
    with heading score above 0 can be considered headings.

    The length_discount argument controls per how many characters in the fragment one full
    point is subtracted from the score.
    """
    if len(paragraph) < 15 or len(paragraph) > config['max_heading_len']:
        return -1.5

    # Do some possible cleanup.
    paragraph = paragraph.replace('-', '')

    signs_1ord = [s.search(paragraph) for s in heading_signs_1ord]
    signs_1ord_count = len([s for s in signs_1ord if s])
    if verbose:
        print('+{:.1f} from first-order signs'.format(signs_1ord_count))
    signs_2ord = [s.search(paragraph) for s in heading_signs_2ord]
    signs_2ord_count = len([s for s in signs_2ord if s])
    if verbose:
        print('+{:.1f} from second-order signs'.format(signs_2ord_count))
    if signs_1ord_count == 0:
        signs_2ord_count -= 1.5
        if verbose:
            print('-1.5 from no first-order signs')
    elif not len([s.search(paragraph) for s in heading_signs_1ord[:25]]):
        signs_2ord_count -= 1.0
        if verbose:
            print('-1.0 from no first-order signs in the first 25 characters')
    signs_count = signs_1ord_count + signs_2ord_count

    antisigns = [s.search(paragraph) for s in heading_antisigns]
    antisigns_count = len([s for s in antisigns if s]) * 0.6
    if verbose:
        print('-{:.1f} from anti-signs {}'.format(antisigns_count, [s.group(0) for s in antisigns if s]))

    # If the first letter is not uppercase, it's a strong signal against.
    try:
        first_letter = re.search('[^\\W\\d_]', paragraph).group(0)
        if first_letter.lower() == first_letter:
            if verbose:
                print('-1.0 from lowercase first letter')
            antisigns_count += 1
    # Penalize also no-letter paragraphs if such are found.
    except AttributeError:
        antisigns_count += 1

    signs_count -= antisigns_count
    if verbose:
        print(paragraph, signs_count, 'signs')

    # To be positive, the signs count must be more than a factor dependent on paragraph length
    if verbose:
        print('-{:.1f} from paragraph length'.format((len(paragraph) / length_discount)))
    return signs_count - (len(paragraph) / length_discount)

myrady = re.compile('[^\\w]{0,4}my.? r[au]d', flags=re.IGNORECASE)
def doc_beginning_score(paragraph, config):
    signs_count = -0.5
    sign_1ord = myrady.match(paragraph)
    signs_2ord = ['dygnitarze', 'urzędnic', 'rycerstw', 'obywatel', 'panow', 'wszyst', 'wszytk', 'koronn', 'świec', 'duchown', 'ziem']
    if sign_1ord is not None or (len(paragraph) > 0 and paragraph[0].lower() != paragraph[0]):
        signs_count += 0.3
        for sign in signs_2ord:
            if paragraph.lower().find(sign):
                signs_count += 0.3 / len(signs_2ord)
    return signs_count

month_words_to_numbers = [
        # NOTE conventionally replace all i with j, convert to lowercase for this matching
        ('stycz', 1),
        ('janua', 1),
        ('lut', 2),
        ('febr', 2),
        ('mar', 3),
        ('kwjet', 4),
        ('apr', 4),
        ('maj', 5),
        ('czerw', 6),
        ('jun', 6),
        ('ljp', 7),
        ('jul', 7),
        ('sjerp', 8),
        ('aug', 8),
        ('wrze', 9),
        ('sept', 9),
        ('paźdz', 10),
        ('octob', 10),
        ('list', 11),
        ('nov', 11),
        ('grud', 12),
        ('dece', 12),
        ]
def extract_dates(string, verbose=False):
    """Find dates in string and return them as a list of triples (day, month, year).

    >>> extract_dates("4. U niwe-rsal zjazdu do starostów o dawanie pomocy posłom, wysłanym do k-ro'lewnej Anny do Płocka, z Osieka- 4 października 1572 -r. eis huiuscemodi litteris. Uw. Po akcie pomieszczone ~w rękopisie. mz k. 72—72")
    [(4, 10, 1572)]
    >>> extract_dates('9 V 1955')
    [(9, 5, 1955)]
    """
    dates = []
    month_words = re.compile(MONTHS) # from global
    month_romandigs = re.compile('[xXvViI]{1,3}')
    for month_find in list(month_words.finditer(string.lower())) + list(month_romandigs.finditer(
                        string)):
        month_number = False
        year_number = False
        day_number = False

        # try to extract the month
        found_month = month_find.group(0)
        if verbose:
            print('{} - month candidate'.format(found_month))

        # For Roman digits, parse them, for the rest take then number from MONTHS.
        if not month_romandigs.match(found_month):
            for (cue, number) in month_words_to_numbers:
                if cue in found_month.replace('i', 'j'):
                    month_number = number
                    break
        else:
            try:
                month_number = roman.fromRoman(found_month)
            except roman.InvalidRomanNumeralError:
                pass
        if not month_number:
            continue
        if verbose:
            print('{} - month number'.format(month_number))

        next_space_ind = string[month_find.end():].find(' ')
        next_blank_ind = string[month_find.end():].find('\n')
        if next_space_ind == -1 or (next_blank_ind >= 0 and next_blank_ind < next_space_ind):
            next_space_ind = next_blank_ind
        next_space_ind = month_find.end() + next_space_ind # align it in the whole str context
        prev_space_ind = string[:month_find.start()].rfind(' ')
        prev_blank_ind = string[:month_find.end()].rfind('\n')
        if prev_space_ind == -1 or (prev_blank_ind >= 0 and prev_blank_ind > prev_space_ind):
            prev_space_ind = prev_blank_ind

        if next_space_ind == -1:
            if verbose:
                print('end of the string, aborted')
            continue

        reversed_order = False # year-month-day or month-day-year

        # Try to extract the next number. This may be the year or the day.
        expected_num_str = string[next_space_ind+1:next_space_ind+5]
        if verbose:
            print('{} - expected number (after month)'.format(expected_num_str))
        try:
            first_num_str = re.search('\\d{1,4}', expected_num_str).group(0)
        except AttributeError: # if search() produces None
            continue
        if len(first_num_str) == 3:
            continue
        first_num = int(first_num_str)
        if len(first_num_str) == 4:
            year_number = first_num
            if year_number < 1500 or year_number > 1795:
                if verbose:
                    print('Rejected the year number {}'.format(year_number))
                year_number = False
        else: # we've eliminated the 3-letter case earlier
            day_number = first_num
            if (day_number > 31
                    or (month_number == 2 and day_number > 29)
                    or (month_number in [4,6,9,11] and day_number > 30)):
                if verbose:
                    print('{} day number rejected for month {}'.format(day_number, month_number))
                day_number = False
            else:
                if verbose:
                    print('{} - day number'.format(day_number))
                reversed_order = True
                try:
                    # If this suceeds, we have a month-day-year date.
                    expected_num2_str = re.search('\\d{4}', string[next_space_ind+1+len(first_num_str)+1
                            # give allowance for "anno domini" etc.
                            :next_space_ind+1+len(first_num_str)+20]).group(0)
                    year_number = int(expected_num2_str)
                except AttributeError:
                    pass
                if year_number and year_number < 1500 or year_number > 1795:
                    if verbose:
                        print('Rejected the year number {}'.format(year_number))
                    year_number = False
                    day_number = False
                elif year_number:
                    if verbose:
                        print('{} - year number'.format(year_number))
                    try:
                        datetime.date(int(year_number), int(month_number), int(day_number))
                        dates.append((day_number, month_number, year_number))
                    except ValueError:
                        if verbose:
                            print('Invalid date {}-{}-{}'.format(day_number, month_number, year_number))
                        continue
                    continue

        # If we don't have a date by now, we would need some chars before the month.
        if prev_space_ind == -1:
            if verbose:
                print('beginning of the string, aborted')
            continue

        # Try the alternative order, as in '1670 Januarius, 22'.
        if reversed_order:
            expected_year_str = string[prev_space_ind-4:prev_space_ind]
            if verbose:
                print('{} - expected year string (before month)'.format(expected_year_str))
            if re.match('^\\d+$', expected_year_str):
                year_number = int(expected_year_str)
                if year_number < 1500 or year_number > 1795:
                    if verbose:
                        print('Rejected the year number {}'.format(year_number))
                    year_number = False
                else:
                    reversed_order = True
            if not year_number:
                continue
            if verbose:
                print('{} - year number'.format(year_number))
        # Try to extract the day for the normal order day-month-year
        else:
            expected_day_str = string[max(prev_space_ind-3, 0):prev_space_ind]
            if verbose:
                print('{} - expected day string'.format(expected_day_str))
            try:
                day_number = int(re.search('\\d+', expected_day_str).group(0))
            except AttributeError:
                continue
            if (day_number > 31
                    or (month_number == 2 and day_number > 29)
                    or (month_number in [4,6,9,11] and day_number > 30)):
                if verbose:
                    print('{} day number rejected for month {}'.format(day_number, month_number))
                continue
            if verbose:
                print('{} - day number'.format(day_number))

        if day_number and month_number and year_number:
            if verbose:
                print('Date found: {} {} {}'.format(day_number, month_number, year_number))
            try:
                datetime.date(int(year_number), int(month_number), int(day_number))
                dates.append((day_number, month_number, year_number))
            except ValueError:
                if verbose:
                    print('Invalid date {}-{}-{}'.format(day_number, month_number, year_number))
                continue

    return dates

def fuzzy_match(str1, str2):
    """For now, fuzzy match is actually exact."""
    # TODO make it fuzzy.
    return re.sub('\\s|(\\\\n)', '', str1) == re.sub('\\s|(\\\\n)', '', str2)

def join_linebreaks(text, clean_end_shades=True):
    """
    Join a text split into lines, optionally removing junk characters occuring at the end due
    to OCR being confused by shades.
    """
    lines = text.split('\n')
    joined_text = ''
    for line in lines:
        if len(joined_text) > 0:
            if re.search(' [^aeikouwyz]$', line):
                line = line[:-2]
            if joined_text[-1] == '-' and line[0].islower():
                joined_text = joined_text[:-1] + line
                continue
        joined_text += ' ' + line
    return joined_text

doctest.testmod()

def is_pertinent(section, config):
    """Assess whether the Section class object is research-pertinent (ie, a resolution of an assembly)."""
    # Consider first actual paragraphs.
    if len(section.pages_paragraphs) <= 1:
        return False # no-content sections are nonpertinent
    if 'sędziowie' in section.pages_paragraphs[1][1]: # judicial lauda from Ruthenia
        return False
    if myrady.match(section.pages_paragraphs[1][1]) is not None:
        return True
    # A second chance if there is some lower-hierarchy heading as the first paragraph.
    if len(section.pages_paragraphs) > 2 and myrady.match(section.pages_paragraphs[2][1]) is not None:
        return True
    # Consider the title.
    signs_pert_titles = [s.search(section.title(config)) for s in resolution_titles]
    if len([s for s in signs_pert_titles if s is not None]) > 0:
        return True
    return False
