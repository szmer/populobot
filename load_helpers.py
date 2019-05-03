import doctest, re, roman

MONTHS = '(stycze?[nń])|(luty?)|(marz?e?c)|(kwie[tc]i?e?[nń])|(maj)|(czerwi?e?c)|(lipi?e?c)|(sierpi?e?[nń])|(wrze[sś]i?e?[nń])|(październik)|(listopad)|(grudz?i?e?[nń])|([ji]anuar)|(februar)|(mart)|(april)|(mai)|([ji]u[nl]i)|(august)|(septemb)|(octob)|(decemb)'

# Meta section detection.
meta_signs = [ # characteristic elements for a meta section
            # page range at the end
            re.compile('\\d+-\\d+\\.$'),
            # "Rękopis"
            re.compile('^.?.?Rp\\.'),
            # evident footnote
            re.compile('^[\\WiIvVxX]{1,3} [^\\\\]{1,40}$'),
            # number range
            re.compile('[0-9]-[0-9]'),
            # pauses, hyphens
            re.compile('-—'),
            # anachronistic vocabulary
            re.compile('(wsp[oöó0][lł)|(]czesn)|(Vol\\.)|(Fasc\\.)|([fF]ol\.)|(Hal\\. Rel\\.)|(Castr\\. Hal\\.)|(Hal\\. Laud\\.)|(Cop\\. Castr\\.)|(Lauda Dobrinensia)|(Monit\\.? Comit\\.? Pol\\.?)|( z?ob\\.)|( tek[sś])|( str\\.)', flags=re.IGNORECASE)
        ]
def is_meta_fragment(fragment, config):
    for sign in meta_signs:
        if sign.search(fragment):
            ###print(sign, fragment)
            return True
    # If a large part of the fragment of non-alphabetic
    if len(fragment) > 0 and len(re.sub('[^\\W0-9]', '', fragment)) / len(fragment) >= 0.65:
        return True

    # If large percentage of tokens is abbreviated
    ###if fragment.count(' ') > 0 and fragment.count('. ') / fragment.count(' ') >= 0.33:
    ###    return True
    return False

# Headings detection.
# Characteristic elements in a heading. Those of second order get -1 if there is no first order signs.
heading_signs_1ord = ([ 
    # square brackets used to number sections in editions
    re.compile('^\\[.*\\]')]
    +
    # titles - each of those will count as one occurence of a sign
    [re.compile(s) for s in ['Artyk', 'Uchwał[ay]', 'Deklarac', 'Postanowien', 'Uniwersa[lł]', 'Wezwanie', 'Mandat', 'Legac[yj]', 'Deputac[yj]', 'Pełnomocnic', 'Poselstwo', 'Laudu?m?a?', 'Instrukcy?j?[ae]', 'Instructio', 'App?robac[yj]a', 'Konfederacy?j?', 'Odpowiedź', 'List', 'Mowa', 'Wotum', 'Zdanie', 'Pokazowan', 'Okazowan', 'Manifest', 'Protest', 'Reprotest', 'Reskrypt', 'Uniwersał', 'Actum', 'Zjazd', 'D[iy]ar[iy]usz', 'Relac', 'Zapisk', 'Sejmik', 'Zebranie', 'Articuli', 'Continuatio', 'Limitatio', 'Literae', 'Zebrani', 'Zaświadczenie', 'Stwierdzenie', 'Att?estac', 'Kwit\\s']])
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
    [re.compile(s, flags=re.IGNORECASE) for s in ['przedsejmo', 'konwokacyj', 'deput', 'zwołuj', 'kwituj', 'wyboru', 'elekc[jy]', 'wzywa', 'ruszenia', 'posłom']]
    +
    # instances issuing documents
    [re.compile(s, flags=re.IGNORECASE) for s in ['sejmiku', 'conventus', 'palatinatu', 'przedsejmo', 'konwokacyj', 'deput', 'województwa', 'ziemi', 'księstw', 'rycerstw', 'szlachty', 'ziemian']])
# The number of antisigns is subtracted from the number of signs.
heading_antisigns = ([
    re.compile('\\D0+'), # isolated zeros are bogus
    ]
    +
    # verb endings
    [re.compile(s) for s in ['[aeu]j[ąe][,\.\\s]', '[ae]my[,\.\\s]', '[aeyi]ć[,\.\\s]', '[iyaeąę]ł[ay]?[,\.\\s]', '[iae[iaeąę]]li?[,\.\\s]', '[sś]my[,\.\\s]', 'ąc[aey]?[mj]?u?[,\.\\s]', '[aoe]n[yieaą][jm]?[,\.\\s]', 'wszy[,\.\\s]', 'eni[ea]m?[,\.\\s]']]
    +
    # other out of place vocabulary
    [re.compile(s, flags=re.IGNORECASE) for s in ['\\smy\\s', 'ichm', 'jmp', 'jkr', '\\smość', '\\smci', '\\span(a|u|(em))?\\s', 'Dr\\.?\\s', '[A-ZŻŹŁŚ]\\w+[sc]ki(emu)?\\s', '\\sby[lł]', 'działo', 'się', 'brak', 'miasto', '\\saby\\s', '\\siż\\s', '\\sże\\s', 'początk', 'pamięci', 'panow', 'grodzkie\\s', '\\stu(taj)?\\s', 'tzn', 'tj', 'według', 'wedle', 'obacz', '\\sakta\\s', 'mowa tu\\s', 'p[\\.,] \\d', 'obtulit', 'feria', 'festum', 'decretor']])

def heading_score(section, config, verbose=False):
    if len(section) < 15 or len(section) > config['max_heading_len']:
        return -1.5

    # Do some possible cleanup.
    section = section.replace('-', '')

    signs_1ord = [s.search(section) for s in heading_signs_1ord]
    signs_1ord_count = len([s for s in signs_1ord if s])
    if verbose:
        print('+{:.1f} from first-order signs'.format(signs_1ord_count))
    signs_2ord = [s.search(section) for s in heading_signs_2ord]
    signs_2ord_count = len([s for s in signs_2ord if s])
    if verbose:
        print('+{:.1f} from second-order signs'.format(signs_2ord_count))
    if signs_1ord_count == 0:
        signs_2ord_count -= 1.5
        if verbose:
            print('-1.5 from no first-order signs')
    signs_count = signs_1ord_count + signs_2ord_count
    antisigns = [s.search(section) for s in heading_antisigns]
    antisigns_count = len([s for s in antisigns if s]) * 0.6
    if verbose:
        print('-{:.1f} from anti-signs {}'.format(antisigns_count, [s.group(0) for s in antisigns if s]))
    # If the first letter is not uppercase, it's a strong signal against.
    try:
        first_letter = re.search('[^\\W\\d_]', section).group(0)
        if first_letter.lower() == first_letter:
            if verbose:
                print('-1.0 lowercase')
            antisigns_count += 1
    # Penalize also no-letter sections if such are found.
    except AttributeError:
        antisigns_count += 1
    signs_count -= antisigns_count
###    print(section, signs_count, 'signs')
    # To be positive, the signs count must be more than a factor dependent on section length
    if verbose:
        print('-{:.1f} from section length'.format((len(section) / 70)))
    return signs_count - (len(section) / 70)

def doc_beginning_score(section, config):
    signs_count = -0.5
    sign_1ord = re.match('[^\\w]{0,4}my.? r[au]d', section, flags=re.IGNORECASE)
    signs_2ord = ['dygnitarze', 'urzędnic', 'rycerstw', 'obywatel', 'panow', 'wszyst', 'wszytk', 'koronn', 'świec', 'duchown', 'ziem']
    if sign_1ord is not None or (len(section) > 0 and section[0].lower() != section[0]):
        signs_count += 0.3
        for sign in signs_2ord:
            if section.lower().find(sign):
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
    for find in list(month_words.finditer(string.lower())) + list(month_romandigs.finditer(string)):
        month_number = False
        year_number = False
        day_number = False

        # try to extract month
        found_month = find.group(0)
        if verbose:
            print('{} - month candidate'.format(found_month))
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

        # try to extract year
        next_space_ind = find.end() + string[find.end():].find(' ')
        if next_space_ind == -1:
            if verbose:
                print('beginning of the string, aborted')
            continue
        # Note thet this should work "automagically" at the end of a string.
        expected_year_str = string[next_space_ind+1:next_space_ind+5]
        if verbose:
            print('{} - expected year string'.format(expected_year_str))
        if re.match('^\\d+$', expected_year_str):
            year_number = int(expected_year_str)
        else:
            continue
        if verbose:
            print('{} - year number'.format(year_number))

        # try to extract day
        prev_space_ind = string[:find.start()].rfind(' ')
        if prev_space_ind == -1:
            if verbose:
                print('beginning of the string, aborted')
            continue
        expected_day_str = string[prev_space_ind-2:prev_space_ind]
        short_expected_day_str = string[prev_space_ind-1:prev_space_ind]
        if verbose:
            print('{} - expected day string, may be 1 shorter'.format(expected_day_str))
        if re.match('^\\d+$', expected_day_str):
            day_number = int(expected_day_str)
        elif re.match('^\\d+$', short_expected_day_str):
            day_number = int(short_expected_day_str)
        else:
            continue
        if verbose:
            print('{} - day number'.format(day_number))
            print('Date found: {}'.format(day_number, month_number, year_number))

        dates.append((day_number, month_number, year_number))

    return dates

def fuzzy_match(str1, str2):
    """For now, fuzzy match is actually exact."""
    # TODO make it fuzzy.
    return str1 == str2

doctest.testmod()
