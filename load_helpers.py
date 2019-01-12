import re

# Meta section detection.
meta_signs = [ # characteristic elements in a meta section
            # page range at the end
            re.compile('\\d+-\\d+\\.$')
        ]
def is_meta_line(line, config):
    for sign in meta_signs:
        if sign.match(line):
            return True
    return False

# Headings detection.
heading_signs = [ # characteristic elements in a heading
         # square brackets used to number sections in editions
         re.compile('\\[.*\\]')
         # numbering - also days, years
         re.compile('\\d+')
         # numbers put in words
         re.compile('pierwsz|drug|wt[oó]r|dwa|trz[ae][cd]z?|czwart|czter|pi[ąę][tc]|sz[óe][śs][tć]|si[eó]de?m|[oó][sś]i?e?m|dziewi[ęą][tć]|dzie[sś]i?[ęą][tcć]|na[śs][tć]|st[oa]|setn?|tysi[ęą]c|prim|secund|terti|quart|quint|se[xg]|vice|esim|cent|mille')
         # months
         re.compile('stycze?[nń]|luty?|marz?e?c|kwie[tc]i?e?[nń]|maj|czerwi?e?c|lipi?e?c|sierpi?e?[nń]|wrze[sś]i?e?[nń]|październik|listopad|grudz?i?e?[nń]|[ji]anuar|februar|mart|april|mai|[ji]u[nl]i|august|e?o?m?br')
         # titles
        re.compile('Uchwał[ay]|Uniwersał|Laudu?m?a?|Instrukcy?j?[ae]|Instructio|Konfederacy?j?|Odpowiedź|P?okazowan|Manifest'),
        ]
def is_heading(section, config):
    if len(section) > config['max_heading_len']:
        return False

    signs = [s.match(section) for s in heading_signs]
    signs_count = len([s for s in signs if s])

    return signs_count => 2 and signs_count > (len(section) / 10)
