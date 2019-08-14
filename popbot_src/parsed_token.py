# The class for saving parsed tokens obtained by morpho.py.

class ParsedToken():
    def __init__(self, form, lemma, interp,
            proper_name=False, unknown_form=False, latin=False, corrected=False):
        self.form = form
        self.lemma = lemma
        self.interp = interp # as string
        self.proper_name = proper_name
        self.unknown_form = unknown_form
        self.latin = latin
        self.corrected = corrected

    @classmethod
    def from_str(cls, token_str):
        semantic_fields = token_str.split('_')
        morpho_fields = '_'.join([f for f in semantic_fields if not f in ['PN', '??']]).split(':')
        self = cls(morpho_fields[0], morpho_fields[1],  ':'.join(morpho_fields[2:]))
        self.proper_name = 'PN' in semantic_fields
        self.unknown_form = '??' in semantic_fields
        self.latin = 'LAT' in semantic_fields
        self.corrected = '!!' in semantic_fields
        self.form = morpho_fields[0]
        self.lemma = morpho_fields[1]
        self.interp = morpho_fields[2:]
        return self

    def __repr__(self):
        repr_str = '{}:{}:{}'.format(self.form, self.lemma,
                ':'.join(self.interp) if isinstance(self.interp, list) else self.interp)
        if self.unknown_form:
            repr_str = '??_' + repr_str
        elif self.corrected:
            repr_str = '!!_' + repr_str
        if self.proper_name:
            repr_str = 'PN_' + repr_str
        if self.latin:
            repr_str = 'LA_' + repr_str
        return repr_str
