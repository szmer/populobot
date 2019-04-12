import re, roman

MONTHS = re.compile('(stycze?[nń])|(luty?)|(marz?e?c)|(kwie[tc]i?e?[nń])|(maj)|(czerwi?e?c)|(lipi?e?c)|(sierpi?e?[nń])|(wrze[sś]i?e?[nń])|(październik)|(listopad)|(grudz?i?e?[nń])|([ji]anuar)|(februar)|(mart)|(april)|(mai)|([ji]u[nl]i)|(august)|(septemb)|(octob)|(decemb)')

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
            # anachronistic vocabulary
            re.compile('(wsp[oöó0][lł)|(]czesn)|(Vol\\.)|(Fasc\\.)|([fF]ol\.)|(Hal\\. Rel\\.)|(Castr\\. Hal\\.)|(Hal\\. Laud\\.)|(Cop\\. Castr\\.)|(Lauda Dobrinensia)|(Monit\\.? Comit\\.? Pol\\.?)|( zob\\.)|( tek[sś])|( str\\.)')
        ]
def is_meta_line(line, config):
    for sign in meta_signs:
        if sign.search(line):
            ###print(sign, line)
            return True
    # If more than the half of the line of non-alphabetic
    if len(line) > 0 and len(re.sub('\\w', '', line)) / len(line) >= 0.5:
        return True

    # If large percentage of tokens is abbreviated
    ###if line.count(' ') > 0 and line.count('. ') / line.count(' ') >= 0.33:
    ###    return True
    return False

# Headings detection.
heading_signs = ([ # characteristic elements in a heading
         # square brackets used to number sections in editions
         re.compile('^\\[.*\\]'),
         # numbering - also days, years
         re.compile('\\d+'),
         # numbers put in words
         re.compile('(pierwsz)|(drug)|(wt[oó]r)|(dwa)|(trz[ae][cd]z?)|(czwart)|(czter)|(pi[ąę][tc])|(sz[óe][śs][tć])|(si[eó]de?m)|([oó][sś]i?e?m)|(dziewi[ęą][tć])|(dzie[sś]i?[ęą][tcć])|(na[śs][tć])|(st[oa])|(setn?)|(tysi[ęą]c)|(prim)|(secund)|(terti)|(quart)|(quint)|(se[xg])|(vice)|(esim)|(cent)|(mille)|( [xXvViI]{1,3} )'),
         # months
         MONTHS]
         +
         # titles - each of those will count as one occurence of a sign
        [re.compile(s) for s in ['Uchwał[ay]', 'Uniwersał', 'Laudu?m?a?', 'Instrukcy?j?[ae]', 'Instructio', 'Konfederacy?j?', 'Odpowiedź', 'P?okazowan', 'Manifest', 'Protestac', 'Reskrypt', 'Uniwersał', 'Sejmik', 'przedsejmo', 'konkowacyj', 'województwa', 'ziemi']])
heading_antisigns = ([
        re.compile('\\D0+'), # isolated zeros are bogus
        ]
        +
        # verb endings
        [re.compile(s) for s in ['y[lł]\\s', '[sś]my\\s', 'y[lł]u\\s', 'aj[ąe]\\s']]
        +
        # other out of place vocabulary
        [re.compile(s, flags=re.IGNORECASE) for s in ['ichm', 'jmp']]
        )

def is_heading(section, config):
    if len(section) < 15 or len(section) > config['max_heading_len']:
        return False

    signs = [s.search(section) for s in heading_signs]
    signs_count = len([s for s in signs if s])
    antisigns = [s.search(section) for s in heading_antisigns]
    antisigns_count = len([s for s in antisigns if s])
    signs_count -= antisigns_count
###    print(section, signs_count, 'signs')

    return signs_count >= 2 and len(section) > 0 and signs_count > (len(section) / 30)

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
def extract_dates(title_str):
    dates = []
    title_str = title_str.lower()
    month_words = MONTHS # from global
    month_romandigs = re.compile('[xXvViI]{1,3}')
    for find in list(month_words.finditer(title_str)) + list(month_romandigs.finditer(title_str)):
        month_number = False
        year_number = False
        day_number = False

        # try to extract month
        found_month = find.group(0)
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

        # try to extract year
        next_space_ind = find.end() + title_str[find.end():].find(' ')
        if next_space_ind == -1:
            continue
        expected_year_str = title_str[next_space_ind+1:next_space_ind+5]
        if re.match('^\\d+$', expected_year_str):
            year_number = int(expected_year_str)
        else:
            continue

        # try to extract day
        prev_space_ind = title_str[:find.start()].rfind(' ')
        if prev_space_ind == -1:
            continue
        expected_day_str = title_str[prev_space_ind-3:prev_space_ind-1]
        short_expected_day_str = title_str[prev_space_ind-2:prev_space_ind-1]
        if re.match('^\\d+$', expected_day_str):
            day_number = int(expected_day_str)
        elif re.match('^\\d+$', short_expected_day_str):
            day_number = int(short_expected_day_str)
        else:
            continue

        dates.append((day_number, month_number, year_number))

    return dates
