import re

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
heading_signs = [ # characteristic elements in a heading
         # square brackets used to number sections in editions
         re.compile('^\\[.*\\]'),
         # numbering - also days, years
         re.compile('\\d+'),
         # numbers put in words
         re.compile('(pierwsz)|(drug)|(wt[oó]r)|(dwa)|(trz[ae][cd]z?)|(czwart)|(czter)|(pi[ąę][tc])|(sz[óe][śs][tć])|(si[eó]de?m)|([oó][sś]i?e?m)|(dziewi[ęą][tć])|(dzie[sś]i?[ęą][tcć])|(na[śs][tć])|(st[oa])|(setn?)|(tysi[ęą]c)|(prim)|(secund)|(terti)|(quart)|(quint)|(se[xg])|(vice)|(esim)|(cent)|(mille)|( [xXvViI]{1,3} )'),
         # months
         re.compile('(stycze?[nń])|(luty?)|(marz?e?c)|(kwie[tc]i?e?[nń])|(maj)|(czerwi?e?c)|(lipi?e?c)|(sierpi?e?[nń])|(wrze[sś]i?e?[nń])|(październik)|(listopad)|(grudz?i?e?[nń])|([ji]anuar)|(februar)|(mart)|(april)|(mai)|([ji]u[nl]i)|(august)|(e?o?m?br)'),
         # titles
        re.compile('(Uchwał[ay])|(Uniwersał)|(Laudu?m?a?)|(Instrukcy?j?[ae])|(Instructio)|(Konfederacy?j?)|(Odpowiedź)|(P?okazowan)|(Manifest)|(Protestac)|(Reskrypt)|(Uniwersał)')
        ]
def is_heading(section, config):
    if len(section) < 15 or len(section) > config['max_heading_len']:
        return False

    signs = [s.search(section) for s in heading_signs]
    signs_count = len([s for s in signs if s])
###    print(section, signs_count, 'signs')

    return signs_count >= 2 and len(section) > 0 and signs_count > (len(section) / 30)
